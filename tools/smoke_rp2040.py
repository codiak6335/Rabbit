#!/usr/bin/env python3
"""Run a non-deploying MicroPython compatibility check on a connected RP2 controller."""

import argparse
import pathlib
import subprocess


ROOT = pathlib.Path(__file__).resolve().parents[1]

CHECK = """
import runtime_support
import displays
import audioalert
import swimset
import workout_runner

assert runtime_support.IS_MICROPYTHON
assert not runtime_support.IS_EMULATOR
assert runtime_support.project_path('/db/pools.json') == '/db/pools.json'
assert workout_runner.WorkoutRunner.MAX_ENTRIES == 256
print('RP2 production imports passed')
"""


def mpremote(device, *args, check=True):
    return subprocess.run(
        ['mpremote', 'connect', device, *args],
        cwd=ROOT,
        check=check,
        text=True,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--device', default='/dev/ttyACM0')
    args = parser.parse_args()

    try:
        mpremote(args.device, 'mount', str(ROOT), 'exec', CHECK)
    finally:
        # A compatibility check enters the REPL, so reboot the existing
        # on-device application whether the check passes or fails.
        mpremote(args.device, 'reset', check=False)


if __name__ == '__main__':
    main()
