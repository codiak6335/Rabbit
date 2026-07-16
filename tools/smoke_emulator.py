#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


HOST = '127.0.0.1'
PORT = int(os.getenv('RABBIT_SMOKE_PORT', '5017'))
BASE_URL = f'http://{HOST}:{PORT}'


def get_json(path, params=None, expected_status=200):
    url = BASE_URL + path
    if params:
        url += '?' + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            body = response.read().decode()
            status = response.status
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        status = exc.code

    if status != expected_status:
        raise AssertionError(f'{url} returned {status}, expected {expected_status}: {body}')
    return json.loads(body)


def wait_for_server(process):
    deadline = time.time() + 10
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError('emulator exited before accepting requests')
        try:
            get_json('/api/emulator/state')
            return
        except Exception:
            time.sleep(0.2)
    raise TimeoutError('emulator did not start in time')


def main():
    env = os.environ.copy()
    env['RABBIT_EMULATOR'] = '1'
    env['RABBIT_HOST'] = HOST
    env['RABBIT_PORT'] = str(PORT)

    process = subprocess.Popen(
        [sys.executable, 'main.py'],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        wait_for_server(process)
        initial_state = get_json('/api/emulator/state')
        if initial_state['pixelCount'] <= 0:
            raise AssertionError('emulator reported no pixels')
        if 'flatProgress' not in initial_state:
            raise AssertionError('emulator state did not include flat-water progress')
        profile = get_json('/api/emulator/pool-profile')
        if not profile.get('ledPositions') or not profile.get('sections'):
            raise AssertionError('emulator reported an incomplete pool profile')
        if profile.get('ledSpacingMm') != 30:
            raise AssertionError('pool profile did not use 30 mm LED spacing')

        prep_params = {
            'pool': 'Bellevue East',
            'direction': 'Near',
            'audio': 'No',
            'duration': '1.00',
            'distance': '25',
            'repetitions': '1',
            'interval': '2.00',
            'strategy': 'even',
            'variation': '8',
        }
        get_json('/prep', prep_params)
        get_json('/start')
        get_json('/start', expected_status=409)
        time.sleep(0.2)
        running_state = get_json('/api/emulator/state')
        if not running_state['displayLines']:
            raise AssertionError('emulator display did not update while running')

        get_json('/stop')
        deadline = time.time() + 3
        while time.time() < deadline:
            state = get_json('/api/emulator/state')
            if 'Status: Idle' in state.get('displayLines', []):
                break
            time.sleep(0.1)
        else:
            raise AssertionError('emulator did not return to idle after stop')
    finally:
        process.terminate()
        try:
            output, _ = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            output, _ = process.communicate()
        if process.returncode not in (0, -15):
            print(output)
            raise RuntimeError(f'emulator exited with code {process.returncode}')


if __name__ == '__main__':
    main()
