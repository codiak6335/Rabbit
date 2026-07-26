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


def post_json(path, payload, expected_status=200, token=None):
    url = BASE_URL + path
    if token:
        url += '?' + urllib.parse.urlencode({'token': token})
    body = json.dumps(payload).encode()
    request = urllib.request.Request(
        url,
        data=body,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            response_body = response.read().decode()
            status = response.status
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode()
        status = exc.code

    if status != expected_status:
        raise AssertionError(f'{url} returned {status}, expected {expected_status}: {response_body}')
    return json.loads(response_body)


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


def assert_quiet_server_output(output):
    noisy_markers = ('microdot.Request object', 'GET /api/')
    found = [marker for marker in noisy_markers if marker in output]
    if found:
        raise AssertionError(f'default emulator output included request tracing: {found}')


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
        with urllib.request.urlopen(BASE_URL + '/', timeout=5) as response:
            index_body = response.read().decode()
        if '<title>Coach On Deck</title>' not in index_body or 'Choose today’s set' not in index_body:
            raise AssertionError('Coach On Deck mobile UI was not served')
        set_status = get_json('/api/set-status')
        if set_status['running'] or set_status['prepped']:
            raise AssertionError('fresh emulator should not report a running or prepped set')
        profile = get_json('/api/emulator/pool-profile')
        if not profile.get('ledPositions') or not profile.get('sections'):
            raise AssertionError('emulator reported an incomplete pool profile')
        if profile.get('ledSpacingMm') != 30:
            raise AssertionError('pool profile did not use 30 mm LED spacing')
        get_json('/ignitemarkers')
        get_json('/loadpools')
        get_json('/IgniteLedLoc/not-a-number', expected_status=400)
        post_json('/db/pools.json', {'defaultPool': 'Missing', 'pools': {}}, expected_status=400)
        saved_sets = {
            'sets': {
                'Smoke Pace': {
                    'mode': 'pace',
                    'pool': 'Bellevue East',
                    'direction': 'Near',
                    'audio': 'No',
                    'duration': '30.00',
                    'distance': 50,
                    'repetitions': 20,
                    'interval': '45.00',
                    'strategy': 'negative_split',
                    'variation': '28.00',
                },
                'Smoke Workout': {
                    'format': 'deckscript',
                    'version': 2,
                    'source': 'workout "Smoke Workout"\\npool "Bellevue East"\\n1 x 25 on :02 hold :01',
                }
            }
        }
        original_sets = get_json('/db/sets.json')
        post_json('/db/sets.json', saved_sets)
        loaded_sets = get_json('/db/sets.json')
        if loaded_sets.get('sets', {}).get('Smoke Pace', {}).get('duration') != '30.00':
            raise AssertionError(f'saved sets were not persisted: {loaded_sets}')
        if loaded_sets.get('sets', {}).get('Smoke Workout', {}).get('version') != 2:
            raise AssertionError(f'DeckScript set was not persisted: {loaded_sets}')
        post_json('/db/sets.json', {'sets': {'Bad': {'mode': 'pace'}}}, expected_status=400)
        invalid_saved_sets = json.loads(json.dumps(saved_sets))
        invalid_saved_sets['sets']['Smoke Pace']['strategy'] = 'invalid'
        post_json('/db/sets.json', invalid_saved_sets, expected_status=400)
        invalid_saved_sets = json.loads(json.dumps(saved_sets))
        invalid_saved_sets['sets']['Smoke Workout']['version'] = 99
        post_json('/db/sets.json', invalid_saved_sets, expected_status=400)
        post_json('/db/sets.json', original_sets)

        prep_params = {
            'pool': 'Bellevue East',
            'direction': 'Near',
            'audio': 'No',
            'duration': '1.00',
            'distance': '25',
            'repetitions': '2',
            'interval': '2.00',
            'strategy': 'even',
            'variation': '8',
        }
        get_json('/prep', prep_params)
        set_status = get_json('/api/set-status')
        if set_status['running'] or not set_status['prepped'] or set_status['mode'] != 'pace':
            raise AssertionError(f'pace prep did not update set status: {set_status}')
        details = set_status.get('setDetails') or {}
        if details.get('distance') != 25 or details.get('targetDurationText') != '1.0':
            raise AssertionError(f'pace prep did not expose target set details: {set_status}')
        if details.get('currentRep') != 1 or details.get('repetitions') != 2:
            raise AssertionError(f'pace prep did not expose current and total reps: {set_status}')
        get_json('/start')
        get_json('/start', expected_status=409)
        time.sleep(0.2)
        running_state = get_json('/api/emulator/state')
        if not running_state['displayLines']:
            raise AssertionError('emulator display did not update while running')
        set_status = get_json('/api/set-status')
        if not set_status['running'] or set_status['mode'] != 'pace':
            raise AssertionError(f'pace start did not update running status: {set_status}')
        details = set_status.get('setDetails') or {}
        if details.get('timeUntilNextRepText') is None:
            raise AssertionError(f'pace running status did not expose next rep countdown: {set_status}')
        if details.get('currentRep') != 1 or details.get('repetitions') != 2:
            raise AssertionError(f'pace running status did not expose current and total reps: {set_status}')
        if not any(line.startswith('Dist:') for line in set_status.get('displayLines', [])):
            raise AssertionError(f'pace running display did not include distance and target duration: {set_status}')
        if not any(line.startswith('Rep:1/2') for line in set_status.get('displayLines', [])):
            raise AssertionError(f'pace running display did not include current and total reps: {set_status}')

        get_json('/stop')
        deadline = time.time() + 3
        while time.time() < deadline:
            state = get_json('/api/emulator/state')
            if 'Status: Idle' in state.get('displayLines', []):
                break
            time.sleep(0.1)
        else:
            raise AssertionError('emulator did not return to idle after stop')
        set_status = get_json('/api/set-status')
        if set_status['running'] or not set_status['prepped'] or set_status['mode'] != 'pace':
            raise AssertionError(f'stop should preserve the prepared pace set: {set_status}')
        details = set_status.get('setDetails') or {}
        if details.get('currentRep') != 2 or set_status.get('complete'):
            raise AssertionError(f'stop should pause and advance to rep 2: {set_status}')

        get_json('/start')
        time.sleep(0.2)
        resumed_status = get_json('/api/set-status')
        if not resumed_status['running'] or (resumed_status.get('setDetails') or {}).get('currentRep') != 2:
            raise AssertionError(f'continue should resume at rep 2: {resumed_status}')
        get_json('/stop')
        completed_status = get_json('/api/set-status')
        if completed_status['running'] or not completed_status.get('complete'):
            raise AssertionError(f'stopping the final rep should complete the set: {completed_status}')
        get_json('/cancel-prep')
        set_status = get_json('/api/set-status')
        if set_status['running'] or set_status['prepped'] or set_status['mode'] is not None:
            raise AssertionError(f'cancel prep did not clear set status: {set_status}')

        negative_split_params = prep_params.copy()
        negative_split_params.update({
            'duration': '10.00',
            'distance': '50',
            'interval': '12.00',
            'repetitions': '2',
            'strategy': 'negative_split',
            'variation': '8.00',
        })
        get_json('/prep', negative_split_params)
        set_status = get_json('/api/set-status')
        details = set_status.get('setDetails') or {}
        if details.get('targetDurationText') != '10.0' or details.get('lastTargetDurationText') != '8.0':
            raise AssertionError(f'negative split status did not expose adjusted current split target: {set_status}')
        get_json('/cancel-prep')

        workout_plan = {
            'version': 2,
            'type': 'compactExecutionPlan',
            'name': 'Smoke Workout',
            'pool': 'Bellevue East',
            'direction': 'Near',
            'audio': 'No',
            'continuous': False,
            'entries': [
                ['s', 25, 0.3, 0.5, 'Fast', None, None, 1, 2, 1, 2],
                ['s', 25, 0.3, 0.5, 'Easy', None, None, 2, 2, 2, 2],
            ],
        }
        post_json('/api/workout/prepare', {'plan': workout_plan})
        workout_status = get_json('/api/set-status')
        if workout_status.get('mode') != 'workout' or not workout_status.get('prepped'):
            raise AssertionError(f'workout prep did not update status: {workout_status}')
        get_json('/start', expected_status=409)
        post_json('/api/workout/start', {})
        post_json('/api/workout/start', {}, expected_status=409)
        time.sleep(0.08)
        get_json('/stop')
        workout_status = get_json('/api/set-status')
        if workout_status.get('running') or workout_status.get('workout', {}).get('entryIndex') != 1:
            raise AssertionError(f'workout stop did not skip to the next swim: {workout_status}')
        post_json('/api/workout/start', {})
        deadline = time.time() + 2
        while time.time() < deadline:
            workout_status = get_json('/api/set-status')
            if workout_status.get('complete'):
                break
            time.sleep(0.05)
        else:
            raise AssertionError(f'workout did not complete: {workout_status}')
        get_json('/cancel-prep')
        invalid_workout = json.loads(json.dumps(workout_plan))
        invalid_workout['entries'][0][2] = None
        post_json('/api/workout/prepare', {'plan': invalid_workout}, expected_status=400)
        post_json('/api/workout/prepare', {'padding': 'x' * 12500}, expected_status=400)
        negative_split_plan = json.loads(json.dumps(workout_plan))
        negative_split_plan['name'] = 'Negative Split Smoke'
        negative_split_plan['entries'] = [
            ['s', 50, 1, 1, 'Negative split', None, None, 1, 1, 1, 1, 'negativeSplit', 0.2, False],
        ]
        post_json('/api/workout/prepare', {'plan': negative_split_plan})
        negative_status = get_json('/api/set-status')
        if negative_status.get('workout', {}).get('entry', {}).get('strategy') != 'negativeSplit':
            raise AssertionError(f'negative split plan was not preserved: {negative_status}')
        get_json('/cancel-prep')

        token_env = env.copy()
        token_env['RABBIT_PORT'] = str(PORT + 1)
        token_env['RABBIT_ADMIN_TOKEN'] = 'smoke-token'
        token_process = subprocess.Popen(
            [sys.executable, 'main.py'],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            env=token_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        token_base = BASE_URL
        try:
            globals()['BASE_URL'] = f'http://{HOST}:{PORT + 1}'
            wait_for_server(token_process)
            get_json('/LightStrand', expected_status=403)
            get_json('/LightStrand', {'token': 'smoke-token'})
            post_json('/db/pools.json', {'defaultPool': 'Missing', 'pools': {}}, expected_status=403)
            post_json('/db/pools.json', {'defaultPool': 'Missing', 'pools': {}}, expected_status=400, token='smoke-token')
            post_json('/db/sets.json', saved_sets, expected_status=403)
            post_json('/db/sets.json', saved_sets, token='smoke-token')
            post_json('/db/sets.json', original_sets, token='smoke-token')
            post_json('/api/workout/prepare', {'plan': workout_plan}, expected_status=403)
            post_json('/api/workout/prepare', {'plan': workout_plan}, token='smoke-token')
            get_json('/cancel-prep', {'token': 'smoke-token'})
        finally:
            globals()['BASE_URL'] = token_base
            token_process.terminate()
            try:
                token_output, _ = token_process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                token_process.kill()
                token_output, _ = token_process.communicate()
            assert_quiet_server_output(token_output)
            if token_process.returncode not in (0, -15):
                print(token_output)
                raise RuntimeError(f'token emulator exited with code {token_process.returncode}')
    finally:
        process.terminate()
        try:
            output, _ = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            output, _ = process.communicate()
        assert_quiet_server_output(output)
        if process.returncode not in (0, -15):
            print(output)
            raise RuntimeError(f'emulator exited with code {process.returncode}')


if __name__ == '__main__':
    main()
