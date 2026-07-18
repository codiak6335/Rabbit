// navigation.js
const navLinks = document.querySelectorAll('nav a');
const mainContent = document.querySelector('main');

let returnDepth = 0;
let currentDivId = document.getElementById('mainmenu')
const previousContent = [];

let pmjsontextarealoaded = 0;
let nwjsonTextarealoaded =  0;
const SET_STATUS_POLL_MS = 1000;
let savedSetsCache = { sets: {} };

function buildPrepQuery(params) {
    return `/prep?${new URLSearchParams(params).toString()}`;
}

function getRabbitToken() {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token') || localStorage.getItem('rabbitToken') || '';
    if (token) {
        localStorage.setItem('rabbitToken', token);
    }
    return token;
}

function rabbitUrl(path) {
    const token = getRabbitToken();
    if (!token) {
        return path;
    }
    const url = new URL(path, window.location.origin);
    url.searchParams.set('token', token);
    return `${url.pathname}${url.search}`;
}

function timeToSeconds(value) {
    const parts = value.split(':');
    let hours = 0;
    let minutes = 0;
    let seconds = 0;

    if (parts.length === 3) {
        hours = Number(parts[0]);
        minutes = Number(parts[1]);
        seconds = Number(parts[2]);
    } else if (parts.length === 2) {
        minutes = Number(parts[0]);
        seconds = Number(parts[1]);
    } else {
        seconds = Number(parts[0]);
    }

    return (hours * 3600) + (minutes * 60) + seconds;
}

function secondsToTimeString(totalSeconds) {
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = (totalSeconds % 60).toFixed(2).padStart(5, '0');
    return `${minutes}:${seconds}`;
}

function addSecondsToTimeString(value, secondsToAdd) {
    return secondsToTimeString(timeToSeconds(value) + secondsToAdd);
}

function showdiv(newdiv) {
    console.log(newdiv)
    currentDivId.style.display = 'none';
    previousContent[returnDepth++] = currentDivId;
   
    if (newdiv === "paceset") {
        addValuesToPoolsSelect('pools');
        LoadSavedSets();
    } else if (newdiv === "sprintset") {
        addValuesToPoolsSelect('sspools');
        LoadSavedSets();
    }

    currentDivId = document.getElementById(newdiv);
    currentDivId.style.display = 'block'
    
    if (newdiv === 'poolmanagement') {
        console.log('show div here I am')
        fetchAndLoadJSON('pmjsonTextarea','/db/pools.json');
    } else if (newdiv === 'networkmanagement') {
        console.log('show dive here I am')
        fetchAndLoadJSON('nwjsonTextarea','/db/wifi.json')
    }

    refreshVisibleSetStatus();
}



function goBack() {
  currentDivId.style.display = 'none';
  currentDivId = previousContent[--returnDepth]
  currentDivId.style.display = 'block'
}



async function PrepSprint() {
    const poolsValue = document.getElementById('sspools').value;
    const directionValue = document.getElementById('ssdirection').value;
    const audioValue = document.getElementById('ssaudio').value;
    const durationValue = document.getElementById('ssduration').value;
    const strategyValue = document.getElementById('ssstrategy').value;
    const variationValue = document.getElementById('ssvariation').value;
    const distanceValue = 25;
    const repetitionsValue = 0;
    const intervalValue = addSecondsToTimeString(durationValue, 5);

    const concatenatedValues = buildPrepQuery({
        pool: poolsValue,
        direction: directionValue,
        audio: audioValue,
        duration: durationValue,
        distance: distanceValue,
        repetitions: repetitionsValue,
        interval: intervalValue,
        strategy: strategyValue,
        variation: variationValue,
        mode: 'sprint'
    });
    
    console.log(concatenatedValues)

    try {
        await callApi(concatenatedValues);
        document.getElementById('ssPrepButton').style.display = 'none';
        document.getElementById('ssStartButton').style.display = 'block';
        document.getElementById('ssCancelButton').style.display = 'block';
        document.getElementById('ssReturnButton').style.display = 'none';
        setInputsDisabled('sstableofinputs', true);
        refreshVisibleSetStatus();
    } catch (error) {
        alert(error.message);
    }
}

