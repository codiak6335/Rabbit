import _thread
import json
import math
import os
import time
import sys

import displays
from microdot import Microdot, send_file
from runtime_support import EMULATOR_STATE, IS_EMULATOR, get_machine_module, get_network_module, patch_time_module, project_path
from swimset import SwimSet

patch_time_module()
network = get_network_module()
machine = get_machine_module()
ujson = json

# from oled233 import OLED_2inch23

app = Microdot()
display = displays.get_display()
ss = SwimSet(display, False)
run_lock = _thread.allocate_lock()
ADMIN_TOKEN = os.getenv('RABBIT_ADMIN_TOKEN', '')


def json_response(payload, status=200):
    return json.dumps(payload), status, {'Content-Type': 'application/json'}


def error_response(message, status=400):
    return json_response({'error': message}, status)


def get_header(request, name):
    value = request.headers.get(name)
    if value is None:
        value = request.headers.get(name.lower())
    return value


def require_admin(request):
    if not ADMIN_TOKEN:
        return None
    supplied_token = request.args.get('token') or get_header(request, 'X-Rabbit-Token')
    if supplied_token != ADMIN_TOKEN:
        return error_response('Forbidden', 403)
    return None


def safe_project_file(base_path, request_path):
    normalized = os.path.normpath('/' + request_path).lstrip('/')
    full_path = project_path(os.path.join(base_path, normalized))
    base_full_path = project_path(base_path)
    if not os.path.abspath(full_path).startswith(os.path.abspath(base_full_path) + os.sep):
        return None
    return full_path


def required_arg(args, name):
    value = args.get(name)
    if value is None or value == '':
        raise ValueError(f'Missing required parameter: {name}')
    return value


def int_arg(args, name, minimum=None):
    try:
        value = int(required_arg(args, name))
    except ValueError:
        raise ValueError(f'Invalid integer parameter: {name}')
    if minimum is not None and value < minimum:
        raise ValueError(f'{name} must be at least {minimum}')
    return value


def get_pool_names():
    with open(project_path('/db/pools.json'), 'r') as pools_file:
        pools_data = json.load(pools_file)
    return pools_data.get('pools', {}).keys()


def pool_length_to_feet(length_label):
    if str(length_label).strip().lower() == '25 yards':
        return 75.0
    return 164.042


def read_int_file(path, default_value):
    try:
        with open(path, 'r') as value_file:
            return int(value_file.readline().strip())
    except (OSError, ValueError):
        return default_value


def validate_pools_config(data):
    if not isinstance(data, dict):
        raise ValueError('pools config must be a JSON object')
    pools = data.get('pools')
    if not isinstance(pools, dict) or not pools:
        raise ValueError('pools config must include a non-empty pools object')
    default_pool = data.get('defaultPool')
    if default_pool not in pools:
        raise ValueError('defaultPool must reference an existing pool')

    for pool_name, pool in pools.items():
        if not isinstance(pool, dict):
            raise ValueError(f'pool must be an object: {pool_name}')
        pixel_count = int(pool.get('PixelCount', 0))
        if pixel_count <= 0:
            raise ValueError(f'PixelCount must be greater than zero: {pool_name}')
        if 'Length' not in pool:
            raise ValueError(f'Length is required: {pool_name}')
        segments = pool.get('Segments')
        if not isinstance(segments, list) or not segments:
            raise ValueError(f'Segments must be a non-empty list: {pool_name}')

        previous_distance = None
        for index, segment in enumerate(segments):
            if not isinstance(segment, dict):
                raise ValueError(f'Segment must be an object: {pool_name} #{index}')
            first_pixel = int(segment.get('FirstPixel', -1))
            distance = float(segment.get('Distance'))
            if first_pixel < 0:
                raise ValueError(f'FirstPixel must be at least zero: {pool_name} #{index}')
            if previous_distance is not None and distance < previous_distance:
                raise ValueError(f'Segment distances must not decrease: {pool_name} #{index}')
            previous_distance = distance


