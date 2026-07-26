'use strict';

const assert = require('assert');
const D = require('../js/deckscript.js');

const pyramid = D.workout('Pyramid', [
    D.ladder(100, 500, 100, 100, {
        on: D.timing('1:15', 'per100'),
        hold: D.timing('1:00', 'per100'),
    }),
]);
const pyramidPlan = D.compile(pyramid);
assert.deepStrictEqual(pyramidPlan.entries.map((entry) => entry.distance), [100, 200, 300, 400, 500, 400, 300, 200, 100]);
assert.strictEqual(pyramidPlan.entries[4].targetSeconds, 300);
assert.strictEqual(pyramidPlan.entries[4].intervalSeconds, 375);
assert.ok(pyramidPlan.entries.slice(0, -1).every((entry) => entry.waitForInterval));
assert.strictEqual(pyramidPlan.entries[pyramidPlan.entries.length - 1].waitForInterval, false);

const nested = D.workout('Quality 50s', [
    D.repeat(5, [
        D.swim(50, { reps: 10, on: D.timing(40), hold: D.timing(25) }),
        D.swim(100, { reps: 3, label: 'Easy', on: D.timing('1:45'), hold: D.timing('1:30') }),
    ]),
]);
const nestedPlan = D.compile(nested);
assert.strictEqual(nestedPlan.entries.length, 65);
assert.strictEqual(nestedPlan.entries[10].targetSeconds, 90);
assert.strictEqual(nestedPlan.entries[13].round, 2);
assert.strictEqual(nestedPlan.entries[8].waitForInterval, true);
assert.strictEqual(nestedPlan.entries[9].waitForInterval, false);
assert.strictEqual(nestedPlan.entries[11].waitForInterval, true);
assert.strictEqual(nestedPlan.entries[12].waitForInterval, false);
const packedNested = D.pack(nestedPlan);
assert.strictEqual(packedNested.type, 'compactExecutionPlan');
assert.strictEqual(packedNested.entries[0][0], 's');
assert.ok(JSON.stringify(packedNested).length < JSON.stringify(nestedPlan).length * 0.55);

const progression = D.workout('Progression', [
    D.repeat(4, [
        D.swim(50, {
            reps: 10,
            on: D.timing(40),
            hold: D.timing(27),
            progress: { onDeltaSeconds: -5, holdDeltaSeconds: -0.75 },
        }),
    ]),
]);
const progressionPlan = D.compile(progression);
assert.deepStrictEqual(
    [0, 10, 20, 30].map((index) => [progressionPlan.entries[index].targetSeconds, progressionPlan.entries[index].intervalSeconds]),
    [[27, 40], [26.25, 35], [25.5, 30], [24.75, 25]],
);

const negativeSplit500s = D.parse(`
workout "Five 500 negative splits"
pool "Bellevue East"
5 x 500 negative split by :04 on 5:30 hold 4:40
`);
const negativeSplitPlan = D.compile(negativeSplit500s);
assert.strictEqual(negativeSplitPlan.entries.length, 5);
assert.strictEqual(negativeSplitPlan.entries[0].strategy, 'negativeSplit');
assert.strictEqual(negativeSplitPlan.entries[0].splitDeltaSeconds, 4);
assert.strictEqual(negativeSplitPlan.entries[0].targetSeconds, 280);
assert.strictEqual(negativeSplitPlan.entries[0].intervalSeconds, 330);
assert.strictEqual(negativeSplitPlan.entries[0].waitForInterval, true);
assert.strictEqual(negativeSplitPlan.entries[4].waitForInterval, false);
assert.strictEqual(D.compile(D.parse(D.format(negativeSplit500s))).entries[0].splitDeltaSeconds, 4);
assert.strictEqual(D.pack(negativeSplitPlan).entries[0].length, 15);

const descend500s = D.parse(`
workout "Five 500 descend"
pool "Bellevue East"
5 x 500 on 5:30 hold 5:00 descend to 4:40
`);
assert.deepStrictEqual(
    D.compile(descend500s).entries.map((entry) => entry.targetSeconds),
    [300, 295, 290, 285, 280],
);
assert.deepStrictEqual(
    D.compile(D.parse(D.format(descend500s))).entries.map((entry) => entry.targetSeconds),
    [300, 295, 290, 285, 280],
);

