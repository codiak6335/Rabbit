const ledGrid = document.getElementById('led-grid');
const pixelCountNode = document.getElementById('pixel-count');
const litCountNode = document.getElementById('lit-count');
const displayLinesNode = document.getElementById('display-lines');
const audioEventsNode = document.getElementById('audio-events');
const lastAudioNode = document.getElementById('last-audio');
const connectionStatusNode = document.getElementById('connection-status');

let pixels = [];

function ensurePixelNodes(count) {
    if (pixels.length === count) {
        return;
    }

    ledGrid.innerHTML = '';
    pixels = [];

    const fragment = document.createDocumentFragment();
    for (let index = 0; index < count; index += 1) {
        const node = document.createElement('div');
        node.className = 'pixel';
        node.title = `LED ${index}`;
        pixels.push(node);
        fragment.appendChild(node);
    }
    ledGrid.appendChild(fragment);
}

function rgbString(rgb) {
    return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
}

function renderState(state) {
    ensurePixelNodes(state.pixelCount);
    pixelCountNode.textContent = String(state.pixelCount);
    litCountNode.textContent = String(state.litPixels.length);

    for (const node of pixels) {
        node.style.background = '#111';
        node.style.boxShadow = 'inset 0 0 0 1px rgba(255, 255, 255, 0.03)';
    }

    for (const pixel of state.litPixels) {
        const node = pixels[pixel.index];
        if (!node) {
            continue;
        }
        node.style.background = rgbString(pixel.rgb);
        node.style.boxShadow = `0 0 10px ${rgbString(pixel.rgb)}`;
    }

    displayLinesNode.textContent = state.displayLines.length ? state.displayLines.join('\n') : 'Display is idle.';
    audioEventsNode.textContent = state.audioEvents.length
        ? state.audioEvents.map((event) => `${event.ticks_ms}ms  ${event.event}`).join('\n')
        : 'No audio events yet.';
    lastAudioNode.textContent = state.audioEvents.length ? state.audioEvents[state.audioEvents.length - 1].event : 'none';
}

async function pollState() {
    try {
        const response = await fetch('/api/emulator/state', { cache: 'no-store' });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const state = await response.json();
        renderState(state);
        connectionStatusNode.textContent = 'connected';
    } catch (error) {
        connectionStatusNode.textContent = 'retrying';
    }
}

pollState();
window.setInterval(pollState, 150);