def validate_wifi_config(data):
    if not isinstance(data, dict):
        raise ValueError('wifi config must be a JSON object')
    wifis = data.get('wifis')
    if not isinstance(wifis, list):
        raise ValueError('wifi config must include a wifis list')
    for index, wifi in enumerate(wifis):
        if not isinstance(wifi, dict):
            raise ValueError(f'wifi entry must be an object: #{index}')
        if not isinstance(wifi.get('ssid'), str) or wifi.get('ssid') == '':
            raise ValueError(f'wifi ssid is required: #{index}')
        if not isinstance(wifi.get('password'), str):
            raise ValueError(f'wifi password must be a string: #{index}')
        int(wifi.get('active', 0))


def validate_db_json(path, data):
    normalized = path.lower()
    if normalized == 'pools.json':
        validate_pools_config(data)
    elif normalized == 'wifi.json':
        validate_wifi_config(data)


def write_json_atomic(file_path, data):
    temp_path = file_path + '.tmp'
    with open(temp_path, 'w') as json_file:
        json.dump(data, json_file, indent=2)
        json_file.write('\n')
    try:
        os.replace(temp_path, file_path)
    except AttributeError:
        try:
            os.remove(file_path)
        except OSError:
            pass
        os.rename(temp_path, file_path)


LEGACY_DEPTH_ANCHORS = {
    'Bellevue East': [
        {'led': 162, 'depthFeet': 5.5},
        {'led': 285, 'depthFeet': 12.0},
        {'led': 366, 'depthFeet': 12.0},
        {'led': 517, 'depthFeet': 5.5},
        {'led': 883, 'depthFeet': 4.0},
    ],
    'Bellevue West': [
        {'led': 174, 'depthFeet': 5.5},
        {'led': 252, 'depthFeet': 12.0},
        {'led': 326, 'depthFeet': 12.0},
        {'led': 527, 'depthFeet': 5.5},
        {'led': 890, 'depthFeet': 5.5},
    ],
}


def interpolate_depth_for_led(led, depth_anchors):
    if not depth_anchors:
        return None
    if led <= depth_anchors[0]['led']:
        return depth_anchors[0]['depthFeet']
    for index in range(len(depth_anchors) - 1):
        start = depth_anchors[index]
        end = depth_anchors[index + 1]
        if led <= end['led']:
            led_delta = end['led'] - start['led']
            t = 0.0 if led_delta == 0 else (led - start['led']) / led_delta
            return start['depthFeet'] + ((end['depthFeet'] - start['depthFeet']) * t)
    return depth_anchors[-1]['depthFeet']


def interpolate_distance_for_led(led, distance_anchors):
    if led <= distance_anchors[0]['led']:
        return distance_anchors[0]['distanceFeet']
    for index in range(len(distance_anchors) - 1):
        start = distance_anchors[index]
        end = distance_anchors[index + 1]
        if led <= end['led']:
            led_delta = end['led'] - start['led']
            t = 0.0 if led_delta == 0 else (led - start['led']) / led_delta
            return start['distanceFeet'] + ((end['distanceFeet'] - start['distanceFeet']) * t)
    return distance_anchors[-1]['distanceFeet']


