# import gc
# import array
# import random
# import sys
# import os
import gc
import json
import time
from logging import getLogger

import machine
import neopixel

import displays
# import random
from audioalert import CAudioAlert
from ledcursor import CCursor

timescale = 1000
logger = getLogger()
logger.info('Micropython')


class BottomContourMaps:
    def __init__(self):
        self.bcms = []
        self.load()

    def load(self):
        with open('BottomContourMaps.json', 'rt') as f:
            # noinspection PyTypeChecker
            self.bcms = json.load(f)
        return self.bcms

    @staticmethod
    def save():
        with open('BottomContourMaps.json', 'wt') as f:
            r = json.dumps(get_bottom_map())
            f.write(r)


def get_bottom_map():
    bcm = BottomContourMaps()
    return bcm.load()


#    bsm = BottomSectionMap = [[5.5, 0, 10, 75]]
#    if not debug:
#        bsm = BottomSectionMap = [[5.5, 174, 251, 6], [12, 252, 326, 15], [12, 327, 526, 21], [5.5, 527, 890, 33]]
#    return bsm


class CLedStrand:
    def __init__(self, pin, lowest_led_number, highest_led_number):
        self.segment = 0
        self.meter15s = None

        self.Strand = neopixel.NeoPixel(machine.Pin(pin), highest_led_number - lowest_led_number + 1)
        self.iLowestLed = lowest_led_number
        self.iHighestLed = highest_led_number
        self.light_strand()

    def draw15s(self):
        if self.meter15s is not None:
            for x in range(-2, 2):
                self.Strand[self.meter15s[0] + x - 5] = (0, 0, 255)
                self.Strand[self.meter15s[1] + x - 5] = (0, 0, 255)

    def light_segment(self):
        print(f'{self.segment}')
        self.Strand.fill((0, 0, 0))
        self.draw15s()

        bsm = get_bottom_map()
        mark = bsm[self.segment]

        for x in range(mark[1], mark[2]):
            self.Strand[x] = (0, 255, 0)

        self.Strand.write()
        self.segment += 1
        if self.segment == len(bsm):
            self.segment = 0

    def light_strand(self):
        self.Strand.fill((0, 0, 0))
        for x in range(self.iLowestLed, self.iHighestLed, 5):
            self.Strand[x] = (255, 255, 255)
        self.Strand.write()

    def clear_strand(self):
        self.Strand.fill((0, 0, 0))
        self.draw15s()

        self.Strand.write()

    def ignite_led_location(self, led_location, color=(255, 255, 255)):
        if self.iLowestLed <= led_location <= self.iHighestLed:
            self.Strand.fill((0, 0, 0))
            self.Strand[led_location] = color
            self.Strand.write()

    def ignite_markers(self):
        self.Strand.fill((0, 0, 0))
        self.Strand.write()

        bsm = get_bottom_map()
        for mark in bsm:
            self.Strand[mark[1] + self.iLowestLed] = (0, 255, 0)
            self.Strand[mark[2] + self.iLowestLed] = (255, 0, 0)
        self.Strand.write()


# Index Defines for BottomSectionMap array field
DEPTH = 0
LEDSTART = 1
LEDEND = 2
FEET = 3


