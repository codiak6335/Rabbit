from machine import Pin, PWM
from utime import sleep

class CAudioAlert:
    def __init__(self):
        self.alertDelay = 2.5
        self.speaker = Pin(15, Pin.OUT)
        self.tonesOn = True
        
    def useAudio(self, flag):
        self.tonesOn = (flag == "yes")
        print("Audio status : ",self.tonesOn)

    def Beep(self):
        if self.tonesOn:
            print("audio working")
            self.speaker.value(1)
            sleep(0.15)
            self.speaker.value(0)
            sleep(0.85)
            self.speaker.value(1)
            sleep(0.15)
            self.speaker.value(0)
            sleep(0.85)
            self.speaker.value(1)
            sleep(0.50)
            self.speaker.value(0)
        else:
            print("audio not working")
            self.alertDelay = 2.5

