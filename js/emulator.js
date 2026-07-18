const pixelCountNode = document.getElementById('pixel-count');
const litCountNode = document.getElementById('lit-count');
const displayLinesNode = document.getElementById('display-lines');
const audioEventsNode = document.getElementById('audio-events');
const lastAudioNode = document.getElementById('last-audio');
const connectionStatusNode = document.getElementById('connection-status');
const poolMapCanvas = document.getElementById('pool-map-canvas');
const poolMapMetaNode = document.getElementById('pool-map-meta');
const profileCanvas = document.getElementById('pool-profile-canvas');
const profileMetaNode = document.getElementById('pool-profile-meta');

let poolProfile = null;
const CHART_LEFT_PADDING = 52;
const CHART_RIGHT_PADDING = 32;

function rgbString(rgb) {
    return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
}

function fitCanvasToDisplaySize(canvas) {
    const ratio = window.devicePixelRatio || 1;
    const width = Math.max(1, Math.floor(canvas.clientWidth * ratio));
    const height = Math.max(1, Math.floor(canvas.clientHeight * ratio));
    if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
    }
    const context = canvas.getContext('2d');
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    return context;
}

function pointForLed(led) {
    if (!poolProfile || !poolProfile.ledPositions.length) {
        return null;
    }
    if (led < 0) {
        return poolProfile.ledPositions[0];
    }
    if (led >= poolProfile.ledPositions.length) {
        return poolProfile.ledPositions[poolProfile.ledPositions.length - 1];
    }
    return poolProfile.ledPositions[led];
}

function depthColor(depthFeet, minDepth, maxDepth) {
    const span = Math.max(0.01, maxDepth - minDepth);
    const t = Math.max(0, Math.min(1, (depthFeet - minDepth) / span));
    const shallow = [64, 190, 198];
    const deep = [9, 55, 105];
    return shallow.map((channel, index) => Math.round(channel + ((deep[index] - channel) * t)));
}

function depthAtDistance(distanceFeet) {
    if (!poolProfile || !poolProfile.ledPositions.length) {
        return 0;
    }

    let closest = poolProfile.ledPositions[0];
    let closestDistance = Math.abs(distanceFeet - closest.distanceFeet);
    for (const position of poolProfile.ledPositions) {
        const delta = Math.abs(distanceFeet - position.distanceFeet);
        if (delta < closestDistance) {
            closest = position;
            closestDistance = delta;
        }
    }
    return closest.depthFeet;
}

