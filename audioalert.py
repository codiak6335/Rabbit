from time import sleep

from runtime_support import EMULATOR_STATE, IS_EMULATOR, get_machine_module


machine = get_machine_module()


class CAudioAlert:
    def __init__(self):
        self.alertDelay = 2.5
        self.speaker = machine.Pin(15, machine.Pin.OUT)
        self.tonesOn = True

    def use_audio(self, flag):
        self.tonesOn = (flag == "Yes")
        print("Audio status : ", self.tonesOn)

    def beeps(self, threeBeeps=True):
        if not self.tonesOn:
            print("audio not working")
            self.alertDelay = 2.15
            return

        if IS_EMULATOR:
            EMULATOR_STATE.add_audio_event('triple_beep' if threeBeeps else 'single_beep')

        if threeBeeps:
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
        sleep(0.15)
        self.speaker.value(0)