def load_pool_profile(pool_name=None):
    with open(project_path('/db/pools.json'), 'r') as pools_file:
        pools_data = json.load(pools_file)

    selected_pool_name = pool_name or pools_data.get('defaultPool')
    pools = pools_data.get('pools', {})
    pool = pools.get(selected_pool_name)
    if pool is None:
        raise ValueError(f'Unknown pool: {selected_pool_name}')

    spacing_mm = float(pool.get('LedSpacingMm', pools_data.get('LedSpacingMm', 30)))
    spacing_feet = spacing_mm / 304.8
    length_feet = pool_length_to_feet(pool.get('Length', ''))
    last_led = read_int_file(project_path('/db/lastled.dat'), int(pool.get('PixelCount', 0)))

    anchors = []
    for segment in pool.get('Segments', []):
        anchor = {
            'led': int(segment.get('FirstPixel', 0)),
            'distanceFeet': float(segment.get('Distance', 0.0)),
        }
        if 'DepthFeet' in segment:
            anchor['depthFeet'] = float(segment['DepthFeet'])
        elif 'Depth' in segment:
            anchor['depthFeet'] = float(segment['Depth'])
        anchors.append(anchor)

    anchors.sort(key=lambda item: item['led'])
    if not anchors:
        raise ValueError(f'Pool has no segment anchors: {selected_pool_name}')
    markers_by_distance = {0.0: {'distanceFeet': 0.0, 'label': '0 ft'}}
    for anchor in anchors:
        markers_by_distance[anchor['distanceFeet']] = {
            'distanceFeet': anchor['distanceFeet'],
            'label': f"{anchor['distanceFeet']:.1f} ft",
        }
    markers_by_distance[length_feet] = {'distanceFeet': length_feet, 'label': f"{length_feet:.0f} ft"}

    depth_anchors = [
        {'led': int(anchor['led']), 'depthFeet': float(anchor['depthFeet'])}
        for anchor in anchors
        if 'depthFeet' in anchor
    ]
    if not depth_anchors:
        depth_anchors = LEGACY_DEPTH_ANCHORS.get(selected_pool_name, [])
    depth_anchors = sorted(depth_anchors, key=lambda item: item['led'])

    if anchors[0]['distanceFeet'] > 0:
        anchors.insert(0, {'led': anchors[0]['led'], 'distanceFeet': 0.0})

    if last_led > anchors[-1]['led'] or length_feet > anchors[-1]['distanceFeet']:
        final_anchor = {
            'led': max(last_led, anchors[-1]['led']),
            'distanceFeet': max(length_feet, anchors[-1]['distanceFeet']),
        }
        if 'depthFeet' in anchors[-1]:
            final_anchor['depthFeet'] = anchors[-1]['depthFeet']
        anchors.append(final_anchor)

    distance_anchors = [anchor.copy() for anchor in anchors]
    anchors_by_led = {anchor['led']: anchor.copy() for anchor in anchors}
    for depth_anchor in depth_anchors:
        led = depth_anchor['led']
        if led not in anchors_by_led:
            anchors_by_led[led] = {
                'led': led,
                'distanceFeet': interpolate_distance_for_led(led, distance_anchors),
            }
        anchors_by_led[led]['depthFeet'] = depth_anchor['depthFeet']
    anchors = sorted(anchors_by_led.values(), key=lambda item: item['led'])

    for anchor in anchors:
        interpolated_depth = interpolate_depth_for_led(anchor['led'], depth_anchors)
        if interpolated_depth is not None:
            anchor['approximateDepthFeet'] = interpolated_depth

    sections = []
    depth_feet = anchors[0].get('approximateDepthFeet', anchors[0].get('depthFeet', 0.0))
    anchors[0]['calculatedDepthFeet'] = depth_feet
    max_depth = depth_feet
    min_depth = depth_feet

    for index in range(len(anchors) - 1):
        start = anchors[index]
        end = anchors[index + 1]
        led_delta = end['led'] - start['led']
        travel_delta = end['distanceFeet'] - start['distanceFeet']
        strip_length_feet = abs(led_delta) * spacing_feet
        possible = strip_length_feet + 0.001 >= abs(travel_delta)
        vertical_magnitude = math.sqrt(max(0.0, strip_length_feet ** 2 - travel_delta ** 2))

        if 'approximateDepthFeet' in start and 'approximateDepthFeet' in end:
            depth_delta = end['approximateDepthFeet'] - start['approximateDepthFeet']
            depth_feet = end['approximateDepthFeet']
            mode = 'depth-profile'
        else:
            midpoint = start['distanceFeet'] + (travel_delta / 2.0)
            sign = 1.0 if midpoint <= (length_feet / 2.0) else -1.0
            depth_delta = vertical_magnitude * sign
            depth_feet += depth_delta
            mode = 'geometry-with-pool-half-direction'

        end['calculatedDepthFeet'] = depth_feet
        max_depth = max(max_depth, depth_feet)
        min_depth = min(min_depth, depth_feet)
        sections.append({
            'startLed': start['led'],
            'endLed': end['led'],
            'startDistanceFeet': start['distanceFeet'],
            'endDistanceFeet': end['distanceFeet'],
            'stripLengthFeet': strip_length_feet,
            'travelLengthFeet': abs(travel_delta),
            'depthChangeFeet': depth_delta,
            'possibleWithLedSpacing': possible,
            'mode': mode,
        })

    led_positions = []
    max_led = max(last_led, anchors[-1]['led'])
    anchor_index = 0
    for led in range(max_led + 1):
        while anchor_index < len(anchors) - 2 and led > anchors[anchor_index + 1]['led']:
            anchor_index += 1
        start = anchors[anchor_index]
        end = anchors[min(anchor_index + 1, len(anchors) - 1)]
        led_span = end['led'] - start['led']
        t = 0.0 if led_span == 0 else (led - start['led']) / led_span
        t = max(0.0, min(1.0, t))
        distance = start['distanceFeet'] + ((end['distanceFeet'] - start['distanceFeet']) * t)
        start_depth = start.get('calculatedDepthFeet', 0.0)
        end_depth = end.get('calculatedDepthFeet', start_depth)
        depth = start_depth + ((end_depth - start_depth) * t)
        led_positions.append({
            'led': led,
            'distanceFeet': distance,
            'depthFeet': depth,
        })

    return {
        'poolName': selected_pool_name,
        'lengthFeet': length_feet,
        'ledSpacingMm': spacing_mm,
        'lastLed': last_led,
        'depthRangeFeet': max_depth - min_depth,
        'anchors': anchors,
        'sections': sections,
        'markers': [markers_by_distance[key] for key in sorted(markers_by_distance)],
        'ledPositions': led_positions,
    }


