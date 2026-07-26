# DeckScript 2

DeckScript is Coach On Deck's versioned language for structured swimming workouts. It is parsed and expanded in the browser, then packed into a compact execution plan for the RP2040.

## Timing words

- `hold` is the swimmer's pace target.
- `on` is a start-to-start send-off.
- `rest` starts after the preceding swim finishes.
- A block transition is immediate unless a rest is written. The final send-off of one block does not delay the next block.

Every paced swim needs a `hold` value before it can be prepared. Times can be written as `:40`, `1:15`, `4:40`, `30s`, or `2min`. A pace may be applied to the complete repetition, `per 50`, or `per 100`.

```text
workout "Pyramid 100–500"
pool "Bellevue East"
direction near
audio yes

ladder 100 to 500 to 100 step 100 on 1:15 per 100 hold 1:00 per 100
```

## Repeats and progressions

Nested repeats are finite unless `until stopped` is explicit.

```text
repeat 5 rounds {
    10 x 50 on :40 hold :25
    3 x 100 easy on 1:45 hold 1:30
}
```

Round changes can adjust the send-off and Hold target:

```text
repeat 4 rounds {
    10 x 50 on :40 hold :27 on-change -5s/round hold-change -0.75s/round
}
```

`negative split` and `descend` are deliberately different:

- A negative split makes the back half of each repetition faster while preserving its total Hold target.
- A descend changes the Hold target from one repetition or round to the next.

For example, the following produces a 2:22 first 250 and 2:18 second 250 on every repetition:

```text
5 x 500 negative split by :04 on 5:30 hold 4:40
```

A five-repetition descend from 5:00 to 4:40 is a different workout:

```text
5 x 500 on 5:30 hold 5:00 descend to 4:40
```

Use `hold-change` when the descend is attached to enclosing rounds instead of one repeated swim line.

The legacy alternating-length Surge strategy is also explicit:

```text
4 x 100 surge by 8% on 1:30 hold 1:20
```

## Recovery and continuous work

```text
4 x 50 hold :30 rest :30,:20,:10 between reps

repeat until stopped {
    1 x 50 sprint on :40 hold :25
}
```

When Stop is pressed, the active swim or recovery is skipped. Continue starts the next compiled step. Continuous workouts reuse one compiled cycle rather than expanding without a bound.

## Written-set import

The editor can conservatively convert one common swim-set expression at a time:

```text
4 x 50 :30s
150 :90s + 100 :60s + 50
2 x (25 fast 25 easy) :60s*
200 (25 fast 25 easy)*
2 turns :60s
```

Imported recovery is attached to the immediately preceding distance. Ambiguous schedules are reported for review. An imported workout can be saved without Hold targets, but it cannot be prepared until every paced swim has one.

## Controller plan

The readable model is saved as DeckScript source. At preparation time the browser validates and compiles it, then sends a compact `compactExecutionPlan` containing at most 256 finite steps and no more than 12 KiB on the wire. Continuous workouts send only one reusable cycle. The controller validates names, labels, distances, timing ranges, pool selection, entry count, and plan version before initializing the strand.
