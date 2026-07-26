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
        self.current_rep_target_seconds = None
        self.strategy = 'even'
        self.variation = 0.08
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
        self.completed_reps = 0
        self.next_display_update_ms = 0
        self.beep_lead_ms = 0
        self.next_rep_start_ms = None
        self.in_rep = False
        self.rep_interrupted = False
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
        self.rep_plan_ms = []
        self.length_index = 0
        self.current_length_ms = 0
        self.pixel_step_fraction = [0.0] * self.STRANDLENGTH
        self.PixelProgress = None

    def use_audio(self, flag):
        self.AudioAlert.use_audio(flag)

    @staticmethod
    def format_seconds(seconds):
        if seconds is None:
            return '--'
        seconds = max(0, int(round(seconds)))
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f'{minutes}:{remaining_seconds:02d}'

    @staticmethod
    def format_target_seconds(seconds):
        if seconds is None:
            return '--'
        seconds = max(0.0, float(seconds))
        minutes = int(seconds // 60)
        remaining_seconds = seconds - (minutes * 60)
        if minutes == 0:
            return f'{remaining_seconds:.1f}'
        return f'{minutes}:{remaining_seconds:04.1f}'

    def seconds_until_next_rep(self):
        if not self.RunningMode or self.staticStartTime is None:
            return None
        if self.repetitions and self.completed_reps >= self.repetitions:
            return None
        if self.repetitions and self.in_rep and self.completed_reps + 1 >= self.repetitions:
            return None

        if self.next_rep_start_ms is not None:
            return max(0, time.ticks_diff(self.next_rep_start_ms, time.ticks_ms()) / timescale)

        target_seconds = self.current_rep_target_seconds if self.repetitions == 0 else self.interval
        return max(0, target_seconds - (time.ticks_diff(time.ticks_ms(), self.staticStartTime) / timescale))

    def current_target_duration_seconds(self):
        if self.current_rep_target_seconds:
            return self.current_rep_target_seconds
        if not self.length_plan_ms:
            return self.duration
        length_index = self.length_index
        if length_index < 0:
            length_index = 0
        elif length_index >= len(self.length_plan_ms):
            length_index = len(self.length_plan_ms) - 1
        return self.length_plan_ms[length_index] / timescale

    def update_set_display(self, status_line=None, force=False):
        now = time.ticks_ms()
        if not force and time.ticks_diff(now, self.next_display_update_ms) < 0:
            return
        self.next_display_update_ms = now + 500

        target_duration = self.format_target_seconds(self.current_target_duration_seconds())
        next_rep = self.format_seconds(self.seconds_until_next_rep())
        rep_text = f'Rep:{self.completed_reps + 1}'
        if self.repetitions:
            rep_text = f'Rep:{min(self.completed_reps + 1, self.repetitions)}/{self.repetitions}'
        if status_line is None:
            status_line = f'{rep_text} N:{next_rep}'
            if self.repetitions and self.completed_reps + 1 >= self.repetitions:
                status_line = f'{rep_text} Final'
        elif not status_line.startswith('Rep:'):
            status_line = f'{rep_text} {status_line}'

        self.display.fill(self.display.black)
        self.display.text("FTL Fish v2.0", 1, 2, self.display.white)
        self.display.text(f'Dist:{self.distance} Tgt:{target_duration}', 1, 12, self.display.white)
        self.display.text(status_line, 1, 22, self.display.white)
        self.display.show()

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

    def build_rep_plan(self, first_duration, repetitions, strategy='even', last_duration=None):
        strategy_key = (strategy or 'even').lower().replace('-', '_').replace(' ', '_')
        if strategy_key != 'negative_split' or repetitions <= 1 or last_duration is None:
            return [first_duration]

        step = (last_duration - first_duration) / (repetitions - 1)
        return [first_duration + (step * index) for index in range(repetitions)]

    def build_length_plan(self, total_duration, length_count, strategy='even', variation=0.08):
        strategy_key = (strategy or 'even').lower().replace('-', '_').replace(' ', '_')
        if length_count <= 0:
            return []
        if variation < 0:
            variation = 0
        elif variation > 0.45:
            variation = 0.45

        weights = [1.0] * length_count
        if strategy_key == 'surge' and length_count > 1:
            for index in range(length_count):
                if index % 2 == 0:
                    weights[index] = 1.0 - variation
                else:
                    weights[index] = 1.0 + variation

        total_weight = sum(weights)
        return [total_duration * weight / total_weight for weight in weights]

    def set_bottom_times(self, duration=120, distance=200, interval=180, repetitions=20, length=25, direction=True,
                         pool='Bellevue East', strategy='even', variation=0.08, last_duration=None):
        self.ltime = 0
        self.completed_reps = 0
        self.next_rep_start_ms = None
        self.in_rep = False
        self.rep_interrupted = False
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
        self.strategy = strategy
        self.variation = variation
        self.length_index = 0
        length_count = max(1, int(round(float(distance) / float(length))))
        self.rep_plan_ms = [int(seconds * timescale) for seconds in self.build_rep_plan(
            float(duration), repetitions, strategy, last_duration
        )]
        self.current_rep_target_seconds = self.rep_plan_ms[0] / timescale
        length_plan_seconds = self.build_length_plan(self.current_rep_target_seconds, length_count, strategy, variation)
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

    def sleep_until_next_beep(self, next_start_ms):
        while self.RunningMode:
            beep_start_ms = next_start_ms - self.beep_lead_ms
            remaining_ms = time.ticks_diff(beep_start_ms, time.ticks_ms())
            if remaining_ms <= 0:
                break
            self.update_set_display()
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
        self.rep_interrupted = False

        self.maxtimeindex = self.highestLed
        self.currentPixel = self.lowestLed
        if not self.Direction:
            self.currentPixel = self.maxtimeindex
            self.timeIndex = self.maxtimeindex

        self.length_index = 0
        length_count = len(self.length_plan_ms) or max(1, int(round(float(self.distance) / float(self.length))))
        if self.rep_plan_ms:
            rep_index = self.completed_reps
            if rep_index >= len(self.rep_plan_ms):
                rep_index = len(self.rep_plan_ms) - 1
            self.current_rep_target_seconds = self.rep_plan_ms[rep_index] / timescale
            length_plan_seconds = self.build_length_plan(
                self.current_rep_target_seconds,
                length_count,
                self.strategy,
                self.variation,
            )
            self.length_plan_ms = [int(seconds * timescale) for seconds in length_plan_seconds]
        self.current_length_ms = self.length_plan_ms[0]
        print(f'Direction Change : {self.Direction}')
        print(f'Rep starting: {self.currentPixel}')
        beep_start_ms = time.ticks_ms()
        self.AudioAlert.beeps(threeBeeps)
        self.beep_lead_ms = max(0, time.ticks_diff(time.ticks_ms(), beep_start_ms))

        start_time = time.ticks_ms()  # Pycharm needs a *1000
        self.staticStartTime = start_time
        self.next_rep_start_ms = self.staticStartTime + int(self.interval * timescale)
        self.in_rep = True

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
            self.update_set_display()

        self.lastRepEnd = time.ticks_ms()
        self.rep_interrupted = not self.RunningMode
        self.in_rep = False
        self.LedStrand.clear_strand()

    def loop(self):
        self.Stopped = False
        self.RunningMode = True
        self.lastPixel = -1
        reps = int(self.completed_reps or 0)
        try:
            while self.RunningMode and (self.repetitions == 0 or reps < self.repetitions):
                self.completed_reps = reps
                self.update_set_display(f'Rep:{reps + 1}/{self.repetitions}', force=True)

                start_time = time.ticks_ms()

                self.rep()

                if self.RunningMode:
                    next_start_ms = self.next_rep_start_ms
                    reps += 1
                    self.completed_reps = reps

                    elapsed_time = time.ticks_diff(time.ticks_ms(), start_time)
                    print(f'{self.interval}, {elapsed_time}')
                    rest_interval = 0
                    if next_start_ms is not None:
                        rest_interval = time.ticks_diff(next_start_ms - self.beep_lead_ms, time.ticks_ms()) / timescale

                    print(f'{reps} of {self.repetitions} repetitions completed.')

                    if rest_interval < 0:
                        print('Slow poke, elapsed_time exceeded the next beep start!')
                        # should validate this on input and not allow it to happen
                        print('No rest for you!')
                    else:
                        if reps < self.repetitions:
                            print(f'Resting Interval : {rest_interval}')
                            self.update_set_display(force=True)
                            self.sleep_until_next_beep(next_start_ms)
                elif self.rep_interrupted:
                    reps += 1
                    self.completed_reps = reps
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
        reps = int(self.completed_reps or 0)
        direction = self.Direction
        try:
            while self.RunningMode:
                self.completed_reps = reps
                self.update_set_display(f'Rep:{reps + 1}', force=True)

                start_time = time.ticks_ms()
                self.rep(threeBeeps=False)
                self.Direction = direction
                if self.RunningMode:
                    reps += 1
                    self.completed_reps = reps

                    elapsed_time = time.ticks_diff(time.ticks_ms(), start_time)
                    print(f'{self.interval}, {elapsed_time}')

                    print(f'{reps} repetitions completed.')
                elif self.rep_interrupted:
                    reps += 1
                    self.completed_reps = reps
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
