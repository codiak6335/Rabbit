(function (root, factory) {
    const api = factory();
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    root.DeckScript = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    'use strict';

    const VERSION = 2;
    const MAX_ENTRIES = 256;
    const MAX_NAME_LENGTH = 64;
    const MAX_LABEL_LENGTH = 80;
    const MAX_DISTANCE = 5000;
    const MAX_SECONDS = 86400;

    function timeSeconds(value) {
        if (typeof value === 'number') {
            if (!Number.isFinite(value)) throw new Error(`Invalid time: ${value}`);
            return value;
        }
        let raw = String(value || '').trim().toLowerCase();
        if (!raw) throw new Error('A time value is required.');
        if (raw.endsWith('min')) {
            const minutes = Number(raw.slice(0, -3));
            if (!Number.isFinite(minutes)) throw new Error(`Invalid time: ${value}`);
            return minutes * 60;
        }
        if (raw.endsWith('s')) raw = raw.slice(0, -1);
        const parts = raw.split(':').map(Number);
        if (parts.some((part) => !Number.isFinite(part)) || parts.length > 3) throw new Error(`Invalid time: ${value}`);
        const seconds = parts.reduce((total, part) => (total * 60) + part, 0);
        if (!Number.isFinite(seconds)) throw new Error(`Invalid time: ${value}`);
        return seconds;
    }

    function timing(value, basis) {
        return { seconds: timeSeconds(value), basis: basis || 'rep' };
    }

    function scaledSeconds(spec, distance) {
        if (!spec) return null;
        const seconds = Number(spec.seconds);
        if (spec.basis === 'per100') return seconds * Number(distance) / 100;
        if (spec.basis === 'per50') return seconds * Number(distance) / 50;
        return seconds;
    }

    function workout(name, items, options) {
        return Object.assign({ version: VERSION, type: 'workout', name: name || 'Untitled workout', items: items || [] }, options || {});
    }

    function swim(distance, options) {
        return Object.assign({ type: 'swim', distance: Number(distance), reps: 1 }, options || {});
    }

    function repeat(count, items, options) {
        return Object.assign({ type: 'repeat', count: count === 'forever' ? 'forever' : Number(count), items: items || [] }, options || {});
    }

    function ladder(start, peak, end, step, options) {
        return Object.assign({
            type: 'ladder', start: Number(start), peak: Number(peak), end: Number(end),
            step: Number(step), options: options || {},
        }, options || {});
    }

    function rest(value) {
        return { type: 'rest', seconds: timeSeconds(value) };
    }

    function activity(name, options) {
        return Object.assign({ type: 'activity', name: String(name), reps: 1 }, options || {});
    }

    function validate(model) {
        const errors = [];
        if (!model || model.type !== 'workout') errors.push('Root must be a workout.');
        if (model && (
            typeof model.name !== 'string'
            || !model.name.trim()
            || model.name.length > MAX_NAME_LENGTH
        )) {
            errors.push(`Workout name must be 1–${MAX_NAME_LENGTH} characters.`);
        }
        if (model && (!Array.isArray(model.items) || !model.items.length)) {
            errors.push('Workout must contain at least one step.');
        }
        if (model && model.pool != null && (
            typeof model.pool !== 'string'
            || !model.pool.trim()
            || model.pool.length > MAX_LABEL_LENGTH
        )) {
            errors.push(`Pool name must be 1–${MAX_LABEL_LENGTH} characters.`);
        }
        if (model && model.direction != null && !/^(near|far)$/i.test(String(model.direction))) {
            errors.push('Direction must be Near or Far.');
        }
        if (model && model.audio != null && !/^(yes|no|on|off|true|false)$/i.test(String(model.audio))) {
            errors.push('Audio must be Yes or No.');
        }

        function validNumber(value, minimum, maximum) {
            return typeof value === 'number' && Number.isFinite(value) && value >= minimum && value <= maximum;
        }

        function validCount(value) {
            return Number.isInteger(value) && value > 0 && value <= MAX_ENTRIES;
        }

        function validateRests(rests, path) {
            if (rests == null) return;
            if (!Array.isArray(rests) || rests.some((value) => !validNumber(value, 0, MAX_SECONDS))) {
                errors.push(`${path}: recovery times must be between 0 and ${MAX_SECONDS} seconds.`);
            }
        }

        function visit(node, path, outerRepeat) {
            if (!node || !node.type) {
                errors.push(`${path}: missing node type.`);
                return;
            }
            if (node.label != null && (
                typeof node.label !== 'string'
                || node.label.length > MAX_LABEL_LENGTH
            )) {
                errors.push(`${path}: label must be at most ${MAX_LABEL_LENGTH} characters.`);
            }
            if (node.type === 'swim') {
                if (!validNumber(node.distance, 0.01, MAX_DISTANCE)) {
                    errors.push(`${path}: distance must be between 0.01 and ${MAX_DISTANCE}.`);
                }
                if (!validCount(node.reps)) {
                    errors.push(`${path}: repetitions must be an integer from 1 to ${MAX_ENTRIES}.`);
                }
                if (node.on && node.rests && node.rests.length) errors.push(`${path}: use either On or rest between reps, not both.`);
                validateRests(node.rests, path);
                const hold = scaledSeconds(node.hold, node.distance);
                const on = scaledSeconds(node.on, node.distance);
                const descendTo = scaledSeconds(node.descendTo, node.distance);
                if (hold != null && !validNumber(hold, 0.01, MAX_SECONDS)) {
                    errors.push(`${path}: Hold must be between 0.01 and ${MAX_SECONDS} seconds.`);
                }
                if (on != null && !validNumber(on, 0.01, MAX_SECONDS)) {
                    errors.push(`${path}: On must be between 0.01 and ${MAX_SECONDS} seconds.`);
                }
                if (on != null && hold != null && hold > on) errors.push(`${path}: Hold cannot exceed On.`);
                if (node.descendTo) {
                    if (node.reps < 2) errors.push(`${path}: descend requires at least two repetitions.`);
                    if (hold == null) errors.push(`${path}: descend requires a starting Hold target.`);
                    if (!validNumber(descendTo, 0.01, MAX_SECONDS)) {
                        errors.push(`${path}: descend target must be a valid time.`);
                    } else if (hold != null && descendTo >= hold) {
                        errors.push(`${path}: descend target must be faster than the starting Hold.`);
                    }
                    if (node.progress) errors.push(`${path}: use descend or round progression, not both.`);
                }
                if (node.strategy === 'negativeSplit') {
                    if (hold == null) errors.push(`${path}: negative split requires a Hold target.`);
                    if (!validNumber(node.splitDeltaSeconds, 0.01, MAX_SECONDS)) {
                        errors.push(`${path}: negative split needs a positive “by” time.`);
                    }
                    if (hold != null && node.splitDeltaSeconds >= hold) {
                        errors.push(`${path}: negative-split margin must be less than Hold.`);
                    }
                }
                if (node.strategy === 'surge' && !validNumber(node.variation, 0.001, 0.45)) {
                    errors.push(`${path}: surge change must be between 0.1% and 45%.`);
                }
                if (node.strategy && !['even', 'negativeSplit', 'surge'].includes(node.strategy)) {
                    errors.push(`${path}: unsupported pacing strategy.`);
                }
                if (node.progress && !outerRepeat) errors.push(`${path}: round progression requires an enclosing repeat.`);
                if (node.progress && (
                    !Number.isFinite(Number(node.progress.onDeltaSeconds || 0))
                    || !Number.isFinite(Number(node.progress.holdDeltaSeconds || 0))
                )) {
                    errors.push(`${path}: round progression changes must be finite numbers.`);
                }
            } else if (node.type === 'repeat') {
                if (node.count !== 'forever' && !validCount(node.count)) {
                    errors.push(`${path}: repeat count must be an integer from 1 to ${MAX_ENTRIES}.`);
                }
                if (node.count === 'forever' && outerRepeat) {
                    errors.push(`${path}: an until-stopped repeat cannot be nested.`);
                }
                if (
                    node.betweenRoundsSeconds != null
                    && !validNumber(node.betweenRoundsSeconds, 0, MAX_SECONDS)
                ) {
                    errors.push(`${path}: between-round rest must be between 0 and ${MAX_SECONDS} seconds.`);
                }
                if (!Array.isArray(node.items) || !node.items.length) {
                    errors.push(`${path}: repeat must contain at least one step.`);
                } else {
                    node.items.forEach((child, index) => visit(child, `${path}.${index + 1}`, node));
                }
            } else if (node.type === 'ladder') {
                if (
                    !validNumber(node.start, 0.01, MAX_DISTANCE)
                    || !validNumber(node.peak, node.start, MAX_DISTANCE)
                    || !validNumber(node.end, 0.01, node.peak)
                    || !validNumber(node.step, 0.01, MAX_DISTANCE)
                ) {
                    errors.push(`${path}: invalid ladder range.`);
                }
                const hold = scaledSeconds(node.hold, node.peak);
                const on = scaledSeconds(node.on, node.peak);
                if (hold != null && !validNumber(hold, 0.01, MAX_SECONDS)) {
                    errors.push(`${path}: Hold must be between 0.01 and ${MAX_SECONDS} seconds.`);
                }
                if (on != null && !validNumber(on, 0.01, MAX_SECONDS)) {
                    errors.push(`${path}: On must be between 0.01 and ${MAX_SECONDS} seconds.`);
                }
                if (on != null && hold != null && hold > on) errors.push(`${path}: Hold cannot exceed On.`);
            } else if (node.type === 'rest') {
                if (!validNumber(node.seconds, 0, MAX_SECONDS)) {
                    errors.push(`${path}: rest must be between 0 and ${MAX_SECONDS} seconds.`);
                }
            } else if (node.type === 'activity') {
                if (
                    typeof node.name !== 'string'
                    || !node.name
                    || node.name.length > MAX_LABEL_LENGTH
                ) {
                    errors.push(`${path}: activity name must be 1–${MAX_LABEL_LENGTH} characters.`);
                }
                if (!validCount(node.reps)) {
                    errors.push(`${path}: activity repetitions must be an integer from 1 to ${MAX_ENTRIES}.`);
                }
                validateRests(node.rests, path);
            } else {
                errors.push(`${path}: unsupported node type “${node.type}”.`);
            }
        }

        if (model && Array.isArray(model.items)) {
            const continuousRoots = model.items.filter((item) => item && item.type === 'repeat' && item.count === 'forever');
            if (continuousRoots.length && (model.items.length !== 1 || continuousRoots.length !== 1)) {
                errors.push('An until-stopped repeat must be the workout’s only top-level step.');
            }
            model.items.forEach((item, index) => visit(item, `item ${index + 1}`, null));
        }
        return errors;
    }

    function compile(model) {
        const errors = validate(model);
        if (errors.length) throw new Error(errors.join('\n'));
        const entries = [];
        let continuous = false;

        function adjusted(spec, delta, roundIndex) {
            if (!spec) return null;
            return { seconds: Number(spec.seconds) + (Number(delta || 0) * roundIndex), basis: spec.basis || 'rep' };
        }

        function emit(entry) {
            if (entries.length >= MAX_ENTRIES) {
                throw new Error(`Workout exceeds the controller limit of ${MAX_ENTRIES} steps.`);
            }
            entries.push(entry);
        }

        function emitSwim(node, context) {
            for (let repIndex = 0; repIndex < node.reps; repIndex += 1) {
                const progress = node.progress || {};
                const onSpec = adjusted(node.on, progress.onDeltaSeconds, context.roundIndex || 0);
                const holdSpec = adjusted(node.hold, progress.holdDeltaSeconds, context.roundIndex || 0);
                let targetSeconds = scaledSeconds(holdSpec, node.distance);
                const intervalSeconds = scaledSeconds(onSpec, node.distance);
                if (node.descendTo) {
                    const lastTargetSeconds = scaledSeconds(node.descendTo, node.distance);
                    const fraction = node.reps > 1 ? repIndex / (node.reps - 1) : 0;
                    targetSeconds += (lastTargetSeconds - targetSeconds) * fraction;
                }
                if (targetSeconds != null && !(targetSeconds > 0 && targetSeconds <= MAX_SECONDS)) {
                    throw new Error(`${context.label || 'Swim'}: Hold must stay greater than zero after progression.`);
                }
                if (intervalSeconds != null && !(intervalSeconds > 0 && intervalSeconds <= MAX_SECONDS)) {
                    throw new Error(`${context.label || 'Swim'}: On must stay greater than zero after progression.`);
                }
                if (targetSeconds != null && intervalSeconds != null && targetSeconds > intervalSeconds) {
                    throw new Error(`${context.label || 'Swim'}: Hold exceeds On after progression.`);
                }
                emit({
                    kind: 'swim',
                    distance: node.distance,
                    targetSeconds,
                    intervalSeconds,
                    restSeconds: intervalSeconds != null && targetSeconds != null ? intervalSeconds - targetSeconds : null,
                    label: node.label || '',
                    segments: node.segments || null,
                    strategy: node.strategy || 'even',
                    splitDeltaSeconds: node.splitDeltaSeconds || null,
                    variation: node.variation || null,
                    waitForInterval: repIndex + 1 < node.reps,
                    round: context.round || null,
                    roundCount: context.roundCount || null,
                    rep: repIndex + 1,
                    repCount: node.reps,
                });
                if (repIndex + 1 < node.reps && node.rests && node.rests.length) {
                    const restIndex = Math.min(repIndex, node.rests.length - 1);
                    emit({ kind: 'rest', seconds: Number(node.rests[restIndex]), label: 'Recovery' });
                }
            }
        }

        function emitActivity(node, context) {
            for (let repIndex = 0; repIndex < node.reps; repIndex += 1) {
                emit({
                    kind: 'activity',
                    activity: node.name,
                    label: node.label || node.name,
                    round: context.round || null,
                    roundCount: context.roundCount || null,
                    rep: repIndex + 1,
                    repCount: node.reps,
                });
                if (repIndex + 1 < node.reps && node.rests && node.rests.length) {
                    const restIndex = Math.min(repIndex, node.rests.length - 1);
                    emit({ kind: 'rest', seconds: Number(node.rests[restIndex]), label: 'Recovery' });
                }
            }
        }

        function walk(items, context) {
            (items || []).forEach((node) => {
                if (node.type === 'swim') {
                    emitSwim(node, context);
                } else if (node.type === 'activity') {
                    emitActivity(node, context);
                } else if (node.type === 'rest') {
                    emit({ kind: 'rest', seconds: node.seconds, label: node.label || 'Rest' });
                } else if (node.type === 'repeat') {
                    const cycles = node.count === 'forever' ? 1 : node.count;
                    if (node.count === 'forever') continuous = true;
                    for (let roundIndex = 0; roundIndex < cycles; roundIndex += 1) {
                        walk(node.items, {
                            round: roundIndex + 1,
                            roundCount: node.count,
                            roundIndex,
                            label: `Round ${roundIndex + 1}`,
                        });
                        if (node.betweenRoundsSeconds && (node.count === 'forever' || roundIndex + 1 < cycles)) {
                            emit({ kind: 'rest', seconds: node.betweenRoundsSeconds, label: 'Between rounds' });
                        }
                    }
                } else if (node.type === 'ladder') {
                    const distances = [];
                    for (let value = node.start; value <= node.peak; value += node.step) distances.push(value);
                    for (let value = node.peak - node.step; value >= node.end; value -= node.step) distances.push(value);
                    distances.forEach((distance, index) => {
                        emitSwim(swim(distance, {
                            on: node.on, hold: node.hold, label: node.label || 'Ladder',
                        }), Object.assign({}, context, { label: `Ladder ${index + 1}` }));
                        if (index + 1 < distances.length) entries[entries.length - 1].waitForInterval = true;
                    });
                }
            });
        }

        walk(model.items, {});
        if (continuous && entries.length && entries[entries.length - 1].kind === 'swim') {
            entries[entries.length - 1].waitForInterval = true;
        }
        const swimCount = entries.filter((entry) => entry.kind === 'swim').length;
        let swimIndex = 0;
        entries.forEach((entry) => {
            if (entry.kind === 'swim') {
                swimIndex += 1;
                entry.swimIndex = swimIndex;
                entry.swimCount = swimCount;
            }
        });
        return {
            version: VERSION,
            type: 'executionPlan',
            name: model.name,
            pool: model.pool || null,
            direction: /^far$/i.test(model.direction || '') ? 'Far' : 'Near',
            audio: /^(no|off|false)$/i.test(model.audio || '') ? 'No' : 'Yes',
            continuous,
            entries,
        };
    }

    function fromLegacy(name, legacy) {
        const options = {
            on: timing(legacy.interval, 'rep'),
            hold: timing(legacy.duration, 'rep'),
            label: legacy.mode === 'sprint' ? 'Sprint' : '',
        };
        if (
            legacy.strategy === 'negative_split'
            && Number(legacy.repetitions) > 1
            && legacy.variation
        ) {
            options.descendTo = timing(legacy.variation, 'rep');
        } else if (legacy.strategy === 'surge') {
            options.strategy = 'surge';
            options.variation = Number(legacy.variation || 0) / 100;
        }
        const item = swim(Number(legacy.distance), Object.assign(options, {
            reps: legacy.mode === 'sprint' ? 1 : Number(legacy.repetitions || 1),
        }));
        const items = legacy.mode === 'sprint' ? [repeat('forever', [item])] : [item];
        return workout(name, items, {
            pool: legacy.pool,
            direction: legacy.direction,
            audio: legacy.audio,
            legacy: true,
        });
    }

    function pack(plan) {
        if (!plan || plan.type !== 'executionPlan' || plan.version !== VERSION) {
            throw new Error('Only a compiled DeckScript 2 plan can be packed.');
        }
        return {
            version: VERSION,
            type: 'compactExecutionPlan',
            name: plan.name,
            pool: plan.pool,
            direction: plan.direction,
            audio: plan.audio,
            continuous: plan.continuous,
            entries: plan.entries.map((entry) => {
                if (entry.kind === 'swim') {
                    return [
                        's', entry.distance, entry.targetSeconds, entry.intervalSeconds, entry.label || '',
                        entry.round, entry.roundCount, entry.rep, entry.repCount, entry.swimIndex, entry.swimCount,
                        entry.strategy || 'even', entry.splitDeltaSeconds,
                        entry.waitForInterval, entry.variation,
                    ];
                }
                if (entry.kind === 'rest') return ['r', entry.seconds, entry.label || 'Rest'];
                return [
                    'a', entry.activity, entry.label || entry.activity,
                    entry.round, entry.roundCount, entry.rep, entry.repCount,
                ];
            }),
        };
    }

    function formatTime(seconds) {
        const value = Number(seconds);
        const minutes = Math.floor(value / 60);
        const remainder = value - (minutes * 60);
        const fraction = Math.abs(remainder - Math.round(remainder)) > 0.0001;
        const rendered = fraction ? remainder.toFixed(2).replace(/0+$/, '').replace(/\.$/, '') : String(Math.round(remainder));
        return minutes ? `${minutes}:${rendered.padStart(2, '0')}` : `:${rendered.padStart(2, '0')}`;
    }

    function formatTiming(spec) {
        if (!spec) return '';
        const basis = spec.basis === 'per100' ? ' per 100' : spec.basis === 'per50' ? ' per 50' : '';
        return `${formatTime(spec.seconds)}${basis}`;
    }

    function format(model) {
        const lines = [`workout ${JSON.stringify(model.name || 'Untitled workout')}`];
        if (model.pool) lines.push(`pool ${JSON.stringify(model.pool)}`);
        if (model.direction) lines.push(`direction ${String(model.direction).toLowerCase()}`);
        if (model.audio) lines.push(`audio ${String(model.audio).toLowerCase()}`);
        lines.push('');

        function writeItems(items, depth) {
            const pad = '    '.repeat(depth);
            (items || []).forEach((node) => {
                if (node.type === 'repeat') {
                    const count = node.count === 'forever' ? 'until stopped' : `${node.count} rounds`;
                    const between = node.betweenRoundsSeconds ? ` rest ${formatTime(node.betweenRoundsSeconds)} between rounds` : '';
                    lines.push(`${pad}repeat ${count}${between} {`);
                    writeItems(node.items, depth + 1);
                    lines.push(`${pad}}`);
                } else if (node.type === 'swim') {
                    let line = `${pad}${node.reps || 1} x ${node.distance}`;
                    if (node.label) line += ` ${node.label}`;
                    if (node.strategy === 'negativeSplit') line += ` negative split by ${formatTime(node.splitDeltaSeconds)}`;
                    if (node.strategy === 'surge') line += ` surge by ${(node.variation * 100).toFixed(2).replace(/\.?0+$/, '')}%`;
                    if (node.on) line += ` on ${formatTiming(node.on)}`;
                    if (node.hold) line += ` hold ${formatTiming(node.hold)}`;
                    if (node.descendTo) line += ` descend to ${formatTiming(node.descendTo)}`;
                    if (node.rests && node.rests.length) {
                        line += ` rest ${node.rests.map(formatTime).join(',')} between reps`;
                    }
                    if (node.progress) {
                        if (node.progress.onDeltaSeconds) line += ` on-change ${node.progress.onDeltaSeconds}s/round`;
                        if (node.progress.holdDeltaSeconds) line += ` hold-change ${node.progress.holdDeltaSeconds}s/round`;
                    }
                    lines.push(line);
                } else if (node.type === 'ladder') {
                    let line = `${pad}ladder ${node.start} to ${node.peak} to ${node.end} step ${node.step}`;
                    if (node.on) line += ` on ${formatTiming(node.on)}`;
                    if (node.hold) line += ` hold ${formatTiming(node.hold)}`;
                    lines.push(line);
                } else if (node.type === 'rest') {
                    lines.push(`${pad}rest ${formatTime(node.seconds)}`);
                } else if (node.type === 'activity') {
                    let line = `${pad}activity ${JSON.stringify(node.name)}`;
                    if (node.reps > 1) line += ` x ${node.reps}`;
                    if (node.rests && node.rests.length) line += ` rest ${node.rests.map(formatTime).join(',')}`;
                    lines.push(line);
                }
            });
        }

        writeItems(model.items, 0);
        return lines.join('\n').trim();
    }

    function logicalLines(source) {
        const lines = [];
        let buffer = '';
        let quote = null;
        let comment = false;
        for (const char of String(source || '')) {
            if (comment) {
                if (char === '\n') {
                    comment = false;
                    if (buffer.trim()) lines.push(buffer.trim());
                    buffer = '';
                }
                continue;
            }
            if (!quote && char === '#') {
                comment = true;
            } else if (quote) {
                buffer += char;
                if (char === quote) quote = null;
            } else if (char === '"' || char === "'") {
                quote = char;
                buffer += char;
            } else if (char === '{' || char === '}') {
                if (buffer.trim()) lines.push(buffer.trim());
                lines.push(char);
                buffer = '';
            } else if (char === '\n' || char === ';') {
                if (buffer.trim()) lines.push(buffer.trim());
                buffer = '';
            } else {
                buffer += char;
            }
        }
        if (buffer.trim()) lines.push(buffer.trim());
        return lines;
    }

    function unquote(value) {
        const raw = String(value || '').trim();
        if ((raw.startsWith('"') && raw.endsWith('"')) || (raw.startsWith("'") && raw.endsWith("'"))) {
            if (raw[0] === '"') return JSON.parse(raw);
            return raw.slice(1, -1);
        }
        return raw;
    }

    function parseTimingText(value, basisText) {
        const basis = /per\s*100/i.test(basisText || '') ? 'per100' : /per\s*50/i.test(basisText || '') ? 'per50' : 'rep';
        return timing(value, basis);
    }

    function parse(source) {
        const lines = logicalLines(source);
        let index = 0;
        let name = 'Untitled workout';
        const options = {};

        function fail(message, line) {
            throw new Error(`DeckScript line ${line + 1}: ${message}`);
        }

        function timingMatch(text, key) {
            const expression = new RegExp(`(?:^|\\s)${key}\\s+([^\\s]+)(\\s+per\\s+(?:50|100))?`, 'i');
            const match = text.match(expression);
            return match ? parseTimingText(match[1], match[2]) : null;
        }

        function parseItems(expectClose) {
            const items = [];
            while (index < lines.length) {
                const lineIndex = index;
                const line = lines[index++];
                if (line === '}') {
                    if (!expectClose) fail('unexpected closing brace.', lineIndex);
                    return items;
                }
                if (line === '{') fail('opening brace must follow a block declaration.', lineIndex);

                let match = line.match(/^repeat\s+(until\s+stopped|\d+(?:\s+rounds?)?)(?:\s+rest\s+([^\s]+)\s+between\s+rounds)?$/i);
                if (match) {
                    if (lines[index++] !== '{') fail('repeat requires an opening brace.', lineIndex);
                    const count = /^until/i.test(match[1]) ? 'forever' : Number(match[1].match(/\d+/)[0]);
                    items.push(repeat(count, parseItems(true), match[2] ? { betweenRoundsSeconds: timeSeconds(match[2]) } : null));
                    continue;
                }

                match = line.match(/^ladder\s+(\d+(?:\.\d+)?)\s+to\s+(\d+(?:\.\d+)?)\s+to\s+(\d+(?:\.\d+)?)\s+step\s+(\d+(?:\.\d+)?)(.*)$/i);
                if (match) {
                    items.push(ladder(match[1], match[2], match[3], match[4], {
                        on: timingMatch(match[5], 'on'),
                        hold: timingMatch(match[5], 'hold'),
                    }));
                    continue;
                }

                match = line.match(/^rest\s+(.+)$/i);
                if (match) {
                    items.push(rest(match[1]));
                    continue;
                }

                match = line.match(/^activity\s+("[^"]+"|'[^']+'|[^\s]+)(?:\s+x\s+(\d+))?(?:\s+rest\s+(.+))?$/i);
                if (match) {
                    const rests = match[3] ? match[3].split(',').map(timeSeconds) : null;
                    items.push(activity(unquote(match[1]), { reps: Number(match[2] || 1), rests }));
                    continue;
                }

                match = line.match(/^(?:(\d+)\s*x\s*)?(\d+(?:\.\d+)?)(.*)$/i);
                if (match) {
                    const tail = match[3] || '';
                    const strategyMatch = tail.match(/\bnegative[\s-]+split\s+by\s+([^\s]+)/i);
                    const surgeMatch = tail.match(/\bsurge\s+by\s+(\d+(?:\.\d+)?)%/i);
                    const descendMatch = tail.match(/\bdescend\s+to\s+([^\s]+)(\s+per\s+(?:50|100))?/i);
                    let labelTail = strategyMatch ? tail.replace(strategyMatch[0], '') : tail;
                    if (surgeMatch) labelTail = labelTail.replace(surgeMatch[0], '');
                    const cleanLabelTail = descendMatch ? labelTail.replace(descendMatch[0], '') : labelTail;
                    const firstTiming = cleanLabelTail.search(/\s(?:on|hold|rest|descend|on-change|hold-change)\s/i);
                    const label = (firstTiming >= 0 ? cleanLabelTail.slice(0, firstTiming) : cleanLabelTail).trim();
                    const onDelta = tail.match(/\bon-change\s+([+-]?\d+(?:\.\d+)?)s?\/round\b/i);
                    const holdDelta = tail.match(/\bhold-change\s+([+-]?\d+(?:\.\d+)?)s?\/round\b/i);
                    const restMatch = tail.match(/\brest\s+(.+?)\s+between\s+reps\b/i);
                    const rests = restMatch ? restMatch[1].split(',').map((value) => timeSeconds(value.trim())) : null;
                    const progress = onDelta || holdDelta ? {
                        onDeltaSeconds: onDelta ? Number(onDelta[1]) : 0,
                        holdDeltaSeconds: holdDelta ? Number(holdDelta[1]) : 0,
                    } : null;
                    items.push(swim(match[2], {
                        reps: Number(match[1] || 1),
                        label,
                        on: timingMatch(tail, 'on'),
                        hold: timingMatch(tail, 'hold'),
                        rests,
                        progress,
                        strategy: strategyMatch ? 'negativeSplit' : surgeMatch ? 'surge' : 'even',
                        splitDeltaSeconds: strategyMatch ? timeSeconds(strategyMatch[1]) : null,
                        variation: surgeMatch ? Number(surgeMatch[1]) / 100 : null,
                        descendTo: descendMatch ? parseTimingText(descendMatch[1], descendMatch[2]) : null,
                    }));
                    continue;
                }
                fail(`cannot parse “${line}”.`, lineIndex);
            }
            if (expectClose) fail('missing closing brace.', Math.max(0, lines.length - 1));
            return items;
        }

        while (index < lines.length) {
            const line = lines[index];
            let match = line.match(/^workout\s+(.+)$/i);
            if (match) {
                name = unquote(match[1]);
                index += 1;
                continue;
            }
            match = line.match(/^(pool|direction|audio)\s+(.+)$/i);
            if (match) {
                options[match[1].toLowerCase()] = unquote(match[2]);
                index += 1;
                continue;
            }
            break;
        }
        const model = workout(name, parseItems(false), options);
        const errors = validate(model);
        if (errors.length) throw new Error(errors.join('\n'));
        return model;
    }

    function splitTopLevel(text, separator) {
        const parts = [];
        let depth = 0;
        let start = 0;
        for (let index = 0; index < text.length; index += 1) {
            const char = text[index];
            if (char === '(') depth += 1;
            else if (char === ')') depth -= 1;
            else if (char === separator && depth === 0) {
                parts.push(text.slice(start, index).trim());
                start = index + 1;
            }
        }
        parts.push(text.slice(start).trim());
        return parts.filter(Boolean);
    }

    function importShorthand(source, options) {
        const settings = options || {};
        const rawLines = String(source || '').split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
        if (!rawLines.length) throw new Error('Paste one swim set to import.');
        let name = settings.name || 'Imported workout';
        let lines = rawLines;
        if (rawLines.length > 1 && !/\d/.test(rawLines[0])) {
            name = rawLines[0];
            lines = rawLines.slice(1);
        }
        if (lines.length !== 1) throw new Error('Import one set expression at a time. The first line may be its name.');

        const warnings = [];
        const defaultHold = settings.holdPer100 ? timing(settings.holdPer100, 'per100') : null;

        function restSchedule(value) {
            const clean = String(value || '').trim().replace(/\*$/, '')
                .replace(/^:(?=\d+(?:\.\d+)?(?:s|min)$)/i, '');
            if (!clean) return null;
            const pieces = clean.includes('-') ? clean.split('-') : [clean];
            return pieces.map((piece, index) => {
                let token = piece.trim();
                if (index > 0 && token[0] !== ':' && !/min$|s$/i.test(token)) token = `:${token}`;
                return timeSeconds(token);
            });
        }

        function segmentedSwim(text) {
            const segments = [];
            const expression = /(\d+(?:\.\d+)?)\s*([a-z][a-z\s]*?)(?=\s+\d+(?:\.\d+)?\s*[a-z]|$)/gi;
            let match;
            while ((match = expression.exec(text))) {
                segments.push({ distance: Number(match[1]), label: match[2].trim() });
            }
            if (!segments.length) return null;
            return swim(segments.reduce((total, segment) => total + segment.distance, 0), {
                label: segments.map((segment) => `${segment.distance} ${segment.label}`).join(' / '),
                segments,
                hold: defaultHold,
            });
        }

        function parseExpression(expression) {
            const plusParts = splitTopLevel(expression, '+');
            if (plusParts.length > 1) {
                const hasRecovery = (part) => /(?:^|\s)(?::[\d:.]+(?:s|min)?|\d+(?:\.\d+)?(?:s|min))\*?$/i.test(part);
                const recoveryFlags = plusParts.map(hasRecovery);
                if (recoveryFlags[recoveryFlags.length - 1] && recoveryFlags.slice(0, -1).some((value) => !value)) {
                    warnings.push('A recovery written only at the end applies only after the final distance; add it after each distance if that was the intent.');
                }
                return plusParts.flatMap(parseExpression);
            }

            let text = expression.trim();
            const starred = /\*\s*$/.test(text);
            text = text.replace(/\*\s*$/, '').trim();

            let match = text.match(/^(\d+)\s*x\s*\((.*)\)\s*(?::?\s*([:\d][\d:.\-]*(?:s|min)?))?$/i);
            if (match) {
                const count = Number(match[1]);
                const innerText = match[2].trim();
                const recovery = restSchedule(match[3]);
                const segmented = !innerText.includes('+') && !/\d+\s*x\s*/i.test(innerText)
                    ? segmentedSwim(innerText)
                    : null;
                if (segmented) {
                    segmented.reps = count;
                    segmented.rests = recovery;
                    if (recovery && recovery.length !== count - 1) warnings.push('Recovery schedule is extended using its final value.');
                    return [segmented];
                }
                const inner = parseExpression(innerText);
                return [repeat(count, inner, recovery && recovery.length ? { betweenRoundsSeconds: recovery[0] } : null)];
            }

            match = text.match(/^(\d+(?:\.\d+)?)\s*\((.*)\)$/i);
            if (match) {
                const totalDistance = Number(match[1]);
                const pattern = segmentedSwim(match[2]);
                return [swim(totalDistance, {
                    label: pattern ? `Repeat ${pattern.label}` : `Repeat ${match[2].trim()}`,
                    segments: pattern ? pattern.segments : null,
                    hold: defaultHold,
                })];
            }

            match = text.match(/^(\d+)\s+(turns?|dives?)(?:\s+([:\d][\d:.\-]*(?:s|min)?))?$/i);
            if (match) {
                return [activity(match[2].replace(/s$/i, ''), {
                    reps: Number(match[1]),
                    rests: restSchedule(match[3]),
                })];
            }

            match = text.match(/^(turn|dive)s?$/i);
            if (match) return [activity(match[1])];

            if (starred) {
                const repeatingPattern = segmentedSwim(text);
                if (repeatingPattern && repeatingPattern.segments.length > 1) {
                    return [repeat('forever', [repeatingPattern])];
                }
            }

            match = text.match(/^(?:(\d+)\s*x\s*)?(\d+(?:\.\d+)?)(.*)$/i);
            if (!match) throw new Error(`Could not import “${expression}”.`);
            const reps = Number(match[1] || 1);
            const distance = Number(match[2]);
            let tail = (match[3] || '').trim();
            let recovery = null;
            const recoveryMatch = tail.match(/(?:^|\s)([:\d][\d:.\-]*(?:s|min)?)$/i);
            if (recoveryMatch) {
                recovery = restSchedule(recoveryMatch[1]);
                tail = tail.slice(0, recoveryMatch.index).trim();
            }
            if (reps > 1 && recovery && recovery.length !== reps - 1) warnings.push('Recovery schedule is extended using its final value.');
            const importedSwim = swim(distance, {
                reps,
                label: tail,
                hold: defaultHold,
                rests: reps > 1 ? recovery : null,
            });
            if (reps === 1 && recovery && recovery.length) return [importedSwim, rest(recovery[0])];
            return [importedSwim];
        }

        const items = parseExpression(lines[0]);
        if (!defaultHold && items.some((item) => item.type === 'swim' || item.type === 'repeat')) {
            warnings.push('Add a Hold-per-100 target before preparing this workout.');
        }
        if (/\*/.test(lines[0])) {
            const continuousPattern = items.length === 1
                && items[0].type === 'repeat'
                && items[0].count === 'forever';
            warnings.push(continuousPattern
                ? 'The starred pattern repeats until Stop because no total cutoff was stated.'
                : 'The starred pattern was expanded to its stated count or distance cutoff.');
        }
        return {
            model: workout(name, items, {
                pool: settings.pool || null,
                direction: settings.direction || 'Near',
                audio: settings.audio || 'Yes',
            }),
            warnings,
        };
    }

    return {
        VERSION, MAX_ENTRIES, timeSeconds, timing, scaledSeconds, workout, swim, repeat, ladder, rest, activity,
        validate, compile, pack, fromLegacy, formatTime, format, parse, importShorthand,
    };
}));