def do_access_point():
    mac_address_bytes = machine.unique_id()

    # Convert the bytes to a formatted string
    mac_address_str = ":".join(["{:02X}".format(byte) for byte in mac_address_bytes])

    # Print the MAC address
    print("MAC Address:", mac_address_str)
    ssid = "Rabbit-" + mac_address_str
    password = "123456789"

    ap = network.WLAN(network.AP_IF)
    # ap.active(True)
    ap.config(essid=ssid, password=password)
    ap.active(True)

    while not ap.active:
        pass

    print("Access point active")
    print(ap.ifconfig())
    return ap

def do_connection_management():
    # make sure we are not connected
    ap = network.WLAN(network.AP_IF)
    ap.disconnect()
    ap.active(False)

    wlan = network.WLAN(network.STA_IF)
    wlan.disconnect()
    wlan.active(False)
    time.sleep(3)

    profiles = read_profiles(project_path('/db/wifi.json'))
    for wifi in profiles:
        if wifi['active'] != 0:
            wlan = do_connect(wifi['ssid'], wifi['password'])
            if wlan.isconnected():
                break

    if not wlan.isconnected():
        wlan = do_access_point()
    return wlan.ifconfig()

def read_profiles(filename):
    with open(filename, 'r') as json_file:
        data = ujson.load(json_file)

    print(data['wifis'])        
    return data['wifis']

