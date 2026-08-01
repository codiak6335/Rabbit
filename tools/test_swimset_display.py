#!/usr/bin/env python3
import os
import sys

os.environ['RABBIT_EMULATOR'] = '1'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from runtime_support import patch_time_module
from swimset import SwimSet


patch_time_module()


class FakeDisplay:
    black = 0
    white = 1

    def __init__(self):
        self.lines = []

    def fill(self, color):
        self.lines = []

    def text(self, value, x, y, color):
        self.lines.append(value)

    def show(self):
        pass


display = FakeDisplay()
swim_set = object.__new__(SwimSet)
swim_set.display = display
swim_set.next_display_update_ms = 0
swim_set.duration = 30
swim_set.distance = 50
swim_set.interval = 45
swim_set.repetitions = 20
swim_set.completed_reps = 0
swim_set.in_rep = False
swim_set.RunningMode = True
swim_set.staticStartTime = None
swim_set.next_rep_start_ms = None
swim_set.current_rep_target_seconds = 30
swim_set.length_plan_ms = [30000]
swim_set.length_index = 0

assert swim_set.seconds_until_next_rep() == 45

swim_set.update_set_display('Rep:1/20', force=True)
assert 'Rep:1/20' in display.lines, display.lines