function renderTopDownPoolMap(state) {
    if (!poolProfile || !poolMapCanvas) {
        return;
    }

    const context = fitCanvasToDisplaySize(poolMapCanvas);
    const width = poolMapCanvas.clientWidth;
    const height = poolMapCanvas.clientHeight;
    const padding = {
        top: 42,
        right: CHART_RIGHT_PADDING,
        bottom: 46,
        left: CHART_LEFT_PADDING,
    };
    const laneWidthFeet = 8;
    const mapWidth = Math.max(1, width - padding.left - padding.right);
    const mapHeight = Math.max(1, height - padding.top - padding.bottom);
    const poolLength = Math.max(poolProfile.lengthFeet, ...poolProfile.ledPositions.map((item) => item.distanceFeet));
    const depths = poolProfile.ledPositions.map((item) => item.depthFeet);
    const minDepth = Math.min(...depths);
    const maxDepth = Math.max(...depths);

    function xFor(distanceFeet) {
        return padding.left + (distanceFeet / poolLength) * mapWidth;
    }

    function yFor(offsetFeet) {
        return padding.top + ((offsetFeet + (laneWidthFeet / 2)) / laneWidthFeet) * mapHeight;
    }

    context.clearRect(0, 0, width, height);
    context.fillStyle = '#071117';
    context.fillRect(0, 0, width, height);

    for (let column = 0; column < mapWidth; column += 1) {
        const distanceFeet = (column / mapWidth) * poolLength;
        const depthFeet = depthAtDistance(distanceFeet);
        const rgb = depthColor(depthFeet, minDepth, maxDepth);
        context.fillStyle = `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
        context.fillRect(padding.left + column, padding.top, 1.5, mapHeight);
    }

    const waterGradient = context.createLinearGradient(0, padding.top, 0, padding.top + mapHeight);
    waterGradient.addColorStop(0, 'rgba(235, 255, 255, 0.22)');
    waterGradient.addColorStop(0.5, 'rgba(255, 255, 255, 0.03)');
    waterGradient.addColorStop(1, 'rgba(0, 0, 0, 0.22)');
    context.fillStyle = waterGradient;
    context.fillRect(padding.left, padding.top, mapWidth, mapHeight);

    context.strokeStyle = 'rgba(255, 255, 255, 0.7)';
    context.lineWidth = 2;
    context.strokeRect(padding.left, padding.top, mapWidth, mapHeight);

    context.strokeStyle = 'rgba(255, 255, 255, 0.32)';
    context.lineWidth = 1;
    for (const offset of [-2, 0, 2]) {
        const y = yFor(offset);
        context.beginPath();
        context.moveTo(padding.left, y);
        context.lineTo(padding.left + mapWidth, y);
        context.stroke();
    }

    context.strokeStyle = 'rgba(255, 255, 255, 0.18)';
    context.setLineDash([6, 7]);
    for (const marker of poolProfile.markers || []) {
        const x = xFor(marker.distanceFeet);
        context.beginPath();
        context.moveTo(x, padding.top);
        context.lineTo(x, padding.top + mapHeight);
        context.stroke();
    }
    context.setLineDash([]);

    context.fillStyle = 'rgba(238, 244, 247, 0.9)';
    context.font = '12px IBM Plex Sans, Segoe UI, sans-serif';
    context.fillText('Near wall', padding.left, padding.top - 16);
    context.fillText('Far wall', padding.left + mapWidth - 46, padding.top - 16);

    for (const marker of poolProfile.markers || []) {
        const x = xFor(marker.distanceFeet);
        const depth = depthAtDistance(marker.distanceFeet);
        context.fillStyle = 'rgba(238, 244, 247, 0.75)';
        context.fillText(`${depth.toFixed(1)} ft`, x - 16, padding.top + mapHeight + 22);
    }

    context.fillStyle = 'rgba(255, 255, 255, 0.26)';
    for (const position of poolProfile.ledPositions) {
        const x = xFor(position.distanceFeet);
        const y = yFor(0);
        context.beginPath();
        context.arc(x, y, 1.1, 0, Math.PI * 2);
        context.fill();
    }

    for (const pixel of state.litPixels) {
        const point = pointForLed(pixel.index);
        if (!point) {
            continue;
        }
        const x = xFor(point.distanceFeet);
        const y = yFor(0);
        context.fillStyle = rgbString(pixel.rgb);
        context.shadowColor = rgbString(pixel.rgb);
        context.shadowBlur = 12;
        context.beginPath();
        context.arc(x, y, 4.5, 0, Math.PI * 2);
        context.fill();
    }
    context.shadowBlur = 0;

    if (state.flatProgress && state.flatProgress.active) {
        const progress = Math.max(0, Math.min(1, state.flatProgress.fraction));
        const x = padding.left + (progress * mapWidth);
        const y = yFor(-2.8);
        context.fillStyle = '#f7d05c';
        context.shadowColor = '#f7d05c';
        context.shadowBlur = 10;
        context.beginPath();
        context.moveTo(x + 8, y);
        context.lineTo(x - 8, y - 6);
        context.lineTo(x - 8, y + 6);
        context.closePath();
        context.fill();
        context.shadowBlur = 0;
        context.fillStyle = 'rgba(247, 208, 92, 0.95)';
        context.fillText(`${Math.round(progress * 100)}%`, Math.min(width - 64, x + 10), y + 4);
    }

    poolMapMetaNode.textContent = `${poolProfile.poolName} top-down bottom map | ${poolLength.toFixed(0)} ft length | ${minDepth.toFixed(1)}-${maxDepth.toFixed(1)} ft depth`;
}

function renderPoolProfile(state) {
    if (!poolProfile || !profileCanvas) {
        return;
    }

    const context = fitCanvasToDisplaySize(profileCanvas);
    const width = profileCanvas.clientWidth;
    const height = profileCanvas.clientHeight;
    const padding = {
        top: 18,
        right: CHART_RIGHT_PADDING,
        bottom: 28,
        left: CHART_LEFT_PADDING,
    };
    const plotWidth = Math.max(1, width - padding.left - padding.right);
    const plotHeight = Math.max(1, height - padding.top - padding.bottom);
    const positions = poolProfile.ledPositions;
    const maxDistance = Math.max(poolProfile.lengthFeet, ...positions.map((item) => item.distanceFeet));
    const maxDepth = Math.max(1, ...positions.map((item) => item.depthFeet));

    function xFor(distanceFeet) {
        return padding.left + (distanceFeet / maxDistance) * plotWidth;
    }

    function yFor(depthFeet) {
        return padding.top + (depthFeet / maxDepth) * plotHeight;
    }

    context.clearRect(0, 0, width, height);
    context.fillStyle = '#0d151b';
    context.fillRect(0, 0, width, height);

    context.strokeStyle = 'rgba(255, 255, 255, 0.10)';
    context.lineWidth = 1;
    context.beginPath();
    context.moveTo(padding.left, padding.top);
    context.lineTo(padding.left, padding.top + plotHeight);
    context.lineTo(padding.left + plotWidth, padding.top + plotHeight);
    context.stroke();

    context.fillStyle = 'rgba(159, 176, 186, 0.85)';
    context.font = '12px IBM Plex Sans, Segoe UI, sans-serif';
    context.fillText('0 ft', 8, padding.top + 4);
    context.fillText(`${maxDepth.toFixed(1)} ft`, 8, padding.top + plotHeight);
    context.fillText(`${maxDistance.toFixed(0)} ft`, padding.left + plotWidth - 36, height - 8);

    context.strokeStyle = '#425563';
    context.lineWidth = 2;
    context.beginPath();
    for (let index = 0; index < positions.length; index += 1) {
        const point = positions[index];
        const x = xFor(point.distanceFeet);
        const y = yFor(point.depthFeet);
        if (index === 0) {
            context.moveTo(x, y);
        } else {
            context.lineTo(x, y);
        }
    }
    context.stroke();

    context.fillStyle = 'rgba(104, 168, 202, 0.18)';
    context.lineTo(padding.left + plotWidth, padding.top + plotHeight);
    context.lineTo(padding.left, padding.top + plotHeight);
    context.closePath();
    context.fill();

    for (const marker of poolProfile.markers || []) {
        const x = xFor(marker.distanceFeet);
        context.strokeStyle = 'rgba(255, 255, 255, 0.16)';
        context.beginPath();
        context.moveTo(x, padding.top);
        context.lineTo(x, padding.top + plotHeight);
        context.stroke();
    }

    const surfaceY = padding.top;
    context.strokeStyle = 'rgba(66, 217, 255, 0.35)';
    context.lineWidth = 1;
    context.beginPath();
    context.moveTo(padding.left, surfaceY);
    context.lineTo(padding.left + plotWidth, surfaceY);
    context.stroke();

    context.fillStyle = 'rgba(159, 230, 247, 0.9)';
    context.font = '11px IBM Plex Sans, Segoe UI, sans-serif';
    for (const percent of [25, 50, 75]) {
        const x = padding.left + ((percent / 100) * plotWidth);
        context.strokeStyle = 'rgba(159, 230, 247, 0.65)';
        context.beginPath();
        context.moveTo(x, surfaceY - 6);
        context.lineTo(x, surfaceY + 6);
        context.stroke();
        context.fillText(`${percent}%`, x - 10, surfaceY - 9);
    }

    if (state.flatProgress && state.flatProgress.active) {
        const progress = Math.max(0, Math.min(1, state.flatProgress.fraction));
        const x = padding.left + (progress * plotWidth);
        const y = surfaceY;

        context.fillStyle = '#42d9ff';
        context.shadowColor = '#42d9ff';
        context.shadowBlur = 8;
        context.beginPath();
        context.arc(x, y, 5, 0, Math.PI * 2);
        context.fill();
        context.shadowBlur = 0;

        context.font = '11px IBM Plex Sans, Segoe UI, sans-serif';
        const label = `${Math.round(progress * 100)}% time`;
        const labelX = Math.min(width - padding.right - 54, Math.max(padding.left, x + 7));
        context.fillText(label, labelX, y + 15);
    }

    for (const pixel of state.litPixels) {
        const point = pointForLed(pixel.index);
        if (!point) {
            continue;
        }
        const x = xFor(point.distanceFeet);
        const y = yFor(point.depthFeet);
        context.fillStyle = rgbString(pixel.rgb);
        context.shadowColor = rgbString(pixel.rgb);
        context.shadowBlur = 10;
        context.beginPath();
        context.arc(x, y, 3.5, 0, Math.PI * 2);
        context.fill();
    }
    context.shadowBlur = 0;

    profileMetaNode.textContent = `${poolProfile.poolName} | ${poolProfile.ledSpacingMm} mm LED centers | ${poolProfile.depthRangeFeet.toFixed(2)} ft relative depth change`;
}

function renderState(state) {
    pixelCountNode.textContent = String(state.pixelCount);
    litCountNode.textContent = String(state.litPixels.length);

    displayLinesNode.textContent = state.displayLines.length ? state.displayLines.join('\n') : 'Display is idle.';
    audioEventsNode.textContent = state.audioEvents.length
        ? state.audioEvents.map((event) => `${event.ticks_ms}ms  ${event.event}`).join('\n')
        : 'No audio events yet.';
    lastAudioNode.textContent = state.audioEvents.length ? state.audioEvents[state.audioEvents.length - 1].event : 'none';
    renderTopDownPoolMap(state);
    renderPoolProfile(state);
}

async function loadPoolProfile() {
    try {
        const response = await fetch('/api/emulator/pool-profile', { cache: 'no-store' });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        poolProfile = await response.json();
    } catch (error) {
        poolMapMetaNode.textContent = `Pool map unavailable: ${error.message}`;
        profileMetaNode.textContent = `Pool profile unavailable: ${error.message}`;
    }
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

loadPoolProfile().then(pollState);
window.setInterval(pollState, 150);
window.addEventListener('resize', () => {
    fetch('/api/emulator/state', { cache: 'no-store' })
        .then((response) => response.json())
        .then(renderState)
        .catch(() => {});
});
