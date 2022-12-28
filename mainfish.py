import network 
from swimset import SwimSet
import time

from microdot import Microdot, redirect, send_file
import _thread

app = Microdot()
ss = SwimSet(False)


def do_accessPoint():
    ssid = "PicoW"
    password = "123456789"

    ap = network.WLAN(network.AP_IF)
    ap.config(essid=ssid, password=password) 
    ap.active(True)

    while ap.active == False:
      pass

    print("Access point active")
    print(ap.ifconfig())


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
    
def debug():
    print (request.args)
    print (request.url)
    print (request.method)
    print (request.app)
    print (request.client_addr)
    print (request.method)
    print (request.url)
    print (request.query_string)
    print (request.headers)
    print (request.cookies)
    print (request.content_length)
    print (request.content_type)
    print (request.g)

@app.route('/')
def index(request): 
    return send_file("fish.html")

@app.route('/static/<path:path>')
def static(request, path):
    if '..' in path:
        # directory traversal is not allowed
        return 'Not found', 404
    return send_file('static/' + path)


@app.route('/prep')
def prep(request):
    print("Prepping")
    #localstop()
    print(request.args)
    print (request.args['audio'])
    print (request.args['duration'][0])
    ss.SetBottomTimes(int(request.args['duration']),int(request.args['distance']),int(request.args['intervals']),int(request.args['repetitions']))
    ss.useAudio(request.args['audio'])
    return "Prepped"

@app.route('/stop')
def stop(request):
    localstop()
    return "Stopped"

 
def second_thread():
    ss.Loop()
    
@app.route('/start')
def start(request):
    localstop()     
    _thread.start_new_thread(second_thread,())
    return "Started"


def localstop():
    if not ss.Stopped:
        print("stopping")
        ss.StopSet()
        i = 0
        while not ss.Stopped and i<20:
            time.sleep(0.1)   #give the thread a chance to exit cleanly
            i += 1
        print("stopped")

    else:
        print("Not running")


do_accessPoint()
#do_connect()
app.run(debug=True, port=80)