const continuous = D.compile(D.workout('Continuous', [
    D.repeat('forever', [D.swim(50, { on: D.timing(40), hold: D.timing(25) })]),
]));
assert.strictEqual(continuous.continuous, true);
assert.strictEqual(continuous.entries.length, 1);
assert.strictEqual(continuous.entries[0].waitForInterval, true);
const continuousWithRest = D.compile(D.workout('Continuous with recovery', [
    D.repeat('forever', [
        D.swim(50, { on: D.timing(40), hold: D.timing(25) }),
        D.rest(15),
    ]),
]));
assert.strictEqual(continuousWithRest.entries[0].waitForInterval, false);
assert.strictEqual(continuousWithRest.entries[1].kind, 'rest');
assert.throws(() => D.compile(D.workout('Invalid continuous tail', [
    D.repeat('forever', [D.swim(50, { on: D.timing(40), hold: D.timing(25) })]),
    D.rest(10),
])), /only top-level step/);

const legacy = D.fromLegacy('Legacy', {
    mode: 'pace', pool: 'Bellevue East', direction: 'Near', audio: 'Yes',
    duration: '1:00', interval: '1:15', distance: 100, repetitions: 4,
});
assert.strictEqual(D.compile(legacy).entries.length, 4);
const legacyDescend = D.fromLegacy('Legacy descend', {
    mode: 'pace', pool: 'Bellevue East', direction: 'Near', audio: 'Yes',
    duration: '5:00', interval: '5:30', distance: 500, repetitions: 5,
    strategy: 'negative_split', variation: '4:40',
});
assert.deepStrictEqual(
    D.compile(legacyDescend).entries.map((entry) => entry.targetSeconds),
    [300, 295, 290, 285, 280],
);
const surge = D.parse(`
workout "Surge"
pool "Bellevue East"
2 x 100 surge by 8% on 1:30 hold 1:20
`);
assert.strictEqual(D.compile(surge).entries[0].strategy, 'surge');
assert.strictEqual(D.compile(surge).entries[0].variation, 0.08);
assert.strictEqual(D.compile(D.parse(D.format(surge))).entries[0].variation, 0.08);
const legacySurge = D.fromLegacy('Legacy surge', {
    mode: 'pace', pool: 'Bellevue East', direction: 'Near', audio: 'Yes',
    duration: '1:20', interval: '1:30', distance: 100, repetitions: 2,
    strategy: 'surge', variation: '8',
});
assert.strictEqual(D.compile(legacySurge).entries[0].variation, 0.08);

const nestedSource = `
workout "Quality 50s"
pool "Bellevue East"

repeat 5 rounds {
    10 x 50 on :40 hold :25
    3 x 100 Easy on 1:45 hold 1:30
}
`;
const parsedNested = D.parse(nestedSource);
assert.strictEqual(parsedNested.items[0].count, 5);
assert.strictEqual(D.compile(parsedNested).entries.length, 65);
assert.strictEqual(D.compile(D.parse(D.format(parsedNested))).entries.length, 65);

const parsedProgression = D.parse(`
workout "Descending"
repeat 4 rounds {
    10 x 50 on :40 hold :27 on-change -5s/round hold-change -0.75s/round
}
`);
assert.deepStrictEqual(
    [0, 10, 20, 30].map((index) => {
        const entry = D.compile(parsedProgression).entries[index];
        return [entry.targetSeconds, entry.intervalSeconds];
    }),
    [[27, 40], [26.25, 35], [25.5, 30], [24.75, 25]],
);

const parsedLadder = D.parse(`
workout "Pyramid"
ladder 100 to 500 to 100 step 100 on 1:15 per 100 hold 1:00 per 100
`);
assert.deepStrictEqual(D.compile(parsedLadder).entries.map((entry) => entry.distance), [100, 200, 300, 400, 500, 400, 300, 200, 100]);

const parsedContinuous = D.parse(`
workout "Continuous"
repeat until stopped {
    1 x 50 on :40 hold :25
}
`);
assert.strictEqual(D.compile(parsedContinuous).continuous, true);

const recoveryPlan = D.compile(D.workout('Recovery', [
    D.swim(50, { reps: 4, rests: [30, 20, 10] }),
]));
assert.deepStrictEqual(
    recoveryPlan.entries.map((entry) => entry.kind === 'rest' ? `r${entry.seconds}` : `s${entry.distance}`),
    ['s50', 'r30', 's50', 'r20', 's50', 'r10', 's50'],
);

const activityPlan = D.compile(D.workout('Skills', [
    D.activity('turn', { reps: 2, rests: [60] }),
]));
assert.deepStrictEqual(activityPlan.entries.map((entry) => entry.kind), ['activity', 'rest', 'activity']);