async function PrepIt() {
    const poolsValue = document.getElementById('pools').value;
    const directionValue = document.getElementById('direction').value;
    const audioValue = document.getElementById('audio').value;
    const durationValue = document.getElementById('duration').value;
    const distanceValue = document.getElementById('distance').value;
    const repetitionsValue = document.getElementById('repetitions').value;
    const intervalValue = document.getElementById('interval').value;
    const strategyValue = document.getElementById('strategy').value;
    const variationValue = document.getElementById('variation').value;

    const concatenatedValues = buildPrepQuery({
        pool: poolsValue,
        direction: directionValue,
        audio: audioValue,
        duration: durationValue,
        distance: distanceValue,
        repetitions: repetitionsValue,
        interval: intervalValue,
        strategy: strategyValue,
        variation: variationValue,
        mode: 'pace'
    });
    

    console.log(concatenatedValues)

    try {
        await callApi(concatenatedValues);
        document.getElementById('PrepButton').style.display = 'none';
        document.getElementById('StartButton').style.display = 'block';
        document.getElementById('CancelButton').style.display = 'block';
        document.getElementById('ReturnButton').style.display = 'none';
        setInputsDisabled('tableofinputs', true);
        refreshVisibleSetStatus();
    } catch (error) {
        alert(error.message);
    }
}


function toggleReadOnly(parm) {
    const tableofinputs = document.getElementById(parm);
    const inputs = tableofinputs.getElementsByTagName('input');
    for (const element of inputs) {
        element.disabled = !element.disabled; // Toggle the readOnly attribute
    }

    const selects = tableofinputs.getElementsByTagName('select');
    console.log(selects)
    for (const element of selects) {
        element.disabled = !element.disabled; // Toggle the readOnly attribute
    }

}

function setInputsDisabled(parm, disabled) {
    const tableofinputs = document.getElementById(parm);
    const inputs = tableofinputs.getElementsByTagName('input');
    for (const element of inputs) {
        element.disabled = disabled;
    }

    const selects = tableofinputs.getElementsByTagName('select');
    for (const element of selects) {
        element.disabled = disabled;
    }
}

function setDisplay(id, display) {
    document.getElementById(id).style.display = display;
}

function visibleSetPage() {
    if (document.getElementById('paceset').style.display === 'block') {
        return 'pace';
    }
    if (document.getElementById('sprintset').style.display === 'block') {
        return 'sprint';
    }
    return null;
}

function setSetStatusText(id, status, pageMode) {
    const statusNode = document.getElementById(id);
    const modeLabel = status.mode === 'sprint' ? 'Sprint' : 'Pace';
    const displayStatus = (status.displayLines || []).find(line => line.startsWith('Status:') || line.includes('Sprint'));
    const details = status.setDetails || {};
    const detailParts = [];

    if (details.distance !== undefined && details.distance !== null) {
        detailParts.push(`Distance: ${details.distance}`);
    }
    if (details.currentRep !== undefined && details.currentRep !== null) {
        const totalReps = details.repetitions ? details.repetitions : '∞';
        detailParts.push(`Rep: ${details.currentRep}/${totalReps}`);
    }
    if (details.targetDurationText) {
        detailParts.push(`Target: ${details.targetDurationText}`);
    }
    if (
        details.firstTargetDurationText
        && details.lastTargetDurationText
        && details.firstTargetDurationText !== details.lastTargetDurationText
    ) {
        detailParts.push(`First: ${details.firstTargetDurationText}`);
        detailParts.push(`Last: ${details.lastTargetDurationText}`);
    }
    if (details.timeUntilNextRepText) {
        detailParts.push(`Next rep: ${details.timeUntilNextRepText}`);
    } else if (status.running && details.repetitions) {
        detailParts.push('Next rep: none');
    }

    statusNode.style.display = 'block';
    if (status.running) {
        const baseStatus = displayStatus ? `${modeLabel} running - ${displayStatus}` : `${modeLabel} set running`;
        statusNode.textContent = detailParts.length ? `${baseStatus} | ${detailParts.join(' | ')}` : baseStatus;
    } else if (status.prepped && status.mode === pageMode) {
        const baseStatus = `${modeLabel} set prepped`;
        statusNode.textContent = detailParts.length ? `${baseStatus} | ${detailParts.join(' | ')}` : baseStatus;
    } else if (status.prepped) {
        const baseStatus = `${modeLabel} set prepped; switch to the ${modeLabel} page to start or cancel`;
        statusNode.textContent = detailParts.length ? `${baseStatus} | ${detailParts.join(' | ')}` : baseStatus;
    } else {
        statusNode.textContent = 'Status: Idle';
    }
}

function applyPaceControls(status) {
    const matchingPrepped = status.prepped && status.mode === 'pace';
    setSetStatusText('paceStatus', status, 'pace');
    setInputsDisabled('tableofinputs', status.running || matchingPrepped);

    setDisplay('ReturnButton', 'block');
    setDisplay('PrepButton', (!status.running && !matchingPrepped) ? 'block' : 'none');
    setDisplay('StartButton', (!status.running && matchingPrepped) ? 'block' : 'none');
    setDisplay('CancelButton', (!status.running && matchingPrepped) ? 'block' : 'none');
    setDisplay('StopButton', status.running ? 'block' : 'none');
}