class SwimSet:
    def __init__(self, display, debug=True):
        self.ltime = None
        self.BottomSectionMap = None
        self.duration = None
        self.distance = None
        self.length = None
        self.interval = None
        self.repetitions = None
        self.seconds_per_length = None
        self.seconds_per_pixel = None
        self.ms_sleep = None
        self.ms_per_length = None
        self.ms_per_pixel = None
        self.ms_total_time = None
        self.TimeHacks = None
        self.lastPixel = None
        self.drawcount = None
        self.startTimeOfThisLength = None
        self.ltime = None
        self.currentPixel = None
        self.PipOn = None
        self.maxtimeindex = None
        self.currentPixel = None
        self.timeIndex = None
        self.staticStartTime = None
        self.laptimeadjustment = None
        self.lapcount = None
        self.drawcount = None
        self.startTimeOfThisLength = None
        self.lastPixel = None
        self.lastRepEnd = None
        self.lastPixel = None
        self.display = display
        self.Direction = True
        self.dimLevel = 1  # This is a percentage
        self.STRANDLENGTH = 910
        self.FIRSTPIXEL = 174
        self.Stopped = True
        self.debug = debug
        if debug:
            self.dimLevel = .1  # This is a percentage
            self.FIRSTPIXEL = 0
            self.STRANDLENGTH = 21
            # self.BottomSectionMap = [[1, 0, 3, 37.5], [2, 4, 7, 7.5], [3, 8, 10, 30]]

        self.numpix = self.STRANDLENGTH - self.FIRSTPIXEL

        self.LedStrand = CLedStrand(16, 0,
                                    self.STRANDLENGTH - 1)
        # numpix -1 is actually the highest pixel index, not the number of pixels

        self.Cursor = CCursor(self.LedStrand, (255, 255, 255), (255, 0, 0), self.dimLevel)

        self.ms_at_pixel_down = [0] * self.numpix
        self.ms_at_pixel_back = [0] * self.numpix

        self.lowestLed = 1000000
        self.highestLed = -1
        self.ms_buffer = [0] * 1000
        self.RunningMode = False

        self.AudioAlert = CAudioAlert()
        self.meter15s = None

    def use_audio(self, flag):
        self.AudioAlert.use_audio(flag)

    def qc(self, p):
        led = 0
        distance = 0.0
        for sectionMap in self.BottomSectionMap:
            if p > (distance + sectionMap[3]):
                distance += sectionMap[3]
            else:
                distance_remaining = p - distance
                ledsinsection = sectionMap[2] - sectionMap[1]
                ledslength = sectionMap[3] / ledsinsection
                print(f'{sectionMap}')
                print(f'{distance_remaining}, {sectionMap[3]}, {distance}, {ledsinsection}, {ledslength}')
                led = int(distance_remaining / sectionMap[3] * ledsinsection) + sectionMap[1]
                print(f'{led}')
                break
        return led

    def calc15_meter_locations(self):
        p2 = 49.2126
        p1 = 25.7874

        self.LedStrand.meter15s = [self.qc(p1), self.qc(p2)]

        print(f'{self.LedStrand.meter15s}')

    def set_bottom_times(self, duration=120, distance=200, interval=180, repetitions=20, length=25, direction=True):
        self.ltime = 0
        if direction:
            print("Near")
        else:
            print("Far")
        self.BottomSectionMap = get_bottom_map()
        self.Direction = direction
        self.duration = duration
        self.distance = distance
        self.length = length
        self.interval = interval
        self.repetitions = repetitions
        print(f'{self.duration}, {self.distance}, {self.length}')
        self.seconds_per_length = (self.duration / (self.distance / self.length))
        print(f'{self.seconds_per_length}, {self.numpix}')
        self.seconds_per_pixel = (self.seconds_per_length / self.numpix)
        self.ms_sleep = int(self.seconds_per_length * 0.99999999)
        self.ms_per_length = self.seconds_per_length * timescale
        self.ms_per_pixel = int(self.seconds_per_pixel * timescale)
        self.ms_total_time = self.duration * timescale

        duration = self.ms_per_length
        pool_length = self.length
        # print(self.duration)
        led = self.FIRSTPIXEL
        du = 0
        pool_length_in_feet = float(pool_length * 3.0)

        print(f'duration : {duration}')
        for section in self.BottomSectionMap:
            print("Sections : {section}")
            if section[LEDSTART] < self.lowestLed:
                self.lowestLed = section[LEDSTART]
            if self.highestLed <= section[LEDEND]:
                self.highestLed = section[LEDEND]
            percentage_of_length = float(float(section[FEET]) / pool_length_in_feet)
            section_duration = duration * percentage_of_length

            section_led_count = section[LEDEND] - section[LEDSTART]
            led_ms_step = section_duration / section_led_count
            # print ("percentage_of_length, section_duration, section_led_count, led_ms_step : ",percentage_of_length,
            # section_duration, section_led_count, led_ms_step)
            for loop in range(section[LEDSTART], section[LEDEND]):
                du += led_ms_step
                self.ms_buffer[led] = int(du)
                du = du % 1
                led += 1

        # self.ms_buffer[2] = 5000
        print(f'{self.FIRSTPIXEL}, {self.lowestLed}, {self.highestLed}')
        print(f'ms buffer : {self.ms_buffer}')

        self.TimeHacks = {True: [0] * 1000}
        for x in range(self.lowestLed, self.highestLed):
            self.TimeHacks[True][x] = self.ms_buffer[x] + self.TimeHacks[True][x - 1]

        self.TimeHacks[False] = [0] * 1000
        for x in range(self.highestLed, self.lowestLed, -1):
            self.TimeHacks[False][x] = self.ms_buffer[x] + self.TimeHacks[False][x + 1]

        print(gc.mem_alloc(), gc.mem_free(), gc.collect())
        print(gc.mem_alloc(), gc.mem_free())
        # logger.print(f'l buffer : {self.TimeHacks[True]}')

        print(gc.mem_alloc(), gc.mem_free(), gc.collect())
        print(gc.mem_alloc(), gc.mem_free())
        #        print(f'l buffer : {self.TimeHacks[False]}")

        self.calc15_meter_locations()

    def stop_set(self):
        self.RunningMode = False

    # noinspection PyPep8
    def direction_changed(self):

        self.Direction = not self.Direction
        self.lapcount += 1
        if self.currentPixel != self.lastPixel:
            self.lastPixel = self.currentPixel
            self.drawcount += 1
            self.Cursor.draw(self.currentPixel, self.PipOn)

        print(
            f'Direction Changed : {self.lapcount} {self.ms_per_length} {time.ticks_ms()} {self.startTimeOfThisLength} {time.ticks_diff(time.ticks_ms(), self.startTimeOfThisLength)} {self.drawcount}')
        self.drawcount = 0

        delay = int(self.ms_per_length - time.ticks_diff(time.ticks_ms(), self.startTimeOfThisLength))
        print(f'delay : {delay}')
        time.sleep_ms(delay)
        self.startTimeOfThisLength = time.ticks_ms()
        ltime = time.ticks_ms()
        print(f'timehack {time.ticks_diff(ltime, self.ltime)} {self.Cursor.pixelCount}')
        self.Cursor.pixelCount = 0
        self.ltime = ltime

    def next_pixel(self):
        # print(self.accumulatedTime, self.Direction, self.timeIndex, self.ms_buffer[self.timeIndex])
        return_value = True
        current_pace = time.ticks_diff(time.ticks_ms(), self.startTimeOfThisLength)
        #       print(f'in : {current_pace} {self.TimeHacks[True][self.currentPixel]} {self.currentPixel}")
        if self.Direction:
            while current_pace > self.TimeHacks[True][self.currentPixel]:
                self.currentPixel += 1
                if self.currentPixel > self.maxtimeindex:
                    self.currentPixel = self.maxtimeindex
                    self.direction_changed()
                    return_value = False

                    break
        else:
            while current_pace > self.TimeHacks[False][self.currentPixel]:
                self.currentPixel -= 1
                if self.currentPixel < self.lowestLed:
                    self.currentPixel = self.lowestLed
                    self.direction_changed()
                    return_value = False
                    break
        #        print(f'out : {current_pace} {self.TimeHacks[True][self.currentPixel]} {self.currentPixel}")
        return return_value

    def rep(self):
        self.PipOn = True

        self.maxtimeindex = self.highestLed
        self.currentPixel = self.lowestLed
        if not self.Direction:
            self.timeIndex = self.maxtimeindex

        print(f'Direction Change : {self.Direction}')
        print(f'Rep starting: {self.currentPixel}')
        self.AudioAlert.beep()

        start_time = time.ticks_ms()  # Pycharm needs a *1000
        self.staticStartTime = start_time

        self.laptimeadjustment = 0
        self.lapcount = 0
        self.drawcount = 0

        self.startTimeOfThisLength = time.ticks_ms()
        while self.RunningMode:
            if time.ticks_diff(time.ticks_ms(), self.staticStartTime) >= self.ms_total_time:
                break
            self.next_pixel()
            if self.currentPixel != self.lastPixel:
                self.lastPixel = self.currentPixel
                self.drawcount += 1
                self.Cursor.draw(self.currentPixel, self.PipOn)

        self.lastRepEnd = time.ticks_ms()
        self.LedStrand.clear_strand()

    def loop(self):
        self.Stopped = False
        self.RunningMode = True
        self.lastPixel = -1
        reps = 0
        while self.RunningMode and (self.repetitions == 0 or reps < self.repetitions):
            self.display.fill(self.display.black)
            self.display.text("FTL Fish v2.0", 1, 2, self.display.white)
            # self.OLED.text(netstr[0],1,12,self.OLED.white)
            self.display.text(f'Status: {reps} of {self.repetitions}', 1, 22, self.display.white)
            self.display.show()

            start_time = time.ticks_ms()

            self.rep()

            if self.RunningMode:
                reps += 1

                elapsed_time = time.ticks_diff(time.ticks_ms(), start_time)
                print(f'{self.interval}, {elapsed_time}')
                rest_interval = (self.interval * timescale - elapsed_time) / timescale

                print(f'{reps} of {self.repetitions} repetitions completed.')

                if rest_interval < 0:
                    print('Slow poke, elapsed_time exceeded the interval!')
                    # should validate this on input and not allow it to happen
                    print('No rest for you!')
                else:
                    if reps < self.repetitions:
                        print(f'Resting Interval : {rest_interval}')
                        time.sleep(rest_interval)

        self.Stopped = False
        self.display.fill(self.display.black)
        self.display.text("FTL Fish v2.0", 1, 2, self.display.white)
        # self.OLED.text(netstr[0],1,12,self.OLED.white)
        self.display.text("Status: Idle", 1, 22, self.display.white)
        self.display.show()


if __name__ == "__main__":
    s = displays.get_display()
    s.LedStrand.IgniteMarkers(s.debug)
    # s.SetBottomTimes(duration=120, distance = 200, interval = 150, repetitions = 0, length=25)
    s.SetBottomTimes(duration=120, distance=200, interval=150, repetitions=10, length=25, direction=True)
    s.Loop()