const importedReps = D.importShorthand('4 x 50 :30s', {
    name: 'Broken 200', pool: 'Bellevue East', holdPer100: '1:00',
});
const importedRepsPlan = D.compile(importedReps.model);
assert.deepStrictEqual(
    importedRepsPlan.entries.map((entry) => entry.kind === 'rest' ? `r${entry.seconds}` : `s${entry.distance}`),
    ['s50', 'r30', 's50', 'r30', 's50', 'r30', 's50'],
);
assert.strictEqual(importedRepsPlan.entries[0].targetSeconds, 30);
assert.strictEqual(D.compile(D.parse(D.format(importedReps.model))).entries.length, 7);

const importedSequence = D.importShorthand('150 :90s + 100 :60s + 50', {
    pool: 'Bellevue East', holdPer100: '1:20',
});
assert.deepStrictEqual(
    D.compile(importedSequence.model).entries.map((entry) => entry.kind === 'rest' ? `r${entry.seconds}` : `s${entry.distance}`),
    ['s150', 'r90', 's100', 'r60', 's50'],
);
assert.ok(D.importShorthand('50 + 100 + 50 :30s', {
    pool: 'Bellevue East', holdPer100: '1:20',
}).warnings.some((warning) => warning.includes('only at the end')));

const importedPattern = D.importShorthand('200 (25 fast 25 ez)*', {
    pool: 'Bellevue East', holdPer100: '1:10',
});
assert.strictEqual(importedPattern.model.items[0].distance, 200);
assert.strictEqual(importedPattern.model.items[0].segments.length, 2);
assert.strictEqual(D.compile(importedPattern.model).entries[0].targetSeconds, 140);

const importedContinuousPattern = D.importShorthand('25 fast 25 ez*', {
    pool: 'Bellevue East', holdPer100: '1:10',
});
assert.strictEqual(D.compile(importedContinuousPattern.model).continuous, true);
assert.strictEqual(D.compile(importedContinuousPattern.model).entries[0].distance, 50);
assert.ok(importedContinuousPattern.warnings.some((warning) => warning.includes('until Stop')));

const importedSkills = D.importShorthand('2 turns :60s', { pool: 'Bellevue East' });
assert.deepStrictEqual(D.compile(importedSkills.model).entries.map((entry) => entry.kind), ['activity', 'rest', 'activity']);

const shorthandCorpus = [
    '2 x (12.5 fast 12.5 ez) :30s*',
    '25 fast 25 ez*',
    '2 turns :60s',
    '2 x (12.5 fast 37.5 ez) :30s*',
    '2 dives :90s*',
    '25 fast',
    '2 x 25 :45s',
    '2 x 25 :60s + 2 x (12.5 fast 12.5 ez) :30s*',
    '2 x (turn + 25 fast 25 ez) :60s*',
    '2 x 50 :10s',
    '50 :15s + 2 x 25 :10s',
    '2 x 50 from a dive :60s',
    '200 (25 fast 25 ez)*',
    '4 x 50 :30-20-10s',
    '6 x 50 :30-40-50-60-70s',
    '3 x 100 :2min',
    '3 x 100 :40-20s',
    '50 + 100 + 200 + 100 + 50 :30s',
    '3 x 100 :30-20-10s + 4 x 50 :20-15-10s',
    '2 x (200 + 150 + 100 :30s) :60s',
    '1 x 800',
    '800',
];
shorthandCorpus.forEach((source) => {
    const result = D.importShorthand(source, { pool: 'Bellevue East', holdPer100: '1:00' });
    const plan = D.compile(result.model);
    assert.ok(plan.entries.length > 0 && plan.entries.length <= 256, source);
    assert.doesNotThrow(() => D.parse(D.format(result.model)), source);
});
assert.strictEqual(
    D.compile(D.importShorthand('2 x (200 + 150 + 100 :30s) :60s', {
        pool: 'Bellevue East', holdPer100: '1:00',
    }).model).entries.length,
    9,
);

assert.throws(
    () => D.compile(D.parse('workout "Empty"\npool "Bellevue East"')),
    /at least one step/,
);
assert.throws(
    () => D.compile(D.parse(`
workout "Zero progression"
repeat 2 rounds {
    1 x 50 on :10 hold :01 hold-change -1s/round
}
`)),
    /Hold must stay greater than zero/,
);
assert.throws(
    () => D.compile(D.workout('Oversized', [
        D.swim(25, { reps: D.MAX_ENTRIES, hold: D.timing(10), rests: [1] }),
    ])),
    /controller limit/,
);
assert.throws(() => D.timeSeconds(Infinity), /Invalid time/);
assert.throws(
    () => D.compile(D.workout('x'.repeat(65), [D.rest(1)])),
    /Workout name/,
);
assert.throws(
    () => D.compile(D.workout('Bad direction', [D.rest(1)], { direction: 'sideways' })),
    /Direction/,
);

console.log('DeckScript model/compiler tests passed');
