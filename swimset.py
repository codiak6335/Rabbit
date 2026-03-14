# import gc
# import array
# import random
# import sys
# import os
import gc
import json
import time

import machine
import neopixel

import displays
# import random
from audioalert import CAudioAlert
from ledcursor import CCursor

timescale = 1000


def print_gc_stats():
    collect_result = gc.collect()
    if hasattr(gc, "mem_alloc") and hasattr(gc, "mem_free"):
        print(gc.mem_alloc(), gc.mem_free(), collect_result)
        print(gc.mem_alloc(), gc.mem_free())
    else:
        print(f"gc.collect() -> {collect_result}")


class poolDefinitions:
    def _init__(self):
        self.bcms = []
        self.load()

    def load(self):
        with open('/db/pools.json', 'rt') as f:
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
        if pool is None:
            raise ValueError(f"Pool '{pool_name}' was not found in pool definitions")

        PixelCount = pool['PixelCount']
        poolLength = 164.042  # default is 50 meters (in feet)
        if pool['Length'] == '25 yards':
            poolLength = 75.0
        Segments = pool['Segments']

        MaxPixels = 0 
        with open('/db/lastled.dat', "r") as file:
            content = file.readline()
            print(f"lastled = {content}")
            MaxPixels = int(content)

        bcm = []
        print(PixelCount)
        for i, segment in enumerate(Segments):
            first_pixel = (
                segment.get('FirstPixel')
                if isinstance(segment, dict)
                else None
            )
            if first_pixel is None and isinstance(segment, dict):
                first_pixel = segment.get('firstPixel', segment.get('first_pixel'))

            distance = (
                segment.get('Distance')
                if isinstance(segment, dict)
                else None
            )
            if distance is None and isinstance(segment, dict):
                distance = segment.get('distance')

            if first_pixel is None or distance is None:
                print(f"Skipping invalid segment at index {i} for pool '{pool_name}': {segment}")
                continue

            s = [0,0,0,0,0]
            s[0] = 0
            s[1] = int(first_pixel)
            s[2] = PixelCount
            s[3] = float(distance)
            print(s)
            bcm.append(s)

        if len(bcm) == 0:
            raise ValueError(f"Pool '{pool_name}' has no valid segments with FirstPixel/Distance")

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
    pools = PoolData('./db/pools.json')
    if pool == None:
        pool = pools.defaultPool
    bcm = pools.get_corrected_bcm(pool)
    return bcm


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

        self.Cursors = [
            CCursor(self.LedStrand, (255, 255, 255), (255, 0, 0), self.dimLevel),
            CCursor(self.LedStrand, (255, 255, 255), (0, 255, 0), self.dimLevel),
            CCursor(self.LedStrand, (255, 255, 255), (0, 0, 255), self.dimLevel),
        ]
        self.Cursor = self.Cursors[0]
        self.cursor_count = 1
        self.pace_cursor_durations = [120, 120, 120]
        self.sprint_cursor_durations = [120, 120, 120]
        self.pace_cursor_count = 1
        self.sprint_cursor_count = 1
        self.pace_stagger = True
        self._time_profile_cache = {}

        self.ms_at_pixel_down = [0] * self.numpix
        self.ms_at_pixel_back = [0] * self.numpix

        self.lowestLed = 1000000
        self.highestLed = -1
        self.ms_buffer = [0] * 1000
        self.RunningMode = False

        self.AudioAlert = CAudioAlert()
        self.meter15s = None

    @staticmethod
    def _normalize_repetitions(repetitions):
        if repetitions is None:
            return 0
        try:
            value = int(repetitions)
        except (TypeError, ValueError):
            return 0
        return value if value >= 0 else 0

    @staticmethod
    def _normalize_duration_list(values, default_value):
        result = [default_value, default_value, default_value]
        if values is None:
            return result
        for i in range(3):
            if i >= len(values):
                break
            try:
                v = int(values[i])
            except (TypeError, ValueError):
                continue
            if v > 0:
                result[i] = v
        return result

    @staticmethod
    def _duration_count(values):
        if values is None:
            return 1
        count = 0
        for i in range(3):
            if i >= len(values):
                break
            try:
                v = int(values[i])
            except (TypeError, ValueError):
                continue
            if v > 0:
                count += 1
        return count if count > 0 else 1

    def configure_cursors(self, pace_durations=None, sprint_durations=None):
        # Additional cursors are enabled only when additional durations are provided.
        self.pace_cursor_count = self._duration_count(pace_durations)
        self.sprint_cursor_count = self._duration_count(sprint_durations)
        self.cursor_count = max(self.pace_cursor_count, self.sprint_cursor_count)
        self.pace_cursor_durations = self._normalize_duration_list(pace_durations, int(self.duration or 120))
        self.sprint_cursor_durations = self._normalize_duration_list(sprint_durations, int(self.duration or 120))
        self._time_profile_cache = {}
        print(
            f'Configured cursors: pace_count={self.pace_cursor_count} '
            f'sprint_count={self.sprint_cursor_count} pace={self.pace_cursor_durations} '
            f'sprint={self.sprint_cursor_durations}'
        )

    def set_pace_stagger(self, pace_stagger):
        self.pace_stagger = bool(pace_stagger)
        print(f'Configured pace stagger: {self.pace_stagger}')

    def is_prepared(self):
        required = (
            self.BottomSectionMap,
            self.duration,
            self.distance,
            self.length,
            self.interval,
            self.ms_total_time,
            self.ms_per_length,
            self.ms_per_pixel,
        )
        if any(value is None for value in required):
            return False
        return self.length > 0 and self.distance > 0 and self.interval >= 0

    def sleep_interruptible(self, seconds):
        end_time = time.ticks_ms() + int(seconds * 1000)
        while self.RunningMode and time.ticks_diff(end_time, time.ticks_ms()) > 0:
            remaining_ms = time.ticks_diff(end_time, time.ticks_ms())
            step_ms = 100 if remaining_ms > 100 else remaining_ms
            time.sleep_ms(step_ms)

    @staticmethod
    def _format_countdown(seconds):
        if seconds < 60:
            return f'{seconds}s'
        minutes = seconds // 60
        secs = seconds % 60
        return f'{minutes}:{secs:02d}'

    def _rep_status_text(self, rep_number, completed=False):
        if self.repetitions == 0:
            return f'Done rep: {rep_number}' if completed else f'Rep: {rep_number}'
        if completed:
            return f'Done: {rep_number}/{self.repetitions}'
        return f'Rep: {rep_number}/{self.repetitions}'

    @staticmethod
    def _format_elapsed(seconds):
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        return f'{minutes}:{remaining_seconds:02d}'

    def run_rest_countdown(self, rest_seconds, reps_completed):
        rest_ms = int(rest_seconds * timescale)
        end_time = time.ticks_ms() + rest_ms
        last_shown = -1

        while self.RunningMode:
            remaining_ms = time.ticks_diff(end_time, time.ticks_ms())
            if remaining_ms <= 0:
                break

            remaining_seconds = (remaining_ms + 999) // 1000
            if remaining_seconds != last_shown:
                self.display.fill(self.display.black)
                self.display.text("FTL Fish v2.0", 1, 2, self.display.white)
                self.display.text(self._rep_status_text(reps_completed, completed=True), 1, 12, self.display.white)
                self.display.text(f'Next start: {self._format_countdown(remaining_seconds)}', 1, 22, self.display.white)
                self.display.show()
                last_shown = remaining_seconds

            step_ms = 100 if remaining_ms > 100 else remaining_ms
            time.sleep_ms(step_ms)

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

    def set_bottom_times(self, duration=120, distance=200, interval=180, repetitions=20, length=25, direction=True, pool = 'Bellevue East'):
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
        self.repetitions = self._normalize_repetitions(repetitions)
        print(f'dur-dis-lenth {self.duration}, {self.distance}, {self.length}')
        self.seconds_per_length = (self.duration / (self.distance / self.length))
        print(f'secs per length - numpix {self.seconds_per_length}, {self.numpix}')
        self.seconds_per_pixel = (self.seconds_per_length / self.numpix)
        self.ms_sleep = int(self.seconds_per_length * 0.99999999)
        self.ms_per_length = self.seconds_per_length * timescale
        self.ms_per_pixel = int(self.seconds_per_pixel * timescale)
        self.ms_total_time = self.duration * timescale
        self.configure_cursors(self.pace_cursor_durations, self.sprint_cursor_durations)

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

            section_led_count = section[LEDEND] - section[LEDSTART] + 1
            led_ms_step = section_duration / section_led_count
            # print ("percentage_of_length, section_duration, section_led_count, led_ms_step : ",percentage_of_length,
            # section_duration, section_led_count, led_ms_step)
            for loop in range(section[LEDSTART], section[LEDEND] + 1):
                du += led_ms_step
                self.ms_buffer[led] = int(du)
                du = du % 1
                led += 1

        # self.ms_buffer[2] = 5000
        print(f'{self.FIRSTPIXEL}, {self.lowestLed}, {self.highestLed}')
        print(f'ms buffer : {self.ms_buffer}')

        self.TimeHacks = {True: [0] * 1000}
        for x in range(self.lowestLed, self.highestLed + 1):
            self.TimeHacks[True][x] = self.ms_buffer[x] + self.TimeHacks[True][x - 1]

        self.TimeHacks[False] = [0] * 1000
        for x in range(self.highestLed, self.lowestLed - 1, -1):
            self.TimeHacks[False][x] = self.ms_buffer[x] + self.TimeHacks[False][x + 1]

        print_gc_stats()
        print_gc_stats()
        #        print(f'l buffer : {self.TimeHacks[False]}")

        self.calc15_meter_locations()
        print(f'timehacks : {self.TimeHacks}')

    def _create_time_profile(self, duration_seconds):
        duration_seconds = int(duration_seconds)
        if duration_seconds <= 0:
            duration_seconds = int(self.duration or 1)

        cache_key = duration_seconds
        if cache_key in self._time_profile_cache:
            return self._time_profile_cache[cache_key]

        base_duration = int(self.duration or duration_seconds or 1)
        if base_duration <= 0:
            base_duration = 1
        scale = float(duration_seconds) / float(base_duration)

        ms_per_length = int(self.ms_per_length * scale)
        if ms_per_length < 1:
            ms_per_length = 1

        hacks_true = [0] * 1000
        hacks_false = [0] * 1000
        for x in range(self.lowestLed, self.highestLed + 1):
            hacks_true[x] = int(self.TimeHacks[True][x] * scale)
        for x in range(self.lowestLed, self.highestLed + 1):
            hacks_false[x] = int(self.TimeHacks[False][x] * scale)

        profile = {
            'ms_per_length': ms_per_length,
            'hacks_true': hacks_true,
            'hacks_false': hacks_false,
        }
        self._time_profile_cache[cache_key] = profile
        return profile

    def _get_pixel_for_elapsed(self, elapsed_ms, start_direction, profile):
        if elapsed_ms <= 0:
            return self.lowestLed if start_direction else self.highestLed

        ms_per_length = profile['ms_per_length']
        length_index = int(elapsed_ms // ms_per_length)
        time_in_length = int(elapsed_ms - (length_index * ms_per_length))
        direction = start_direction if (length_index % 2 == 0) else (not start_direction)

        if direction:
            for pixel in range(self.lowestLed, self.highestLed + 1):
                if time_in_length <= profile['hacks_true'][pixel]:
                    return pixel
            return self.highestLed
        for pixel in range(self.highestLed, self.lowestLed - 1, -1):
            if time_in_length <= profile['hacks_false'][pixel]:
                return pixel
        return self.lowestLed

    def _render_cursors(self, pixels):
        self.LedStrand.Strand.fill((0, 0, 0))
        self.LedStrand.draw15s()
        for i, pixel in enumerate(pixels):
            if pixel is None:
                continue
            self.Cursors[i].draw(pixel, True, clear_before=False, write_after=False)
        self.LedStrand.Strand.write()

    def _build_rep_plan(self, mode):
        durations = self.pace_cursor_durations if mode == 'pace' else self.sprint_cursor_durations
        active_count = self.pace_cursor_count if mode == 'pace' else self.sprint_cursor_count
        plan = []
        rep_total_ms = 0
        for i in range(active_count):
            duration_ms = int(durations[i] * timescale)
            delay_ms = 0
            if mode == 'pace' and self.pace_stagger and i > 0:
                delay_ms = i * 5 * timescale
            plan.append({
                'index': i,
                'duration_ms': duration_ms,
                'delay_ms': delay_ms,
                'profile': self._create_time_profile(durations[i]),
            })
            candidate_total = delay_ms + duration_ms
            if candidate_total > rep_total_ms:
                rep_total_ms = candidate_total
        return plan, rep_total_ms

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

    def rep(self, mode='pace', threeBeeps=True, rep_number=None):
        print(f'Direction Change : {self.Direction}')
        self.AudioAlert.beeps(threeBeeps)

        start_time = time.ticks_ms()
        plan, rep_total_ms = self._build_rep_plan(mode)
        last_shown_second = -1

        while self.RunningMode:
            elapsed = time.ticks_diff(time.ticks_ms(), start_time)
            if elapsed >= rep_total_ms:
                break

            if mode == 'pace' and rep_number is not None:
                elapsed_seconds = int(elapsed // timescale)
                if elapsed_seconds != last_shown_second:
                    self.display.fill(self.display.black)
                    self.display.text("FTL Fish v2.0", 1, 2, self.display.white)
                    self.display.text(self._rep_status_text(rep_number), 1, 12, self.display.white)
                    self.display.text(f'Time: {self._format_elapsed(elapsed_seconds)}', 1, 22, self.display.white)
                    self.display.show()
                    last_shown_second = elapsed_seconds

            pixels = [None, None, None]
            for entry in plan:
                idx = entry['index']
                cursor_elapsed = elapsed - entry['delay_ms']
                if cursor_elapsed < 0:
                    continue
                if cursor_elapsed > entry['duration_ms']:
                    cursor_elapsed = entry['duration_ms']
                pixels[idx] = self._get_pixel_for_elapsed(cursor_elapsed, self.Direction, entry['profile'])

            self._render_cursors(pixels)
            time.sleep_ms(10)

        self.lastRepEnd = time.ticks_ms()
        self.LedStrand.clear_strand()

    def loop(self):
        if not self.is_prepared():
            raise RuntimeError('Swim set is not prepared. Call /prep before /start.')

        self.Stopped = False
        self.RunningMode = True
        self.lastPixel = -1
        reps = 0
        while self.RunningMode and (self.repetitions == 0 or reps < self.repetitions):
            current_rep = reps + 1
            self.display.fill(self.display.black)
            self.display.text("FTL Fish v2.0", 1, 2, self.display.white)
            # self.OLED.text(netstr[0],1,12,self.OLED.white)
            self.display.text(self._rep_status_text(current_rep), 1, 22, self.display.white)
            self.display.show()

            start_time = time.ticks_ms()

            self.rep(mode='pace', rep_number=current_rep)

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
                    if self.repetitions == 0 or reps < self.repetitions:
                        print(f'Resting Interval : {rest_interval}')
                        self.run_rest_countdown(rest_interval, reps)

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
        while self.RunningMode:
            self.display.fill(self.display.black)
            self.display.text("FTL Fish v2.0", 1, 2, self.display.white)
            # self.OLED.text(netstr[0],1,12,self.OLED.white)
            self.display.text(f'Infinite Sprint Mode', 1, 22, self.display.white)
            self.display.show()

            start_time = time.ticks_ms()
            self.rep(mode='sprint', threeBeeps=False)
            self.Direction = direction
            if self.RunningMode:
                reps += 1

                elapsed_time = time.ticks_diff(time.ticks_ms(), start_time)
                print(f'{self.interval}, {elapsed_time}')
                rest_interval = (self.interval * timescale - elapsed_time) / timescale

                print(f'{reps} repetitions completed.')

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
