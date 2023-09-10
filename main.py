import _thread
import time
import sys

import network
import ujson

import displays
from microdot import Microdot, send_file
from swimset import SwimSet

# from oled233 import OLED_2inch23

app = Microdot()
display = displays.get_display()
ss = SwimSet(display, False)


def do_access_point():
    ssid = "PicoW"
    password = "123456789"

    ap = network.WLAN(network.AP_IF)
    # ap.active(True)
    ap.config(essid=ssid, password=password)
    ap.active(True)

    while not ap.active:
        pass

    print("Access point active")
    print(ap.ifconfig())
    return ap.ifconfig()


# noinspection SpellCheckingInspection
def do_connect():
    ssid = 'beaver'
    key = 'joanieandcharlielovealex'
    import network
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        sta_if.connect(ssid, key)
        while not sta_if.isconnected():
            pass
    print('network config:', sta_if.ifconfig())
    return sta_if.ifconfig()


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
    with open('/db/lastled.dat', "w") as file1:
        file1.write(f"{int(path)}")
    return '{"msg":"saved"}'

@app.route('/IgniteLedLoc/<path:path>')
def ignite_led_location(request, path):
    print("path : ", path)
    debug(request)
    ss.LedStrand.ignite_led_location(int(path))

    return '{"msg":"Lit"}'


# noinspection PyUnusedLocal
@app.route('/prototypes/<path:path>')
def index(request, path):
    return send_file('prototypes/' + path)



# noinspection PyUnusedLocal
@app.route('/')
def index(request):
    return send_file('rabbit.html')

@app.route('/favicon.ico')
def index(request):
    return send_file('favicon.ico')


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

        return total_seconds

    except ValueError as e:
        print(f"Error: {e}")
        return None

# Example usage:
#input_string = "01:23:45.67"
#seconds_float = string_to_seconds(input_string)
#if seconds_float is not None:
    #print(f"Converted value: {seconds_float:.2f} seconds")


# noinspection SpellCheckingInspection
@app.route('/prep')
def prep(request):
    print("Prepping ")
    # local_stop()
    print(request.args)
    print(request.args['audio'])
    print(request.args['duration'][0])
    ss.set_bottom_times()
    print(int(string_to_seconds(request.args['duration'])))
    print(int(string_to_seconds(request.args['interval'])))
    ss.set_bottom_times(int(string_to_seconds(request.args['duration'])), int(request.args['distance']), int(string_to_seconds(request.args['interval'])),
                        int(request.args['repetitions']), 25, request.args['direction'] == "Near")
#    ss.use_audio(request.args['audio'])
    return '{"msg":"Prepped"}'


# noinspection PyUnusedLocal
@app.route('/db/<path:path>', methods=['GET', 'POST'])
def db(request, path):
    print("db ", path)
    if '..' in path:
    # directory traversal is not allowed
        return 'Not found', 404
    if request.method == 'GET':
        return send_file("/db/"+path)
    elif request.method == 'POST':
        print(request.body)
        with open('/db/'+path, "w") as json_file:
            json_file.write(request.body)
            
        return '{"msg":"Saved"}'
    
    

# noinspection PyUnusedLocal
@app.route('/css/<path:path>')
def css(request, path):
    print("css ", path)
    if '..' in path:
    # directory traversal is not allowed
        return 'Not found', 404
    return send_file("/css/"+path)

# noinspection PyUnusedLocal
@app.route('/js/<path:path>')
def css(request, path):
    print("js ", path)
    if '..' in path:
    # directory traversal is not allowed
        return 'Not found', 404
    return send_file("/js/"+path)



# noinspection PyUnusedLocal
@app.route('/static/<path:path>')
def static(request, path):
    print("static ", path)
    if '..' in path:
    # directory traversal is not allowed
        return 'Not found', 404
    return send_file("/static/"+path)


# noinspection PyUnusedLocal
@app.route('/stop')
def stop(request):
    local_stop()
    return '{"msg":"Stopped"}'


# noinspection PyUnusedLocal
@app.route('/ClearStrand')
def clear_strand(request):
    ss.LedStrand.clear_strand()
    return '{"msg":"Cleared"}'


# noinspection PyUnusedLocal
@app.route('/LightStrand')
def light_strand(request):
    ss.LedStrand.light_strand()
    return '{"msg":"StrandLit"}'


# noinspection PyUnusedLocal
@app.route('/LightSegment')
def light_segment(request):
    ss.LedStrand.light_segment()
    return '{"msg":"SegmentLit"}'


# noinspection PyUnusedLocal,SpellCheckingInspection
@app.route('/ignitemarkers')
def ignite_markers(request):
    ss.LedStrand.ignite_markers(ss.debug)


def second_thread():
    ss.LedStrand.clear_strand()
    ss.loop()


# noinspection PyUnresolvedReferences,PyUnusedLocal
@app.route('/start')
def start(request):
    # local_stop()
    _thread.start_new_thread(second_thread, ())
    return '{"msg":"Started"}'

def sprint_second_thread():
    ss.LedStrand.clear_strand()
    ss.sprintloop()

# noinspection PyUnresolvedReferences,PyUnusedLocal
@app.route('/startsprint')
def startsprint(request):
    # local_stop()
    _thread.start_new_thread(sprint_second_thread, ())
    return '{"msg":"Started"}'


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
    pools_filename = "/data/Pools.json"
    f = open(pools_filename, 'r')
    settings_string = f.read()
    f.close()
    n = settings_string.replace("\'", "\"")
    pools = ujson.loads(n)
    ps = str(pools).replace("\'", "\"")
    print(ps)
    return ps


# noinspection PyUnusedLocal,SpellCheckingInspection
@app.route('/HardReset')
def hardreset(request):
    machine.reset()
    return "{msg:reset}"

# OLED = OLED_2inch23()
display.fill(display.black)
display.text("FTL Rabbit v2.0", 1, 2, display.white)
display.text("Network Starting", 1, 12, display.white)
display.show()
# netstr = do_access_point()
netstr = do_connect()
display.fill(display.black)
display.text("FTL Rabbit v2.0", 1, 2, display.white)
display.text(netstr[0], 1, 12, display.white)
display.text("Status: Idle", 1, 22, display.white)
display.show()

app.run(debug=True, port=80)