def do_connect(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    print('Trying to connect to %s...' % ssid)
    wlan.connect(ssid, password)
    for retry in range(200):
        connected = wlan.isconnected()
        if connected:
            break
        time.sleep(0.1)
        print('.', end='')
    if connected:
        print('\nConnected. Network config: ', wlan.ifconfig())
    else:
        print('\nFailed. Not Connected to: ' + ssid)
    return wlan


def debug(request):
    print(request.args)
    print(request.url)
    print(request.method)
    print(request.app)
    print(request.client_addr)
    print(request.method)
    print(request.url)
    print(request.query_string)
    print(request.headers)
    print(request.cookies)
    print(request.content_length)
    print(request.content_type)
    print(request.g)

@app.route('/saveaslastled/<path:path>')
def save_as_last_led(request, path):
    admin_error = require_admin(request)
    if admin_error:
        return admin_error
    try:
        led = int(path)
    except ValueError:
        return error_response('Invalid LED number', 400)
    if led < 0:
        return error_response('LED number must be at least zero', 400)
    with open(project_path('/db/lastled.dat'), "w") as file1:
        file1.write(f"{led}")
    return json_response({'msg': 'saved'})

@app.route('/IgniteLedLoc/<path:path>')
def ignite_led_location(request, path):
    admin_error = require_admin(request)
    if admin_error:
        return admin_error
    try:
        led = int(path)
    except ValueError:
        return error_response('Invalid LED number', 400)
    print("path : ", path)
    debug(request)
    ss.LedStrand.ignite_led_location(led)

    return json_response({'msg': 'Lit'})


# noinspection PyUnusedLocal
@app.route('/prototypes/<path:path>')
def index(request, path):
    return send_file(project_path('prototypes/' + path))



# noinspection PyUnusedLocal
@app.route('/')
def index(request):
    return send_file(project_path('index.html'))

@app.route('/favicon.ico')
def index(request):
    return send_file(project_path('favicon.ico'))


@app.route('/emulator')
def emulator(request):
    return send_file(project_path('emulator.html'))


@app.route('/api/emulator/state')
def emulator_state(request):
    snapshot = EMULATOR_STATE.snapshot()
    flat_progress = {
        'active': False,
        'fraction': 0.0,
        'direction': 'near-to-far',
    }
    if ss.RunningMode and ss.startTimeOfThisLength is not None and ss.current_length_ms:
        elapsed_ms = time.ticks_diff(time.ticks_ms(), ss.startTimeOfThisLength)
        fraction = elapsed_ms / ss.current_length_ms
        if fraction < 0:
            fraction = 0.0
        elif fraction > 1:
            fraction = 1.0
        if not ss.Direction:
            fraction = 1.0 - fraction
        flat_progress = {
            'active': True,
            'fraction': fraction,
            'direction': 'near-to-far' if ss.Direction else 'far-to-near',
        }
    snapshot['flatProgress'] = flat_progress
    return json.dumps(snapshot)


@app.route('/api/emulator/pool-profile')
def emulator_pool_profile(request):
    try:
        profile = load_pool_profile(request.args.get('pool'))
    except ValueError as exc:
        return error_response(str(exc), 404)
    return json_response(profile)


def string_to_seconds(input_str):
    try:
        # Split the input string into components
        components = input_str.split(':')

        if len(components) == 1:
            # Only seconds and fractions provided
            seconds_parts = components[0].split('.')
            if len(seconds_parts) == 2:
                seconds = float(seconds_parts[0])
                fractions = float(seconds_parts[1])
            else:
                seconds = float(seconds_parts[0])
                fractions = 0.0  # If no fractions provided, assume 0.0 seconds
            total_seconds = seconds + (fractions / 100.0)

        elif len(components) == 2:
            # Minutes and seconds provided
            minutes = float(components[0])
            seconds_parts = components[1].split('.')
            if len(seconds_parts) == 2:
                seconds = float(seconds_parts[0])
                fractions = float(seconds_parts[1])
            else:
                seconds = float(seconds_parts[0])
                fractions = 0.0  # If no fractions provided, assume 0.0 seconds
            total_seconds = (minutes * 60) + seconds + (fractions / 100.0)

        elif len(components) == 3:
            # Hours, minutes, seconds, and fractions provided
            hours = float(components[0])
            minutes = float(components[1])
            seconds_parts = components[2].split('.')
            if len(seconds_parts) == 2:
                seconds = float(seconds_parts[0])
                fractions = float(seconds_parts[1])
            else:
                seconds = float(seconds_parts[0])
                fractions = 0.0  # If no fractions provided, assume 0.0 seconds
            total_seconds = (hours * 3600) + (minutes * 60) + seconds + (fractions / 100.0)

        else:
            raise ValueError("Input does not have a valid format.")
        print(f"string to seconds : ${total_seconds}") 
        return total_seconds

    except ValueError as e:
        print(f"Error: {e}")
        return None


def get_variation_fraction(request_args):
    try:
        return float(request_args.get('variation', '8')) / 100.0
    except ValueError:
        return 0.08

# Example usage:
#input_string = "01:23:45.67"
#seconds_float = string_to_seconds(input_string)
#if seconds_float is not None:
    #print(f"Converted value: {seconds_float:.2f} seconds")


# noinspection SpellCheckingInspection
@app.route('/prep')
def prep(request):
    admin_error = require_admin(request)
    if admin_error:
        return admin_error
    print("Prepping ")
    if ss.RunningMode:
        return error_response('Cannot prep while a set is running.', 409)

    try:
        pool = required_arg(request.args, 'pool')
        if pool not in get_pool_names():
            raise ValueError(f'Unknown pool: {pool}')

        direction = required_arg(request.args, 'direction')
        if direction not in ('Near', 'Far'):
            raise ValueError('direction must be Near or Far')

        audio = required_arg(request.args, 'audio')
        if audio not in ('Yes', 'No'):
            raise ValueError('audio must be Yes or No')

        duration_seconds = string_to_seconds(required_arg(request.args, 'duration'))
        interval_seconds = string_to_seconds(required_arg(request.args, 'interval'))
        if duration_seconds is None or duration_seconds <= 0:
            raise ValueError('duration must be greater than zero')
        if interval_seconds is None or interval_seconds < duration_seconds:
            raise ValueError('interval must be greater than or equal to duration')

        distance = int_arg(request.args, 'distance', 1)
        repetitions = int_arg(request.args, 'repetitions', 0)
        strategy = request.args.get('strategy', 'even')
        if strategy not in ('even', 'negative_split', 'surge'):
            raise ValueError('strategy must be even, negative_split, or surge')
        variation = get_variation_fraction(request.args)

        print(f'duration = {duration_seconds}')
        print(f'interval = {interval_seconds}')
        print(f'strategy = {strategy}, variation = {variation}')
        ss.set_bottom_times(int(duration_seconds), distance, int(interval_seconds),
                            repetitions, 25, direction == "Near", pool, strategy, variation)
        ss.use_audio(audio)
    except (KeyError, ValueError, TypeError) as exc:
        return error_response(str(exc), 400)

    return json_response({'msg': 'Prepped'})


# noinspection PyUnusedLocal
@app.route('/db/<path:path>', methods=['GET', 'POST'])
def db(request, path):
    print("db ", path)
    file_path = safe_project_file('db', path)
    if file_path is None:
        return 'Not found', 404
    if request.method == 'GET':
        return send_file(file_path)
    elif request.method == 'POST':
        admin_error = require_admin(request)
        if admin_error:
            return admin_error
        print(request.body)
        body = request.body.decode() if isinstance(request.body, bytes) else request.body
        try:
            data = json.loads(body)
            validate_db_json(path, data)
        except (TypeError, ValueError) as exc:
            return error_response(str(exc), 400)
        write_json_atomic(file_path, data)
            
        return json_response({'msg': 'Saved'})
    
    

# noinspection PyUnusedLocal
@app.route('/css/<path:path>')
def css(request, path):
    print("css ", path)
    file_path = safe_project_file('css', path)
    if file_path is None:
        return 'Not found', 404
    return send_file(file_path)

# noinspection PyUnusedLocal
@app.route('/js/<path:path>')
def css(request, path):
    print("js ", path)
    file_path = safe_project_file('js', path)
    if file_path is None:
        return 'Not found', 404
    return send_file(file_path)



# noinspection PyUnusedLocal
@app.route('/static/<path:path>')
def static(request, path):
    print("static ", path)
    file_path = safe_project_file('static', path)
    if file_path is None:
        return 'Not found', 404
    return send_file(file_path)


# noinspection PyUnusedLocal
@app.route('/stop')
def stop(request):
    admin_error = require_admin(request)
    if admin_error:
        return admin_error
    local_stop()
    return json_response({'msg': 'Stopped'})


# noinspection PyUnusedLocal
@app.route('/ClearStrand')
def clear_strand(request):
    admin_error = require_admin(request)
    if admin_error:
        return admin_error
    ss.LedStrand.clear_strand()
    return json_response({'msg': 'Cleared'})


# noinspection PyUnusedLocal
@app.route('/LightStrand')
def light_strand(request):
    admin_error = require_admin(request)
    if admin_error:
        return admin_error
    ss.LedStrand.light_strand()
    return json_response({'msg': 'StrandLit'})


# noinspection PyUnusedLocal
@app.route('/LightSegment')
def light_segment(request):
    admin_error = require_admin(request)
    if admin_error:
        return admin_error
    ss.LedStrand.light_segment()
    return json_response({'msg': 'SegmentLit'})


# noinspection PyUnusedLocal,SpellCheckingInspection
@app.route('/ignitemarkers')
def ignite_markers(request):
    admin_error = require_admin(request)
    if admin_error:
        return admin_error
    ss.LedStrand.ignite_markers()
    return json_response({'msg': 'MarkersLit'})


def second_thread():
    ss.LedStrand.clear_strand()
    ss.loop()


def start_set_thread(target):
    with run_lock:
        if ss.RunningMode:
            return False
        if not ss.length_plan_ms:
            raise ValueError('Prep a set before starting.')
        ss.Stopped = False
        ss.RunningMode = True
        _thread.start_new_thread(target, ())
    return True


# noinspection PyUnresolvedReferences,PyUnusedLocal
@app.route('/start')
def start(request):
    admin_error = require_admin(request)
    if admin_error:
        return admin_error
    try:
        if not start_set_thread(second_thread):
            return error_response('A set is already running.', 409)
    except ValueError as exc:
        return error_response(str(exc), 400)
    return json_response({'msg': 'Started'})

def sprint_second_thread():
    ss.LedStrand.clear_strand()
    ss.sprintloop()

# noinspection PyUnresolvedReferences,PyUnusedLocal
@app.route('/startsprint')
def startsprint(request):
    admin_error = require_admin(request)
    if admin_error:
        return admin_error
    try:
        if not start_set_thread(sprint_second_thread):
            return error_response('A set is already running.', 409)
    except ValueError as exc:
        return error_response(str(exc), 400)
    return json_response({'msg': 'Started'})


def local_stop():
    if not ss.Stopped:
        print("stopping")
        ss.stop_set()
        i = 0
        while not ss.Stopped and i < 20:
            time.sleep(0.1)  # give the thread a chance to exit cleanly
            i += 1
        print("Stopped")

    else:
        print("Not running")


# noinspection PyUnusedLocal,SpellCheckingInspection
@app.route('/loadpools')
def load_pools(request):
    with open(project_path('/db/pools.json'), 'r') as pools_file:
        pools = json.load(pools_file)
    return json_response(pools)


# noinspection PyUnusedLocal,SpellCheckingInspection
@app.route('/HardReset')
def hardreset(request):
    admin_error = require_admin(request)
    if admin_error:
        return admin_error
    try:
        machine.reset()
    except SystemExit as exc:
        return json_response({'msg': 'reset-emulated'})
    return json_response({'msg': 'reset'})

# OLED = OLED_2inch23()
display.fill(display.black)
display.text("FTL Rabbit v2.0", 1, 2, display.white)
display.text("Network Starting", 1, 12, display.white)
display.show()
if IS_EMULATOR:
    netstr = ('127.0.0.1',)
else:
    netstr = do_connection_management()
display.fill(display.black)
display.text("FTL Rabbit v2.0", 1, 2, display.white)
display.text(netstr[0], 1, 12, display.white)
display.text("Status: Idle", 1, 22, display.white)
display.show()

default_host = '0.0.0.0' if IS_EMULATOR else '0.0.0.0'
default_port = 5000 if IS_EMULATOR else 80
run_host = os.getenv('RABBIT_HOST', default_host)
run_port = int(os.getenv('RABBIT_PORT', default_port))
print(f'Rabbit server starting on http://{run_host}:{run_port}')
app.run(host=run_host, debug=True, port=run_port)
