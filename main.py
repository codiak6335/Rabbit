import _thread
import time
from logging import getLogger, basicConfig, DEBUG

import network
import ujson

import displays
from microdot import Microdot, send_file
from swimset import SwimSet

# from oled233 import OLED_2inch23

basicConfig(level=DEBUG, filename=None, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = getLogger()

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
    return send_file("rabbit.html")


# noinspection PyUnusedLocal
@app.route('/static/<path:path>')
def static(request, path):
    if '..' in path:
        # directory traversal is not allowed
        return 'Not found', 404
    return send_file('static/' + path)


# noinspection SpellCheckingInspection
@app.route('/prep')
def prep(request):
    print("Prepping")
    # local_stop()
    print(request.args)
    print(request.args['audio'])
    print(request.args['duration'][0])
    ss.set_bottom_times(int(request.args['duration']), int(request.args['distance']), int(request.args['intervals']),
                        int(request.args['repetitions']), 25, request.args['direction'] == "Near")
    ss.use_audio(request.args['audio'])
    return '{"msg":"Prepped"}'


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
