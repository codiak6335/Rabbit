AP_IF = 0
STA_IF = 1


class WLAN:
    def __init__(self, interface):
        self.interface = interface
        self._active = False
        self._connected = False
        self._config = {}

    def active(self, value=None):
        if value is not None:
            self._active = bool(value)
        return self._active

    def config(self, **kwargs):
        self._config.update(kwargs)

    def connect(self, ssid, password):
        self._config.update(ssid=ssid, password=password)
        self._connected = True

    def disconnect(self):
        self._connected = False

    def isconnected(self):
        return self._connected

    def ifconfig(self):
        if self.interface == AP_IF:
            return ("192.168.4.1", "255.255.255.0", "192.168.4.1", "192.168.4.1")
        return ("127.0.0.1", "255.0.0.0", "127.0.0.1", "127.0.0.1")