function applySprintControls(status) {
    const matchingPrepped = status.prepped && status.mode === 'sprint';
    setSetStatusText('sprintStatus', status, 'sprint');
    setInputsDisabled('sstableofinputs', status.running || matchingPrepped);

    setDisplay('ssReturnButton', 'block');
    setDisplay('ssPrepButton', (!status.running && !matchingPrepped) ? 'block' : 'none');
    setDisplay('ssStartButton', (!status.running && matchingPrepped) ? 'block' : 'none');
    setDisplay('ssCancelButton', (!status.running && matchingPrepped) ? 'block' : 'none');
    setDisplay('ssStopButton', status.running ? 'block' : 'none');
}

async function refreshVisibleSetStatus() {
    const page = visibleSetPage();
    if (!page) {
        return;
    }

    try {
        const status = await callApi('/api/set-status');
        if (page === 'pace') {
            applyPaceControls(status);
        } else if (page === 'sprint') {
            applySprintControls(status);
        }
    } catch (error) {
        const statusId = page === 'pace' ? 'paceStatus' : 'sprintStatus';
        const statusNode = document.getElementById(statusId);
        statusNode.style.display = 'block';
        statusNode.textContent = `Status unavailable: ${error.message}`;
    }
}

function savedSetSelectId(mode) {
    return mode === 'sprint' ? 'sssavedSets' : 'savedSets';
}

function populateSavedSetSelect(mode) {
    const select = document.getElementById(savedSetSelectId(mode));
    if (!select) {
        return;
    }

    select.innerHTML = '';
    const matchingSets = Object.entries(savedSetsCache.sets || {})
        .filter(([, savedSet]) => savedSet.mode === mode)
        .sort(([left], [right]) => left.localeCompare(right));

    for (const [name] of matchingSets) {
        const option = document.createElement('option');
        option.value = name;
        option.text = name;
        select.appendChild(option);
    }
}

async function LoadSavedSets() {
    try {
        const response = await fetch('/db/sets.json', { method: 'GET', cache: 'no-store' });
        if (!response.ok) {
            throw new Error(`Request failed: ${response.status}`);
        }
        savedSetsCache = await response.json();
        populateSavedSetSelect('pace');
        populateSavedSetSelect('sprint');
    } catch (error) {
        console.error('Error loading saved sets:', error);
    }
}

function currentSetFromForm(mode) {
    if (mode === 'sprint') {
        const duration = document.getElementById('ssduration').value;
        return {
            mode: 'sprint',
            pool: document.getElementById('sspools').value,
            direction: document.getElementById('ssdirection').value,
            audio: document.getElementById('ssaudio').value,
            duration,
            distance: 25,
            repetitions: 0,
            interval: addSecondsToTimeString(duration, 5),
            strategy: document.getElementById('ssstrategy').value,
            variation: document.getElementById('ssvariation').value,
        };
    }

    return {
        mode: 'pace',
        pool: document.getElementById('pools').value,
        direction: document.getElementById('direction').value,
        audio: document.getElementById('audio').value,
        duration: document.getElementById('duration').value,
        distance: Number(document.getElementById('distance').value),
        repetitions: Number(document.getElementById('repetitions').value),
        interval: document.getElementById('interval').value,
        strategy: document.getElementById('strategy').value,
        variation: document.getElementById('variation').value,
    };
}

function applySavedSet(savedSet) {
    if (savedSet.mode === 'sprint') {
        document.getElementById('sspools').value = savedSet.pool;
        document.getElementById('ssdirection').value = savedSet.direction;
        document.getElementById('ssaudio').value = savedSet.audio;
        document.getElementById('ssduration').value = savedSet.duration;
        document.getElementById('ssstrategy').value = savedSet.strategy;
        document.getElementById('ssvariation').value = savedSet.variation;
        return;
    }

    document.getElementById('pools').value = savedSet.pool;
    document.getElementById('direction').value = savedSet.direction;
    document.getElementById('audio').value = savedSet.audio;
    document.getElementById('duration').value = savedSet.duration;
    document.getElementById('distance').value = savedSet.distance;
    document.getElementById('repetitions').value = savedSet.repetitions;
    document.getElementById('interval').value = savedSet.interval;
    document.getElementById('strategy').value = savedSet.strategy;
    document.getElementById('variation').value = savedSet.variation;
}

