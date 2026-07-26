#!/usr/bin/env python3
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from runtime_support import patch_time_module
from workout_runner import WorkoutPlanError, WorkoutRunner


patch_time_module()


class FakeStrand:
    def clear_strand(self):
        pass


class FakeSwimSet:
    def __init__(self):
        self.length = 25
        self.LedStrand = FakeStrand()
        self.Stopped = True
        self.RunningMode = False
        self.beep_lead_ms = 0
        self.next_rep_start_ms = None
        self.audio = None

    def set_bottom_times(self, target, distance, interval, repetitions, length, direction, pool, strategy, variation, last):
        self.length = length
        self.duration = target
        self.distance = distance
        self.interval = interval

    def use_audio(self, value):
        self.audio = value

    def build_length_plan(self, target, count, strategy, variation):
        weights = [1 - variation if index % 2 == 0 else 1 + variation for index in range(count)]
        total_weight = sum(weights)
        return [target * weight / total_weight for weight in weights]

    def rep(self):
        self.next_rep_start_ms = time.ticks_ms()

    def stop_set(self):
        self.RunningMode = False

    def seconds_until_next_rep(self):
        return 0


class RecordingRunner(WorkoutRunner):
    def __init__(self, swim_set):
        super().__init__(swim_set)
        self.interval_waits = 0

    def _run_rest_until(self, deadline):
        self.interval_waits += 1


def compact_plan():
    return {
        'version': 2,
        'type': 'compactExecutionPlan',
        'name': 'Runner test',
        'pool': 'Test Pool',
        'direction': 'Near',
        'audio': 'No',
        'continuous': False,
        'entries': [
            ['s', 25, 1, 1, 'Fast', None, None, 1, 2, 1, 2],
            ['r', 0, 'Immediate'],
            ['s', 25, 1, 1, 'Easy', None, None, 2, 2, 2, 2],
        ],
    }


def expect_invalid(plan, phrase):
    runner = WorkoutRunner(FakeSwimSet())
    try:
        runner.prepare(plan)
    except WorkoutPlanError as exc:
        assert phrase in str(exc), str(exc)
    else:
        raise AssertionError('Expected invalid plan: %s' % phrase)


runner = WorkoutRunner(FakeSwimSet())
runner.prepare(compact_plan())
assert runner.status()['prepared']
assert runner.start()
runner.run()
status = runner.status()
assert status['complete']
assert status['entryIndex'] == 3
assert runner.swim_set.audio == 'No'

interval_plan = compact_plan()
interval_plan['entries'] = [
    ['s', 25, 1, 2, '', None, None, 1, 2, 1, 2, 'even', None, True],
    ['s', 25, 1, 2, '', None, None, 2, 2, 2, 2, 'even', None, False],
]
runner = RecordingRunner(FakeSwimSet())
runner.prepare(interval_plan)
runner.start()
runner.run()
assert runner.interval_waits == 1

negative_split = compact_plan()
negative_split['name'] = 'Negative split'
negative_split['entries'] = [
    ['s', 500, 280, 330, '', None, None, 1, 1, 1, 1, 'negativeSplit', 4, False, None],
]
runner = WorkoutRunner(FakeSwimSet())
runner.prepare(negative_split)
runner.start()
runner.run()
assert len(runner.swim_set.length_plan_ms) == 20
assert sum(runner.swim_set.length_plan_ms[:10]) == 142000
assert sum(runner.swim_set.length_plan_ms[10:]) == 138000

surge_plan = compact_plan()
surge_plan['name'] = 'Surge'
surge_plan['entries'] = [
    ['s', 100, 80, 90, '', None, None, 1, 1, 1, 1, 'surge', None, False, 0.08],
]
runner = WorkoutRunner(FakeSwimSet())
runner.prepare(surge_plan)
runner.start()
runner.run()
assert runner.swim_set.length_plan_ms == [18400, 21600, 18400, 21600]

invalid = compact_plan()
invalid['entries'] = invalid['entries'] * 100
expect_invalid(invalid, 'too large')

invalid = compact_plan()
invalid['entries'][0][2] = None
expect_invalid(invalid, 'Hold target')

invalid = compact_plan()
invalid['entries'][0][3] = 0.5
expect_invalid(invalid, 'On interval')

invalid = compact_plan()
invalid['name'] = 'x' * 65
expect_invalid(invalid, 'at most 64')

invalid = compact_plan()
invalid['entries'][0][4] = 'x' * 81
expect_invalid(invalid, 'invalid label')

invalid = compact_plan()
invalid['entries'] = [
    ['s', 75, 60, 70, '', None, None, 1, 1, 1, 1, 'negativeSplit', 2, False, None],
]
expect_invalid(invalid, 'even number')

invalid = compact_plan()
invalid['entries'] = [
    ['s', 100, 60, 70, '', None, None, 1, 1, 1, 1, 'surge', None, False, 0.8],
]
expect_invalid(invalid, 'surge change')

print('WorkoutRunner tests passed')
