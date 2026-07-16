// navigation.js
const navLinks = document.querySelectorAll('nav a');
const mainContent = document.querySelector('main');

let returnDepth = 0;
let currentDivId = document.getElementById('mainmenu')
const previousContent = [];

let pmjsontextarealoaded = 0;
let nwjsonTextarealoaded =  0;

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
    } else if (newdiv === "sprintset") {
        addValuesToPoolsSelect('sspools');
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
        variation: variationValue
    });
    
    console.log(concatenatedValues)

    try {
        await callApi(concatenatedValues);
        document.getElementById('ssPrepButton').style.display = 'none';
        document.getElementById('ssStartButton').style.display = 'block';
        document.getElementById('ssCancelButton').style.display = 'block';
        document.getElementById('ssReturnButton').style.display = 'none';
        toggleReadOnly('sstableofinputs');
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
        variation: variationValue
    });
    

    console.log(concatenatedValues)

    try {
        await callApi(concatenatedValues);
        document.getElementById('PrepButton').style.display = 'none';
        document.getElementById('StartButton').style.display = 'block';
        document.getElementById('CancelButton').style.display = 'block';
        document.getElementById('ReturnButton').style.display = 'none';
        toggleReadOnly('tableofinputs');
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
    } catch (error) {
        alert(error.message);
    }

}

function CancelIt() {
    document.getElementById('StartButton').style.display = 'none';
    document.getElementById('ReturnButton').style.display = 'block';
    document.getElementById('CancelButton').style.display = 'none';
    document.getElementById('PrepButton').style.display = 'block';
    toggleReadOnly('tableofinputs')
}


async function StopIt() {
    try {
        await callApi('/stop');
        document.getElementById('CancelButton').style.display = 'block';
        document.getElementById('StartButton').style.display = 'block';
        document.getElementById('StopButton').style.display = 'none';
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
    } catch (error) {
        alert(error.message);
    }

}

function CancelSprint() {
    document.getElementById('ssStartButton').style.display = 'none';
    document.getElementById('ssReturnButton').style.display = 'block';
    document.getElementById('ssCancelButton').style.display = 'none';
    document.getElementById('ssPrepButton').style.display = 'block';
    toggleReadOnly('sstableofinputs')

}

async function StopSprint() {
    try {
        await callApi('/stop');
        document.getElementById('ssCancelButton').style.display = 'block';
        document.getElementById('ssStartButton').style.display = 'block';
        document.getElementById('ssStopButton').style.display = 'none';
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