async function SaveCurrentSet(mode) {
    const name = prompt('Saved set name');
    if (!name || !name.trim()) {
        return;
    }

    const normalizedName = name.trim();
    const updatedSets = {
        sets: {
            ...(savedSetsCache.sets || {}),
            [normalizedName]: currentSetFromForm(mode),
        },
    };

    try {
        const response = await fetch(rabbitUrl('/db/sets.json'), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(updatedSets),
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || `Request failed: ${response.status}`);
        }
        savedSetsCache = updatedSets;
        populateSavedSetSelect(mode);
        document.getElementById(savedSetSelectId(mode)).value = normalizedName;
    } catch (error) {
        alert(error.message);
    }
}

function LoadSavedSet(mode) {
    const select = document.getElementById(savedSetSelectId(mode));
    const savedSet = savedSetsCache.sets ? savedSetsCache.sets[select.value] : null;
    if (!savedSet) {
        alert('No saved set selected.');
        return;
    }
    applySavedSet(savedSet);
}


async function callApi(callme) {
    const response = await fetch(rabbitUrl(callme), {
        method: 'GET',
    });
    let data = {};
    try {
        data = await response.json();
    } catch (error) {
        data = {};
    }
    if (!response.ok) {
        throw new Error(data.error || `Request failed: ${response.status}`);
    }
    console.log('Success:', data);
    return data;
}

async function StartIt() {
    try {
        await callApi('/start');
        document.getElementById('StartButton').style.display = 'none';
        document.getElementById('ReturnButton').style.display = 'none';
        document.getElementById('CancelButton').style.display = 'none';
        document.getElementById('StopButton').style.display = 'block';
        refreshVisibleSetStatus();
    } catch (error) {
        alert(error.message);
    }

}

async function CancelIt() {
    try {
        await callApi('/cancel-prep');
        document.getElementById('StartButton').style.display = 'none';
        document.getElementById('ReturnButton').style.display = 'block';
        document.getElementById('CancelButton').style.display = 'none';
        document.getElementById('PrepButton').style.display = 'block';
        setInputsDisabled('tableofinputs', false);
        refreshVisibleSetStatus();
    } catch (error) {
        alert(error.message);
    }
}


async function StopIt() {
    try {
        await callApi('/stop');
        document.getElementById('CancelButton').style.display = 'block';
        document.getElementById('StartButton').style.display = 'block';
        document.getElementById('StopButton').style.display = 'none';
        refreshVisibleSetStatus();
    } catch (error) {
        alert(error.message);
    }

}


async function StartSprint() {
    try {
        await callApi('/startsprint');
        document.getElementById('ssStartButton').style.display = 'none';
        document.getElementById('ssReturnButton').style.display = 'none';
        document.getElementById('ssCancelButton').style.display = 'none';
        document.getElementById('ssStopButton').style.display = 'block';
        refreshVisibleSetStatus();
    } catch (error) {
        alert(error.message);
    }

}

async function CancelSprint() {
    try {
        await callApi('/cancel-prep');
        document.getElementById('ssStartButton').style.display = 'none';
        document.getElementById('ssReturnButton').style.display = 'block';
        document.getElementById('ssCancelButton').style.display = 'none';
        document.getElementById('ssPrepButton').style.display = 'block';
        setInputsDisabled('sstableofinputs', false);
        refreshVisibleSetStatus();
    } catch (error) {
        alert(error.message);
    }
}

async function StopSprint() {
    try {
        await callApi('/stop');
        document.getElementById('ssCancelButton').style.display = 'block';
        document.getElementById('ssStartButton').style.display = 'block';
        document.getElementById('ssStopButton').style.display = 'none';
        refreshVisibleSetStatus();
    } catch (error) {
        alert(error.message);
    }

}




function test()  {
    console.log(document.getElementById('main-content').innerHTML)
}

navLinks.forEach(link => {
    link.addEventListener('click', function (e) {
        e.preventDefault(); // Prevent default link behavior
        const href = this.getAttribute('href');
        loadPage(href);
        history.pushState(null, '', href); // Update the URL
    });
});

// Handle back/forward browser navigation
window.addEventListener('popstate', function () {
    const currentUrl = window.location.pathname;
    loadPage(currentUrl);
});

function validateTimeFormat(input) {
    const regex = /^(?:(?:([01]?[0-9]|2[0-3]):)?([0-5]?[0-9]):)?([0-5]?[0-9])\.(\d{1,3})$/;
    if (!regex.test(input.value)) {
        alert("Invalid time format. Please use [HH:]mm:ss.sss format.");
        //input.value = ""; // Clear the input field
    }
}


