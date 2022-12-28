from machine import Pin, PWM
from utime import sleep

class CAudioAlert:
    def __init__(self):
        self.alertDelay = 2.5
        self.speaker = PWM(Pin(15, Pin.OUT))
        self.tonesOn = True
        self.speaker.freq(2000)
        
    def useAudio(self, flag):
        self.tonesOn = (flag == "yes")
        print("Audio status : ",self.tonesOn)

    def Beep(self):
        if self.tonesOn:
            self.speaker.duty_u16(50000)
            sleep(0.15)
            self.speaker.duty_u16(0)
            sleep(0.85)
            self.speaker.duty_u16(50000)
            sleep(0.15)
            self.speaker.duty_u16(0)
            sleep(0.85)
            self.speaker.duty_u16(50000)
            sleep(0.50)
            self.speaker.duty_u16(0)
        else:
            self.alertDelay = 2.5

