import time


class WorkoutPlanError(ValueError):
    pass


class WorkoutRunner:
    MAX_ENTRIES = 256
    MAX_NAME_LENGTH = 64
    MAX_LABEL_LENGTH = 80
    MAX_DISTANCE = 5000
    MAX_SECONDS = 86400

    def __init__(self, swim_set):
        self.swim_set = swim_set
        self.plan = None
        self.entries = []
        self.index = 0
        self.cycle = 1
        self.running = False
        self.stopped = True
        self.complete = False
        self._pool = None
        self._direction = True
        self._deadline_ms = None

    @staticmethod
    def _entry_dict(entry):
        if isinstance(entry, dict):
            return entry
        if not isinstance(entry, (list, tuple)) or not entry:
            return {}
        if entry[0] == 's':
            fields = (
                'kind', 'distance', 'targetSeconds', 'intervalSeconds', 'label',
                'round', 'roundCount', 'rep', 'repCount', 'swimIndex', 'swimCount',
                'strategy', 'splitDeltaSeconds', 'waitForInterval', 'variation',
            )
            values = ['swim'] + list(entry[1:])
        elif entry[0] == 'r':
            fields = ('kind', 'seconds', 'label')
            values = ['rest'] + list(entry[1:])
        elif entry[0] == 'a':
            fields = ('kind', 'activity', 'label', 'round', 'roundCount', 'rep', 'repCount')
            values = ['activity'] + list(entry[1:])
        else:
            return {}
        return {field: values[index] if index < len(values) else None for index, field in enumerate(fields)}

    @staticmethod
    def _number_between(value, minimum, maximum):
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and value == value
            and minimum <= value <= maximum
        )

    def prepare(self, plan):
        if self.running:
            raise WorkoutPlanError('Cannot prepare a workout while it is running.')
        self._validate(plan)
        self.plan = plan
        self.entries = plan.get('entries', [])
        self.index = 0
        self.cycle = 1
        self.running = False
        self.stopped = True
        self.complete = False
        self._pool = plan.get('pool')
        self._direction = plan.get('direction', 'Near') != 'Far'
        self._deadline_ms = None

        first_swim = self._first_swim()
        if first_swim is not None:
            self._initialize_hardware(first_swim)
        self.swim_set.use_audio(plan.get('audio', 'Yes'))

    def clear(self):
        if self.running:
            raise WorkoutPlanError('Cannot clear a workout while it is running.')
        self.plan = None
        self.entries = []
        self.index = 0
        self.cycle = 1
        self.complete = False
        self._deadline_ms = None

    def _validate(self, plan):
        if not isinstance(plan, dict) or plan.get('type') not in ('executionPlan', 'compactExecutionPlan'):
            raise WorkoutPlanError('Expected a compiled executionPlan.')
        if plan.get('version') != 2:
            raise WorkoutPlanError('Unsupported execution plan version.')
        name = plan.get('name')
        if not isinstance(name, str) or not name.strip() or len(name) > self.MAX_NAME_LENGTH:
            raise WorkoutPlanError('Execution plan needs a name of at most %d characters.' % self.MAX_NAME_LENGTH)
        if not isinstance(plan.get('pool'), str) or not plan.get('pool'):
            raise WorkoutPlanError('Execution plan needs a pool.')
        if plan.get('direction', 'Near') not in ('Near', 'Far'):
            raise WorkoutPlanError('Execution plan direction must be Near or Far.')
        if plan.get('audio', 'Yes') not in ('Yes', 'No'):
            raise WorkoutPlanError('Execution plan audio must be Yes or No.')
        if not isinstance(plan.get('continuous', False), bool):
            raise WorkoutPlanError('Execution plan continuous flag must be true or false.')
        entries = plan.get('entries')
        if not isinstance(entries, list) or not entries:
            raise WorkoutPlanError('Execution plan has no entries.')
        if len(entries) > self.MAX_ENTRIES:
            raise WorkoutPlanError('Execution plan is too large for this controller.')
        for index, raw_entry in enumerate(entries):
            if isinstance(raw_entry, (list, tuple)) and len(raw_entry) > 15:
                raise WorkoutPlanError('Plan entry %d has too many fields.' % (index + 1))
            entry = self._entry_dict(raw_entry)
            if not entry:
                raise WorkoutPlanError('Plan entry %d is invalid.' % (index + 1))
            kind = entry.get('kind')
            label = entry.get('label') or ''
            if not isinstance(label, str) or len(label) > self.MAX_LABEL_LENGTH:
                raise WorkoutPlanError('Plan entry %d has an invalid label.' % (index + 1))
            if kind == 'swim':
                distance = entry.get('distance')
                target = entry.get('targetSeconds')
                interval = entry.get('intervalSeconds')
                strategy = entry.get('strategy') or 'even'
                split_delta = entry.get('splitDeltaSeconds')
                wait_for_interval = entry.get('waitForInterval')
                variation = entry.get('variation')
                if not self._number_between(distance, 0.01, self.MAX_DISTANCE):
                    raise WorkoutPlanError('Swim %d has an invalid distance.' % (index + 1))
                if not self._number_between(target, 0.01, self.MAX_SECONDS):
                    raise WorkoutPlanError('Swim %d needs a numeric Hold target.' % (index + 1))
                if interval is not None and (
                    not self._number_between(interval, 0.01, self.MAX_SECONDS) or interval < target
                ):
                    raise WorkoutPlanError('Swim %d has an invalid On interval.' % (index + 1))
                if strategy not in ('even', 'negativeSplit', 'surge'):
                    raise WorkoutPlanError('Swim %d has an invalid pacing strategy.' % (index + 1))
                if wait_for_interval is not None and not isinstance(wait_for_interval, bool):
                    raise WorkoutPlanError('Swim %d has an invalid interval-wait flag.' % (index + 1))
                if strategy == 'negativeSplit' and (
                    not self._number_between(split_delta, 0.01, target - 0.01)
                ):
                    raise WorkoutPlanError('Swim %d has an invalid negative-split margin.' % (index + 1))
                if strategy == 'negativeSplit':
                    length_count = int(round(float(distance) / 25.0))
                    if length_count < 2 or length_count % 2 or abs((length_count * 25.0) - distance) > 0.001:
                        raise WorkoutPlanError(
                            'Swim %d negative split requires an even number of 25-unit lengths.' % (index + 1)
                        )
                if strategy == 'surge' and not self._number_between(variation, 0.001, 0.45):
                    raise WorkoutPlanError('Swim %d has an invalid surge change.' % (index + 1))
            elif kind == 'rest':
                seconds = entry.get('seconds')
                if not self._number_between(seconds, 0, self.MAX_SECONDS):
                    raise WorkoutPlanError('Rest %d has an invalid duration.' % (index + 1))
            elif kind == 'activity':
                activity_name = entry.get('activity')
                if (
                    not isinstance(activity_name, str)
                    or not activity_name
                    or len(activity_name) > self.MAX_LABEL_LENGTH
                ):
                    raise WorkoutPlanError('Activity %d needs a name.' % (index + 1))
            else:
                raise WorkoutPlanError('Unsupported plan entry kind: %s' % kind)

    def _first_swim(self):
        for raw_entry in self.entries:
            entry = self._entry_dict(raw_entry)
            if entry.get('kind') == 'swim':
                return entry
        return None

    def _initialize_hardware(self, entry):
        interval = entry.get('intervalSeconds')
        target = entry.get('targetSeconds')
        self.swim_set.set_bottom_times(
            target,
            entry.get('distance'),
            interval if interval is not None else target,
            1,
            25,
            self._direction,
            self._pool,
            'even',
            0.0,
            None,
        )

    def _configure_swim(self, entry):
        target = float(entry.get('targetSeconds'))
        interval = entry.get('intervalSeconds')
        if interval is None:
            interval = target
        distance = float(entry.get('distance'))
        length_count = max(1, int(round(distance / float(self.swim_set.length))))

        self.swim_set.duration = target
        self.swim_set.distance = distance
        self.swim_set.interval = float(interval)
        self.swim_set.repetitions = int(entry.get('swimCount') or 1)
        self.swim_set.completed_reps = max(0, int(entry.get('swimIndex') or 1) - 1)
        self.swim_set.rep_plan_ms = []
        self.swim_set.current_rep_target_seconds = target
        if entry.get('strategy') == 'negativeSplit':
            if length_count < 2 or length_count % 2:
                raise WorkoutPlanError('Negative split requires an even number of pool lengths.')
            split_delta = float(entry.get('splitDeltaSeconds'))
            half_length_count = length_count // 2
            first_half_seconds = (target + split_delta) / 2.0
            second_half_seconds = (target - split_delta) / 2.0
            length_seconds = (
                [first_half_seconds / half_length_count] * half_length_count
                + [second_half_seconds / half_length_count] * half_length_count
            )
        elif entry.get('strategy') == 'surge':
            length_seconds = self.swim_set.build_length_plan(
                target,
                length_count,
                'surge',
                float(entry.get('variation')),
            )
        else:
            length_seconds = self.swim_set.build_length_plan(target, length_count, 'even', 0.0)
        self.swim_set.length_plan_ms = [int(seconds * 1000) for seconds in length_seconds]
        self.swim_set.current_length_ms = self.swim_set.length_plan_ms[0]

    def start(self):
        if self.plan is None:
            raise WorkoutPlanError('Prepare a workout before starting.')
        if self.running:
            return False
        if self.complete and not self.plan.get('continuous'):
            raise WorkoutPlanError('Workout is complete. Prepare it again to restart.')
        self.running = True
        self.stopped = False
        self.swim_set.Stopped = False
        self.swim_set.RunningMode = True
        self._deadline_ms = None
        return True

    def stop(self):
        self.running = False
        self.swim_set.stop_set()

    def run(self):
        try:
            while self.running:
                if self.index >= len(self.entries):
                    if self.plan.get('continuous'):
                        self.index = 0
                        self.cycle += 1
                    else:
                        self.complete = True
                        break

                entry = self._entry_dict(self.entries[self.index])
                kind = entry.get('kind')
                if kind == 'swim':
                    self._configure_swim(entry)
                    self.swim_set.RunningMode = True
                    self.swim_set.rep()
                    if (
                        self.running
                        and entry.get('waitForInterval')
                        and self.swim_set.next_rep_start_ms is not None
                    ):
                        deadline = self.swim_set.next_rep_start_ms - self.swim_set.beep_lead_ms
                        self._run_rest_until(deadline)
                elif kind == 'rest':
                    self._run_rest(entry.get('seconds', 0))
                else:
                    self._run_activity(entry)

                self.index += 1
                if not self.running:
                    break
        finally:
            self.running = False
            self.stopped = True
            self.swim_set.RunningMode = False
            self.swim_set.Stopped = True
            self._deadline_ms = None
            self.swim_set.LedStrand.clear_strand()

    def _run_rest(self, seconds):
        self._run_rest_until(time.ticks_ms() + int(float(seconds) * 1000))

    def _run_rest_until(self, deadline):
        self._deadline_ms = deadline
        try:
            while self.running:
                remaining = time.ticks_diff(deadline, time.ticks_ms())
                if remaining <= 0:
                    break
                time.sleep(min(0.1, remaining / 1000.0))
        finally:
            self._deadline_ms = None

    def _run_activity(self, entry):
        # Non-swim skills are coach-directed. The controller holds the LEDs clear
        # and advances immediately unless an explicit rest follows.
        self.swim_set.LedStrand.clear_strand()

    def status(self):
        entry = None
        if self.entries:
            entry_index = min(self.index, len(self.entries) - 1)
            entry = self._entry_dict(self.entries[entry_index])
        seconds_until_next = None
        if self.running:
            if self._deadline_ms is not None:
                seconds_until_next = max(
                    0,
                    time.ticks_diff(self._deadline_ms, time.ticks_ms()) / 1000.0,
                )
            elif entry and entry.get('kind') == 'swim':
                seconds_until_next = self.swim_set.seconds_until_next_rep()
                if seconds_until_next is None and not self.swim_set.in_rep and entry.get('waitForInterval'):
                    seconds_until_next = entry.get('intervalSeconds')
        return {
            'prepared': self.plan is not None,
            'running': self.running,
            'stopped': self.stopped,
            'complete': self.complete,
            'continuous': bool(self.plan and self.plan.get('continuous')),
            'name': self.plan.get('name') if self.plan else None,
            'entryIndex': self.index,
            'entryCount': len(self.entries),
            'cycle': self.cycle,
            'entry': entry,
            'secondsUntilNext': seconds_until_next,
        }