const poolsSelect = document.createElement('select');
poolsSelect.style.visibility='hidden';
document.body.appendChild(poolsSelect);
FetchPools()
LoadSavedSets()
window.setInterval(refreshVisibleSetStatus, SET_STATUS_POLL_MS);

function FetchPools() {
    poolsSelect.innerHTML = ''
    fetch('/db/pools.json', {method: 'GET'})
         .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log(data)
            for (const schoolName in data.pools) {
            
            console.log(data.pools)
              if (data.pools.hasOwnProperty(schoolName)) {
                  const option = document.createElement("option");
                  option.text = schoolName;
                  console.log("Appending:")
                  console.log(schoolName)
                  if (schoolName === data.defaultPool) {
                        option.selected = true;
                        console.log("selected")
                    }
                poolsSelect.appendChild(option);
              }
            }
        })
        .catch(error => {
            console.error('Error fetching JSON:', error);
        });
    }
    function addValuesToPoolsSelect(poolelement) {
        console.log('addValuesToPoolsSelect() called');
        // Get the "pools" select element by its ID

        const pSelect = document.getElementById(poolelement);
        pSelect.innerHTML = ""
        console.log(pSelect)
 
        // Iterate through the values and add them to the select element
        for (const option of poolsSelect.options) {
            const clonedOption = option.cloneNode(true);
            clonedOption.selected = option.selected;
            pSelect.appendChild(clonedOption);
        }
    }

    // Call the function to add values to the "pools" select element
function fetchAndLoadJSON(textareaId, jsonFilename) {
    console.log("Fetch in",textareaId, pmjsontextarealoaded, nwjsonTextarealoaded)
    fetch(jsonFilename, { method: 'GET' })
        .then(response => response.json())
        .then(data => {
            const jsonTextarea = document.getElementById(textareaId);
            console.log(jsonTextarea)
            jsonTextarea.value = JSON.stringify(data, null, 2);
            if (textareaId === 'pmjsonTextarea') {
                pmjsontextarealoaded = 1
            } else 
                if (textareaId === 'nwjsonTextarea') {
                    nwjsonTextarealoaded = 1
                }
                console.log("Fetch out",textareaId, pmjsontextarealoaded, nwjsonTextarealoaded)
        })
        .catch(error => console.error('Error fetching JSON:', error));
}
 
    // Function to submit the edited JSON
    function submitJSON(textareaId,filename) {
        console.log("get in", textareaId, pmjsontextarealoaded, nwjsonTextarealoaded)
        if (textareaId === 'pmjsonTextarea') {
            if (pmjsontextarealoaded === 0) {
                alert("Data has not been loaded yet.")
                return
            }
        } else 
            if (textareaId === 'nwjsonTextarea') {
                if (nwjsonTextarealoaded === 0) {
                    alert("Data has not been loaded yet.")
                    return
                }
            }  
       
        console.log('submitting')
        const editedJSON = document.getElementById(textareaId).value;

        // Parse the edited JSON
        try {
            const parsedJSON = JSON.parse(editedJSON);
            // You can send the parsedJSON to your server for processing here
            console.log('Edited JSON:', parsedJSON);

            // Example: Send the edited JSON to a server using fetch
            
            fetch(rabbitUrl(filename), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(parsedJSON),
            })
            .then(response => response.json().then(data => {
                if (!response.ok) {
                    throw new Error(data.error || `Request failed: ${response.status}`);
                }
                return data;
            }))
            .then(data => {
                console.log('Server response:', data);
            })
            .catch(error => alert('Error submitting JSON: ' + error));
           
            
        } catch (error) {
            console.error('Error parsing JSON:', error);
        }
    }

    // Function to submit the edited JSON
    async function saveaslastled() {
        siblingobj = document.getElementById('ledlocationtext');
        try {
            await callApi("/saveaslastled/" + siblingobj.value);
        } catch (error) {
            alert(error.message);
        }
    }

    async function ledlocationchange(obj) {
        console.log(obj.type)
        var siblingobj;
        if (obj.type == "range") {
            siblingobj = document.getElementById('ledlocationtext');
        } else {
            siblingobj = document.getElementById('ledlocationslide');
        }
        siblingobj.value = obj.value
        try {
            await callApi("/IgniteLedLoc/" + obj.value);
        } catch (error) {
            alert(error.message);
        }
    }

    function adjustLedLocation(increment) {
      var siblingobj = document.getElementById('ledlocationtext');
      var currentValue = parseInt(siblingobj.value, 10); // Parse the current value as an integer
      var newValue = currentValue + increment; // Add or subtract based on the 'increment' parameter
      siblingobj.value = newValue; // Update the element's value
      ledlocationchange(siblingobj)
}
