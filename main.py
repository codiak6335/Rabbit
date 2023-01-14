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
display = displays.getDisplay()
ss = SwimSet(display, False)


def do_accessPoint():
    ssid = "PicoW"
    password = "123456789"

    ap = network.WLAN(network.AP_IF)
    # ap.active(True)
    ap.config(essid=ssid, password=password)
    ap.active(True)

    while ap.active == False:
        pass

    print("Access point active")
    print(ap.ifconfig())
    return ap.ifconfig()


def do_connect():
    SSID = 'beaver'
    KEY = 'joanieandcharlielovealex'
    import network
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        sta_if.connect(SSID, KEY)
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
def IgniteLedLoc(request, path):
    print("path : ", path)
    debug(request)
    ss.LedStrand.IgniteLedLoc(int(path))

    return '{"msg":"Lit"}'


@app.route('/prototypes/<path:path>')
def index(request, path):
    return send_file('prototypes/' + path)


@app.route('/')
def index(request):
    return send_file("rabbit.html")


@app.route('/static/<path:path>')
def static(request, path):
    if '..' in path:
        # directory traversal is not allowed
        return 'Not found', 404
    return send_file('static/' + path)


@app.route('/prep')
def prep(request):
    print("Prepping")
    # localstop()
    print(request.args)
    print(request.args['audio'])
    print(request.args['duration'][0])
    ss.SetBottomTimes(int(request.args['duration']), int(request.args['distance']), int(request.args['intervals']),
                      int(request.args['repetitions']), 25, request.args['direction'] == "Near")
    ss.useAudio(request.args['audio'])
    return '{"msg":"Prepped"}'


@app.route('/stop')
def stop(request):
    localstop()
    return '{"msg":"Stopped"}'


@app.route('/ClearStrand')
def ClearStrand(request):
    ss.LedStrand.ClearStrand()
    return '{"msg":"Cleared"}'


@app.route('/LightStrand')
def LightStrand(request):
    ss.LedStrand.LightStrand()
    return '{"msg":"StrandLit"}'


@app.route('/LightSegment')
def LightSegment(request):
    ss.LedStrand.LightSegment()
    return '{"msg":"SegmentLit"}'


@app.route('/ignitemarkers')
def ignitemarkers(request):
    ss.LedStrand.IgniteMarkers(ss.debug)


def second_thread():
    ss.LedStrand.ClearStrand()
    ss.Loop()


@app.route('/start')
def start(request):
    # localstop()
    _thread.start_new_thread(second_thread, ())
    return '{"msg":"Started"}'


def localstop():
    if not ss.Stopped:
        print("stopping")
        ss.StopSet()
        i = 0
        while not ss.Stopped and i < 20:
            time.sleep(0.1)  # give the thread a chance to exit cleanly
            i += 1
        print("Stopped")

    else:
        print("Not running")


@app.route('/loadpools')
def LoadPools(request):
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
# netstr = do_accessPoint()
netstr = do_connect()
display.fill(display.black)
display.text("FTL Rabbit v2.0", 1, 2, display.white)
display.text(netstr[0], 1, 12, display.white)
display.text("Status: Idle", 1, 22, display.white)
display.show()

app.run(debug=True, port=80)
