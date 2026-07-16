# import gc
# import array
# import random
# import sys
# import os
import gc
import json
import time

import displays
from audioalert import CAudioAlert
from ledcursor import CCursor
from runtime_support import get_machine_module, get_neopixel_module, patch_time_module, project_path


patch_time_module()
machine = get_machine_module()
neopixel = get_neopixel_module()

timescale = 1000


class poolDefinitions:
    def _init__(self):
        self.bcms = []
        self.load()

    def load(self):
        with open(project_path('/db/pools.json'), 'rt') as f:
            # noinspection PyTypeChecker
            self.bcms = json.load(f)
        return self.bcms
    
class PoolData:
    def __init__(self, filename):
        self.filename = filename
        self.data = self.load_data()
        print(self.data)
        self.defaultPool = self.data['defaultPool']
        print(self.defaultPool)

    
    def load_data(self):
        try:
            with open(self.filename, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            print(f"File '{self.filename}' not found.")
            return {}

    def get_pool_data(self, pool_name):
        if pool_name in self.data.get('pools', {}):
            return self.data['pools'][pool_name]
        else:
            return None

    def get_corrected_bcm(self, pool_name):
        pool = self.get_pool_data(pool_name)

        PixelCount = pool['PixelCount']
        poolLength = 164.042  # default is 50 meters (in feet)
        if pool['Length'] == '25 yards':
            poolLength = 75.0
        Segments = pool['Segments']

        MaxPixels = 0 
        with open(project_path('/db/lastled.dat'), "r") as file:
            content = file.readline()
            print(f"lastled = {content}")
            MaxPixels = int(content)

        bcm = []
        print(PixelCount)
        for segment in Segments:
            s = [0,0,0,0,0]
            s[0] = 0
            s[1] = segment['FirstPixel']
            s[2] = PixelCount
            s[3] = segment['Distance']
            print(s)
            bcm.append(s)

        for i in range(len(bcm) - 1):
            bcm[i][2] = bcm[i + 1][1] - 1
        for i in range(len(bcm)):
            bcm[i][4] = bcm[i][2]-bcm[i][1]

        finalBcm = [row[:] for row in bcm]

        for i in range(len(finalBcm)-1, -1, -1):
            finalBcm[i][2] = MaxPixels
            MaxPixels = MaxPixels - finalBcm[i][4]
            finalBcm[i][1] = MaxPixels
            MaxPixels = MaxPixels - 1
            del finalBcm[i][4]
                        
        total = 0;
        for i in range(len(finalBcm)):
            print(i)
            if i == len(finalBcm) -1:
                finalBcm[i][3] = poolLength - total
            else:
                finalBcm[i][3] = finalBcm[i+1][3] - finalBcm[i][3]
                total += finalBcm[i][3]

            print(f'{finalBcm[i][3]}')
            

        print(bcm)
        print(finalBcm)
        return finalBcm
 
def get_bottom_map(pool = None):
    pools = PoolData(project_path('/db/pools.json'))
    if pool == None:
        pool = pools.defaultPool
    bcm = pools.get_corrected_bcm(pool)
    return bcm


class CLedStrand:
    def __init__(self, pin, lowest_led_number, highest_led_number):
        self.segment = 0
        self.meter15s = None

        self.Strand = neopixel.NeoPixel(machine.Pin(pin), highest_led_number - lowest_led_number + 1, timing=1)
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
        self.ms_buffer = [0] * self.STRANDLENGTH
        self.RunningMode = False

        self.AudioAlert = CAudioAlert()
        self.meter15s = None
        self.length_plan_ms = []
        self.length_index = 0
        self.current_length_ms = 0
        self.pixel_step_fraction = [0.0] * self.STRANDLENGTH
        self.PixelProgress = None

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

        print(f'15 meter leds = {self.LedStrand.meter15s}')

    def build_length_plan(self, total_duration, length_count, strategy='even', variation=0.08):
        strategy_key = (strategy or 'even').lower().replace('-', '_').replace(' ', '_')
        if length_count <= 0:
            return []
        if variation < 0:
            variation = 0
        elif variation > 0.45:
            variation = 0.45

        weights = [1.0] * length_count
        if strategy_key == 'negative_split' and length_count > 1:
            midpoint = (length_count - 1) / 2.0
            for index in range(length_count):
                if midpoint == 0:
                    weights[index] = 1.0
                else:
                    offset = (index - midpoint) / midpoint
                    weights[index] = 1.0 - (variation * offset)
        elif strategy_key == 'surge' and length_count > 1:
            for index in range(length_count):
                if index % 2 == 0:
                    weights[index] = 1.0 - variation
                else:
                    weights[index] = 1.0 + variation

        total_weight = sum(weights)
        return [total_duration * weight / total_weight for weight in weights]

    def set_bottom_times(self, duration=120, distance=200, interval=180, repetitions=20, length=25, direction=True,
                         pool='Bellevue East', strategy='even', variation=0.08):
        self.ltime = 0
        if direction:
            print("Near")
        else:
            print("Far")
        self.BottomSectionMap = get_bottom_map(pool)
        self.Direction = direction
        self.duration = duration
        self.distance = distance
        self.length = length
        self.interval = interval
        self.repetitions = repetitions
        self.length_index = 0
        length_count = max(1, int(round(float(distance) / float(length))))
        length_plan_seconds = self.build_length_plan(float(duration), length_count, strategy, variation)
        self.length_plan_ms = [int(seconds * timescale) for seconds in length_plan_seconds]
        print(f'dur-dis-lenth {self.duration}, {self.distance}, {self.length}')
        self.seconds_per_length = (self.duration / length_count)
        print(f'secs per length - numpix {self.seconds_per_length}, {self.numpix}')
        self.seconds_per_pixel = (self.seconds_per_length / self.numpix)
        self.ms_sleep = int(self.seconds_per_length * 0.99999999)
        self.ms_per_length = self.seconds_per_length * timescale
        self.ms_per_pixel = int(self.seconds_per_pixel * timescale)
        self.ms_total_time = self.duration * timescale
        self.current_length_ms = self.length_plan_ms[0]
        self.lowestLed = 1000000
        self.highestLed = -1
        self.ms_buffer = [0] * self.STRANDLENGTH

        pool_length = self.length
        du = 0.0
        pool_length_in_feet = float(pool_length * 3.0)

        print(f'length plan ms : {self.length_plan_ms}')
        for section in self.BottomSectionMap:
            print(f"Sections : {section}")
            section_led_count = section[LEDEND] - section[LEDSTART]
            if section_led_count <= 0:
                raise ValueError(f'Invalid pool section LED range: {section}')
            if section[LEDSTART] < self.lowestLed:
                self.lowestLed = section[LEDSTART]
            if self.highestLed <= section[LEDEND]:
                self.highestLed = section[LEDEND]

        timing_size = max(self.STRANDLENGTH, self.highestLed + 1)
        self.pixel_step_fraction = [0.0] * timing_size
        led = self.FIRSTPIXEL
        for section in self.BottomSectionMap:
            percentage_of_length = float(float(section[FEET]) / pool_length_in_feet)

            section_led_count = section[LEDEND] - section[LEDSTART]
            led_step_fraction = percentage_of_length / section_led_count
            for loop in range(section[LEDSTART], section[LEDEND]):
                if led >= len(self.pixel_step_fraction):
                    self.pixel_step_fraction.extend([0.0] * (led - len(self.pixel_step_fraction) + 1))
                du += led_step_fraction
                self.pixel_step_fraction[led] = led_step_fraction
                led += 1

        print(f'{self.FIRSTPIXEL}, {self.lowestLed}, {self.highestLed}')
        print(f'pixel timing entries : {len(self.pixel_step_fraction)}')

        timing_size = max(len(self.pixel_step_fraction), self.highestLed + 1)
        self.TimeHacks = {True: [0.0] * timing_size}
        cumulative = 0.0
        for x in range(self.lowestLed, self.highestLed):
            cumulative += self.pixel_step_fraction[x]
            self.TimeHacks[True][x] = cumulative

        self.TimeHacks[False] = [0.0] * timing_size
        cumulative = 0.0
        self.TimeHacks[False][self.highestLed] = 0.0
        for x in range(self.highestLed - 1, self.lowestLed - 1, -1):
            cumulative += self.pixel_step_fraction[x]
            self.TimeHacks[False][x] = cumulative

        if hasattr(gc, 'mem_alloc') and hasattr(gc, 'mem_free'):
            print(gc.mem_alloc(), gc.mem_free(), gc.collect())
            print(gc.mem_alloc(), gc.mem_free())

            print(gc.mem_alloc(), gc.mem_free(), gc.collect())
            print(gc.mem_alloc(), gc.mem_free())
        else:
            gc.collect()
        #        print(f'l buffer : {self.TimeHacks[False]}")

        self.calc15_meter_locations()
        print(f'timehack entries : {len(self.TimeHacks[True])}')

    def stop_set(self):
        self.RunningMode = False

    def sleep_rest_interval(self, rest_interval):
        end_time = time.ticks_ms() + int(rest_interval * timescale)
        while self.RunningMode:
            remaining_ms = time.ticks_diff(end_time, time.ticks_ms())
            if remaining_ms <= 0:
                break
            time.sleep(min(0.1, remaining_ms / timescale))

    # noinspection PyPep8
    def direction_changed(self):
        self.Direction = not self.Direction
        self.lapcount += 1
        if self.currentPixel != self.lastPixel:
            self.lastPixel = self.currentPixel
            self.drawcount += 1
            self.Cursor.draw(self.currentPixel, self.PipOn)

        print(
            f'Direction Changed : {self.lapcount} {self.current_length_ms} {time.ticks_ms()} {self.startTimeOfThisLength} {time.ticks_diff(time.ticks_ms(), self.startTimeOfThisLength)} {self.drawcount}')
        self.drawcount = 0

        delay = int(self.current_length_ms - time.ticks_diff(time.ticks_ms(), self.startTimeOfThisLength))
        print(f'delay : {delay}')
        if delay > 0:
            time.sleep_ms(delay)

        if self.length_index + 1 >= len(self.length_plan_ms):
            return False

        self.length_index += 1
        self.current_length_ms = self.length_plan_ms[self.length_index]
        self.startTimeOfThisLength = time.ticks_ms()
        ltime = time.ticks_ms()
        print(f'timehack {time.ticks_diff(ltime, self.ltime)} {self.Cursor.pixelCount}')
        self.Cursor.pixelCount = 0
        self.ltime = ltime
        return True

    def next_pixel(self):
        # print(self.accumulatedTime, self.Direction, self.timeIndex, self.ms_buffer[self.timeIndex])
        return_value = True
        current_pace = time.ticks_diff(time.ticks_ms(), self.startTimeOfThisLength)
        #       print(f'in : {current_pace} {self.TimeHacks[True][self.currentPixel]} {self.currentPixel}")
        if self.Direction:
            while current_pace > (self.TimeHacks[True][self.currentPixel] * self.current_length_ms):
                self.currentPixel += 1
                if self.currentPixel > self.maxtimeindex:
                    self.currentPixel = self.maxtimeindex
                    return_value = self.direction_changed()

                    break
        else:
            while current_pace > (self.TimeHacks[False][self.currentPixel] * self.current_length_ms):
                self.currentPixel -= 1
                if self.currentPixel < self.lowestLed:
                    self.currentPixel = self.lowestLed
                    return_value = self.direction_changed()
                    break
        #        print(f'out : {current_pace} {self.TimeHacks[True][self.currentPixel]} {self.currentPixel}")
        return return_value

    def rep(self, threeBeeps=True):
        self.PipOn = True

        self.maxtimeindex = self.highestLed
        self.currentPixel = self.lowestLed
        if not self.Direction:
            self.currentPixel = self.maxtimeindex
            self.timeIndex = self.maxtimeindex

        self.length_index = 0
        self.current_length_ms = self.length_plan_ms[0]
        print(f'Direction Change : {self.Direction}')
        print(f'Rep starting: {self.currentPixel}')
        self.AudioAlert.beeps(threeBeeps)

        start_time = time.ticks_ms()  # Pycharm needs a *1000
        self.staticStartTime = start_time

        self.laptimeadjustment = 0
        self.lapcount = 0
        self.drawcount = 0

        self.startTimeOfThisLength = time.ticks_ms()
        while self.RunningMode:
            if self.length_index >= len(self.length_plan_ms):
                break
            if not self.next_pixel():
                break
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
        try:
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
                            self.sleep_rest_interval(rest_interval)
        finally:
            self.RunningMode = False
            self.Stopped = True
            self.display.fill(self.display.black)
            self.display.text("FTL Fish v2.0", 1, 2, self.display.white)
            # self.OLED.text(netstr[0],1,12,self.OLED.white)
            self.display.text("Status: Idle", 1, 22, self.display.white)
            self.display.show()




    def sprintloop(self):
        self.Stopped = False
        self.RunningMode = True
        self.lastPixel = -1
        reps = 0
        direction = self.Direction
        try:
            while self.RunningMode:
                self.display.fill(self.display.black)
                self.display.text("FTL Fish v2.0", 1, 2, self.display.white)
                # self.OLED.text(netstr[0],1,12,self.OLED.white)
                self.display.text(f'Infinite Sprint Mode', 1, 22, self.display.white)
                self.display.show()

                start_time = time.ticks_ms()
                self.rep(threeBeeps=False)
                self.Direction = direction
                if self.RunningMode:
                    reps += 1

                    elapsed_time = time.ticks_diff(time.ticks_ms(), start_time)
                    print(f'{self.interval}, {elapsed_time}')

                    print(f'{reps} repetitions completed.')
        finally:
            self.RunningMode = False
            self.Stopped = True
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
