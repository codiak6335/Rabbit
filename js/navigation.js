// navigation.js
const navLinks = document.querySelectorAll('nav a');
const mainContent = document.querySelector('main');

let returnDepth = 0;
let currentDivId = document.getElementById('mainmenu')
const previousContent = [];

function showdiv(newdiv) {
    console.log(newdiv)
    currentDivId.style.display = 'none';
    previousContent[returnDepth++] = currentDivId;
   
    if (newdiv === "paceset") {
        addValuesToPoolsSelect('pools');
    } else if (newdiv === "sprintset") {
        addValuesToPoolsSelect('sspools');
    } else if (newdiv === 'poolmanagement') {
        console.log('here I am')
            fetchAndLoadJSON();
    }


    currentDivId = document.getElementById(newdiv);
    currentDivId.style.display = 'block'
    
    
}



function goBack() {
  currentDivId.style.display = 'none';
  currentDivId = previousContent[--returnDepth]
  currentDivId.style.display = 'block'
}



function PrepSprint() {
    const poolsValue = document.getElementById('sspools').value;
    const directionValue = document.getElementById('ssdirection').value;
    const audioValue = document.getElementById('ssaudio').value;
    const durationValue = document.getElementById('ssduration').value;
    const distanceValue = 25;
    const repetitionsValue = 0;
    const intervalValue = durationValue+5;

        // Concatenate the values into a single string
    const concatenatedValues = `/prep?pool=${poolsValue}&direction=${directionValue}&audio=${audioValue}&duration=${durationValue}&distance=${distanceValue}&repetitions=${repetitionsValue}&interval=${intervalValue}`;
    
    console.log(concatenatedValues)

    callApi(concatenatedValues)

    document.getElementById('ssPrepButton').style.display = 'none';
    document.getElementById('ssStartButton').style.display = 'block';
    document.getElementById('ssCancelButton').style.display = 'block';
    document.getElementById('ssReturnButton').style.display = 'none';
    toggleReadOnly('sstableofinputs')
}

function PrepIt() {
    const poolsValue = document.getElementById('pools').value;
    const directionValue = document.getElementById('direction').value;
    const audioValue = document.getElementById('audio').value;
    const durationValue = document.getElementById('duration').value;
    const distanceValue = document.getElementById('distance').value;
    const repetitionsValue = document.getElementById('repetitions').value;
    const intervalValue = document.getElementById('interval').value;

        // Concatenate the values into a single string
    const concatenatedValues = `/prep?pool=${poolsValue}&direction=${directionValue}&audio=${audioValue}&duration=${durationValue}&distance=${distanceValue}&repetitions=${repetitionsValue}&interval=${intervalValue}`;
    

    console.log(concatenatedValues)

    callApi(concatenatedValues)

    document.getElementById('PrepButton').style.display = 'none';
    document.getElementById('StartButton').style.display = 'block';
    document.getElementById('CancelButton').style.display = 'block';
     document.getElementById('ReturnButton').style.display = 'none';
    toggleReadOnly('tableofinputs')
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


function callApi(callme) {
    fetch(callme, {
            method: 'GET', // or 'PUT'
        })
            .then((response) => response.json())
            .then((data) => {
                console.log('Success:', data);
            })
            .catch((error) => {
                console.error('Error:', error);
            });
}

function StartIt() {
    callApi('/start')
    document.getElementById('StartButton').style.display = 'none';
    document.getElementById('ReturnButton').style.display = 'none';
    document.getElementById('CancelButton').style.display = 'none';
    document.getElementById('StopButton').style.display = 'block';

}

function CancelIt() {
    document.getElementById('StartButton').style.display = 'none';
    document.getElementById('ReturnButton').style.display = 'block';
    document.getElementById('CancelButton').style.display = 'none';
    document.getElementById('PrepButton').style.display = 'block';
    toggleReadOnly('tableofinputs')
}


function StopIt() {
    callApi('/stop')
    document.getElementById('CancelButton').style.display = 'block';
    document.getElementById('StartButton').style.display = 'block';
    document.getElementById('StopButton').style.display = 'none';

}


function StartSprint() {
    callApi('/startsprint')
    document.getElementById('ssStartButton').style.display = 'none';
    document.getElementById('ssReturnButton').style.display = 'none';
    document.getElementById('ssCancelButton').style.display = 'none';
    document.getElementById('ssStopButton').style.display = 'block';

}

function CancelSprint() {
    document.getElementById('ssStartButton').style.display = 'none';
    document.getElementById('ssReturnButton').style.display = 'block';
    document.getElementById('ssCancelButton').style.display = 'none';
    document.getElementById('ssPrepButton').style.display = 'block';
    toggleReadOnly('sstableofinputs')

}

function StopSprint() {
    callApi('/stop')
    document.getElementById('ssCancelButton').style.display = 'block';
    document.getElementById('ssStartButton').style.display = 'block';
    document.getElementById('ssStopButton').style.display = 'none';

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
                  if (schoolName === data.defaultSchool) {
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

function FetchPoolsOld() {
    poolsSelect.innerHTML = ''
    fetch('/db/pools.json', {method: 'GET'})
         .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Check if 'data' and 'data.options' are defined
            if (data && data.options) {
                // Access the options array from the JSON data
                const optionsArray = data.options;

                // Populate globalSelect with options from the JSON data
                optionsArray.forEach(optionText => {
                    const optionElement = document.createElement('option');
                    optionElement.text = optionText;
                    optionElement.value = optionText; // You can set a different value if needed
                    poolsSelect.appendChild(optionElement);
                });
                console.log(poolsSelect)
            } else {
                console.error('JSON data or options array is undefined');
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
    function fetchAndLoadJSON() {
            fetch('/db/pools.json', {method: 'GET'}) // Replace with your JSON file URL
                .then(response => response.json())
                .then(data => {
                    // Load the JSON content into the textarea
                    document.getElementById('jsonTextarea').value = JSON.stringify(data, null, 2);
                })
                .catch(error => console.error('Error fetching JSON:', error));
        }

    // Function to submit the edited JSON
    function submitJSON() {
        console.log('submitting')
        const editedJSON = document.getElementById('jsonTextarea').value;

        // Parse the edited JSON
        try {
            const parsedJSON = editedJSON;
            // You can send the parsedJSON to your server for processing here
            console.log('Edited JSON:', parsedJSON);

            // Example: Send the edited JSON to a server using fetch
            
            fetch('/db/pools.json', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: parsedJSON,
            })
            .then(response => response.json())
            .then(data => {
                console.log('Server response:', data);
            })
            .catch(error => console.error('Error submitting JSON:', error));
            
        } catch (error) {
            console.error('Error parsing JSON:', error);
        }
        FetchPools()
    }

    // Function to submit the edited JSON
    function saveaslastled() {
        siblingobj = document.getElementById('ledlocationtext');
        callApi("/saveaslastled/" + siblingobj.value)
    }

    function ledlocationchange(obj) {
        console.log(obj.type)
        var siblingobj;
        if (obj.type == "range") {
            siblingobj = document.getElementById('ledlocationtext');
        } else {
            siblingobj = document.getElementById('ledlocationslide');
        }
        siblingobj.value = obj.value
        callApi("/IgniteLedLoc/" + obj.value)
    }

