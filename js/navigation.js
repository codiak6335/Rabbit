(function () {
    'use strict';

    const state = {
        screen: 'home',
        history: [],
        sets: {},
        pools: [],
        defaultPool: '',
        selectedName: '',
        selectedSet: null,
        server: null,
        deckPhase: 'idle',
        jsonPath: '',
        poll: null,
        busy: false,
    };

    const $ = (id) => document.getElementById(id);
    const screens = {
        home: $('homeScreen'), review: $('reviewScreen'), editor: $('editorScreen'),
        deck: $('deckScreen'), tools: $('toolsScreen'), json: $('jsonScreen'), led: $('ledScreen'),
    };

    function token() {
        const queryToken = new URLSearchParams(location.search).get('token');
        if (queryToken) localStorage.setItem('rabbitToken', queryToken);
        return queryToken || localStorage.getItem('rabbitToken') || '';
    }

    function url(path) {
        const value = token();
        if (!value) return path;
        const target = new URL(path, location.origin);
        target.searchParams.set('token', value);
        return target.pathname + target.search;
    }

    async function request(path, options) {
        const response = await fetch(url(path), Object.assign({ cache: 'no-store' }, options || {}));
        const text = await response.text();
        let data = {};
        try { data = text ? JSON.parse(text) : {}; } catch (_) { data = { text: text }; }
        if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
        return data;
    }

    function show(screen, push) {
        if (!screens[screen]) return;
        if (push !== false && state.screen !== screen) state.history.push(state.screen);
        Object.keys(screens).forEach((name) => screens[name].classList.toggle('is-active', name === screen));
        state.screen = screen;
        $('backButton').classList.toggle('is-hidden', screen === 'home' || screen === 'deck');
        $('menuButton').classList.toggle('is-hidden', screen === 'deck');
        window.scrollTo(0, 0);
    }

    function goBack() {
        show(state.history.pop() || 'home', false);
    }

    function toast(message) {
        const node = $('toast');
        node.textContent = message;
        node.classList.add('is-visible');
        clearTimeout(toast.timer);
        toast.timer = setTimeout(() => node.classList.remove('is-visible'), 2400);
    }

    function applyTheme(choice) {
        const selected = choice || localStorage.getItem('coachTheme') || 'dark';
        const systemDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        const resolved = selected === 'dark' || (selected === 'system' && systemDark) ? 'dark' : 'light';
        document.documentElement.dataset.theme = selected;
        document.documentElement.dataset.resolvedTheme = resolved;
        localStorage.setItem('coachTheme', selected);
        document.querySelector('meta[name="theme-color"]').setAttribute('content', resolved === 'dark' ? '#071a2b' : '#0878c9');
        document.querySelectorAll('[data-theme-choice]').forEach((button) => {
            button.classList.toggle('is-selected', button.dataset.themeChoice === selected);
            button.setAttribute('aria-pressed', button.dataset.themeChoice === selected ? 'true' : 'false');
        });
    }

    function setConnection(connected) {
        document.querySelector('.app-header').classList.toggle('is-offline', !connected);
        $('poolLabel').textContent = connected ? (state.defaultPool || 'No pool selected') : 'Controller unavailable';
    }

    function formatStrategy(value) {
        return ({ even: 'Even pace', negative_split: 'Negative split', surge: 'Surge' })[value] || value;
    }

    function generatedName(set) {
        if (set.mode === 'sprint') return `${set.duration} sprint`;
        return `${set.repetitions} × ${set.distance} @ ${set.interval}`;
    }

    function describe(set) {
        if (set.mode === 'sprint') return `${set.duration} target · ${formatStrategy(set.strategy)}`;
        return `${set.repetitions} reps · ${set.distance} · ${set.duration} target`;
    }

    function renderSets() {
        const list = $('setList');
        const entries = Object.entries(state.sets);
        list.innerHTML = '';
        if (!entries.length) {
            list.innerHTML = '<div class="empty-state">No saved sets yet.<br>Create one to get on deck.</div>';
            return;
        }
        entries.sort((a, b) => a[0].localeCompare(b[0])).forEach(([name, set]) => {
            const card = document.createElement('button');
            card.type = 'button';
            card.className = 'set-card';
            card.innerHTML =
                `<div class="set-card-top"><h3>${escapeHtml(name || generatedName(set))}</h3><span class="chevron">›</span></div>` +
                `<p>${escapeHtml(describe(set))}</p>` +
                `<div class="set-card-tags"><span class="tag">${set.mode === 'sprint' ? 'Sprint' : 'Pace'}</span>` +
                `<span class="tag">${escapeHtml(set.direction || 'Near')} end</span>` +
                `<span class="tag">${set.audio === 'No' ? 'Silent' : 'Audio'}</span></div>`;
            card.addEventListener('click', () => selectSet(name, set));
            list.appendChild(card);
        });
    }

    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
    }

    function selectSet(name, set) {
        state.selectedName = name || generatedName(set);
        state.selectedSet = Object.assign({}, set);
        renderReview();
        show('review');
    }

    function renderReview() {
        const set = state.selectedSet;
        if (!set) return;
        $('reviewTitle').textContent = state.selectedName || generatedName(set);
        $('reviewSummary').textContent = describe(set);
        $('reviewReps').textContent = set.mode === 'sprint' ? 'Continuous' : set.repetitions;
        $('reviewDistance').textContent = set.distance;
        $('reviewInterval').textContent = set.interval;
        $('reviewTarget').textContent = set.duration;
        $('reviewStrategy').textContent = formatStrategy(set.strategy);
        $('reviewDirection').textContent = `${set.direction || 'Near'} end`;
        $('reviewAudio').textContent = set.audio === 'No' ? 'Off' : 'On';
    }

    function populateEditor(set, name) {
        const value = set || {
            mode: 'pace', pool: state.defaultPool, direction: 'Near', audio: 'Yes',
            duration: '1:20.0', distance: 100, repetitions: 10, interval: '1:30.0',
            strategy: 'even', variation: '8',
        };
        $('editorTitle').textContent = set ? 'Edit set' : 'Create a set';
        $('setName').value = name || '';
        $('setMode').value = value.mode || 'pace';
        $('setPool').value = value.pool || state.defaultPool;
        $('setDirection').value = value.direction || 'Near';
        $('setAudio').value = value.audio || 'Yes';
        $('setDuration').value = value.duration || '';
        $('setDistance').value = value.distance || 25;
        $('setRepetitions').value = value.repetitions || 1;
        $('setInterval').value = value.interval || '';
        $('setStrategy').value = value.strategy || 'even';
        $('setVariation').value = value.variation == null ? '8' : value.variation;
        syncModeFields();
        $('formError').classList.add('is-hidden');
    }

    function syncModeFields() {
        const sprint = $('setMode').value === 'sprint';
        $('setRepetitions').disabled = sprint;
        $('setDistance').disabled = sprint;
        if (sprint) {
            $('setRepetitions').value = 0;
            $('setDistance').value = 25;
        } else {
            if (Number($('setRepetitions').value) < 1) $('setRepetitions').value = 10;
        }
    }

    function setFromForm() {
        const sprint = $('setMode').value === 'sprint';
        const set = {
            mode: sprint ? 'sprint' : 'pace',
            pool: $('setPool').value,
            direction: $('setDirection').value,
            audio: $('setAudio').value,
            duration: $('setDuration').value.trim(),
            distance: sprint ? 25 : Number($('setDistance').value),
            repetitions: sprint ? 0 : Number($('setRepetitions').value),
            interval: $('setInterval').value.trim(),
            strategy: $('setStrategy').value,
            variation: $('setVariation').value.trim(),
        };
        if (!set.pool) throw new Error('Choose a pool.');
        if (!set.duration || !set.interval) throw new Error('Enter target time and send-off.');
        if (!sprint && (!set.distance || !set.repetitions)) throw new Error('Distance and repetitions must be greater than zero.');
        return set;
    }

    async function saveSet() {
        try {
            const set = setFromForm();
            const customName = $('setName').value.trim();
            const name = customName || generatedName(set);
            state.sets[name] = set;
            await request('/db/sets.json', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sets: state.sets }),
            });
            renderSets();
            toast(`Saved “${name}”`);
            selectSet(name, set);
        } catch (error) { showFormError(error.message); }
    }

    function showFormError(message) {
        $('formError').textContent = message;
        $('formError').classList.remove('is-hidden');
    }

    function prepPath(set) {
        const params = new URLSearchParams(set);
        return `/prep?${params.toString()}`;
    }

    async function prepare() {
        if (!state.selectedSet || state.busy) return;
        setBusy($('prepareButton'), true, 'Preparing…');
        try {
            await request(prepPath(state.selectedSet));
            state.deckPhase = 'prepared';
            updateDeck({ running: false, prepped: true, mode: state.selectedSet.mode, setDetails: {
                currentRep: 1, repetitions: state.selectedSet.repetitions,
                timeUntilNextRepText: null,
            }});
            state.history = [];
            show('deck', false);
        } catch (error) {
            toast(error.message);
        } finally { setBusy($('prepareButton'), false, 'Prepare set'); }
    }

    function setBusy(button, busy, label) {
        state.busy = busy;
        button.disabled = busy;
        const span = button.querySelector('span');
        if (span) span.textContent = label; else button.textContent = label;
    }

    function updateDeck(status) {
        if (!status) return;
        state.server = status;
        const details = status.setDetails || {};
        const total = details.repetitions || (state.selectedSet && state.selectedSet.repetitions) || '∞';
        const current = details.currentRep || 1;
        $('deckSetName').textContent = state.selectedName || (state.selectedSet ? generatedName(state.selectedSet) : 'Current set');
        $('currentRep').textContent = current;
        $('totalReps').textContent = total || '∞';

        const primary = $('deckPrimaryButton');
        primary.classList.remove('is-start', 'is-stop');
        if (status.running) {
            state.deckPhase = 'running';
            $('deckState').textContent = 'Running';
            $('countdownLabel').textContent = 'Next start';
            $('countdownValue').textContent = details.timeUntilNextRepText || '—:—';
            $('deckMessage').textContent = 'Stop ends this rep and queues the next one.';
            primary.textContent = 'Stop';
            primary.classList.add('is-stop');
        } else if (status.complete) {
            state.deckPhase = 'complete';
            $('deckState').textContent = 'Complete';
            $('countdownLabel').textContent = 'Set finished';
            $('countdownValue').textContent = 'DONE';
            $('deckMessage').textContent = 'Nice work. Run it again or choose another set.';
            primary.textContent = 'Run again';
            primary.classList.add('is-start');
        } else if (status.prepped) {
            state.deckPhase = current > 1 ? 'paused' : 'prepared';
            $('deckState').textContent = current > 1 ? 'Paused' : 'Ready';
            $('countdownLabel').textContent = current > 1 ? 'Next up' : 'Ready to start';
            $('countdownValue').textContent = current > 1 ? `REP ${current}` : '—:—';
            $('deckMessage').textContent = current > 1 ? `Rep ${current - 1} ended. Continue when the lane is ready.` : 'Timing and LEDs are prepared.';
            primary.textContent = current > 1 ? 'Continue' : 'Start';
            primary.classList.add('is-start');
        } else {
            state.deckPhase = 'idle';
        }
    }

    async function deckPrimary() {
        if (state.busy) return;
        const button = $('deckPrimaryButton');
        state.busy = true;
        button.disabled = true;
        try {
            if (state.deckPhase === 'running') {
                await request('/stop');
                await refreshStatus();
            } else if (state.deckPhase === 'complete') {
                await prepare();
            } else {
                await request(state.selectedSet && state.selectedSet.mode === 'sprint' ? '/startsprint' : '/start');
                await refreshStatus();
            }
        } catch (error) { toast(error.message); }
        finally { state.busy = false; button.disabled = false; }
    }

    async function refreshStatus() {
        try {
            const status = await request('/api/set-status');
            setConnection(true);
            state.server = status;
            if (state.screen === 'deck') updateDeck(status);
            const resumable = status.prepped || status.running;
            $('resumeCard').classList.toggle('is-hidden', !resumable);
            if (resumable) {
                const details = status.setDetails || {};
                $('resumeTitle').textContent = status.running ? 'Set running' : 'Set ready';
                $('resumeMeta').textContent = `Rep ${details.currentRep || 1} of ${details.repetitions || '∞'}`;
                $('resumeButton').textContent = status.running ? 'View' : 'Return';
            }
        } catch (_) {
            setConnection(false);
        }
    }

    async function mainMenu() {
        show('home', false);
    }

    async function openJson(kind) {
        state.jsonPath = kind === 'pool' ? '/db/pools.json' : '/db/wifi.json';
        $('jsonTitle').textContent = kind === 'pool' ? 'Pool settings' : 'Network settings';
        $('jsonMessage').textContent = 'Loading…';
        show('json');
        try {
            const data = await request(state.jsonPath);
            $('jsonEditor').value = JSON.stringify(data, null, 2);
            $('jsonMessage').textContent = '';
        } catch (error) { $('jsonMessage').textContent = error.message; }
    }

    async function saveJson() {
        try {
            const data = JSON.parse($('jsonEditor').value);
            await request(state.jsonPath, {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
            });
            $('jsonMessage').textContent = 'Saved successfully.';
            if (state.jsonPath.indexOf('pools') >= 0) await loadData();
        } catch (error) { $('jsonMessage').textContent = error.message; }
    }

    async function loadData() {
        const [poolData, setData] = await Promise.all([request('/db/pools.json'), request('/db/sets.json')]);
        state.defaultPool = poolData.defaultPool || '';
        state.pools = Object.keys(poolData.pools || {});
        state.sets = setData.sets || {};
        $('poolLabel').textContent = state.defaultPool || 'No pool selected';
        $('setPool').innerHTML = state.pools.map((name) => `<option${name === state.defaultPool ? ' selected' : ''}>${escapeHtml(name)}</option>`).join('');
        renderSets();
    }

    function bind() {
        document.querySelectorAll('[data-theme-choice]').forEach((button) => {
            button.addEventListener('click', () => applyTheme(button.dataset.themeChoice));
        });
        $('backButton').addEventListener('click', goBack);
        $('menuButton').addEventListener('click', () => show('tools'));
        $('newSetButton').addEventListener('click', () => { populateEditor(); show('editor'); });
        $('editSetButton').addEventListener('click', () => { populateEditor(state.selectedSet, state.selectedName); show('editor'); });
        $('prepareButton').addEventListener('click', prepare);
        $('setMode').addEventListener('change', syncModeFields);
        $('setForm').addEventListener('submit', (event) => {
            event.preventDefault();
            try {
                const set = setFromForm();
                state.selectedSet = set;
                state.selectedName = $('setName').value.trim() || generatedName(set);
                renderReview();
                show('review');
            } catch (error) { showFormError(error.message); }
        });
        $('saveSetButton').addEventListener('click', saveSet);
        $('deckPrimaryButton').addEventListener('click', deckPrimary);
        $('deckMenuButton').addEventListener('click', mainMenu);
        $('resumeButton').addEventListener('click', () => {
            if (state.server && !state.selectedSet) {
                const details = state.server.setDetails || {};
                state.selectedSet = { mode: state.server.mode || 'pace', repetitions: details.repetitions || 0 };
                state.selectedName = 'Current set';
            }
            updateDeck(state.server);
            show('deck', false);
        });
        document.querySelectorAll('[data-tool]').forEach((button) => button.addEventListener('click', () => {
            const tool = button.dataset.tool;
            if (tool === 'led') show('led'); else openJson(tool);
        }));
        document.querySelectorAll('[data-api]').forEach((button) => button.addEventListener('click', async () => {
            try { await request(button.dataset.api); $('ledMessage').textContent = 'Command completed.'; }
            catch (error) { $('ledMessage').textContent = error.message; }
        }));
        $('saveJsonButton').addEventListener('click', saveJson);
        $('resetButton').addEventListener('click', async () => {
            if (!confirm('Restart the controller? This interrupts the current session.')) return;
            try { await request('/HardReset'); toast('Controller restarting'); } catch (error) { toast(error.message); }
        });
        if (location.port === '5000') {
            $('emulatorLink').classList.remove('is-hidden');
            $('emulatorLink').addEventListener('click', () => { location.href = '/emulator'; });
        }
    }

    async function init() {
        bind();
        applyTheme(document.documentElement.dataset.theme || 'dark');
        if (window.matchMedia) {
            const media = window.matchMedia('(prefers-color-scheme: dark)');
            if (media.addEventListener) {
                media.addEventListener('change', () => {
                    if (document.documentElement.dataset.theme === 'system') applyTheme('system');
                });
            }
        }
        try { await loadData(); }
        catch (error) { $('setList').innerHTML = `<div class="empty-state">Could not load sets.<br>${escapeHtml(error.message)}</div>`; }
        await refreshStatus();
        state.poll = setInterval(refreshStatus, 1000);
    }

    init();
}());
