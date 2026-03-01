const socket = io();

const mainContainer = document.getElementById("main");
const usersContainer = document.getElementById("users");
const menuContainer = document.getElementById("menu");

const state = {
    stage: "lobby",
    question: "",
    responses: {},
    matchedResponses: {},
    scores: {},
    cattleWrangler: null,
    pinkCowToken: null,
    winners: [],
    allUsersResponded: false,
    noResponses: false
};

const stageHandlers = {
    "lobby": renderLobby,
    "questions": renderQuestions,
    "match-responses": renderMatchedResponses,
    "final-results": renderFinalResults
};

function refreshContainers(stage) {
    clearActiveTimer();
    menuContainer.innerHTML = "";
    mainContainer.innerHTML = "";
    // Calls the stageHandler function for the current stage
    (stageHandlers[stage] || (() => {}))();
}

// Element utility function
function createElement(type, {id, text, className, props = {}, events = {}} = {}, appendTo) {
    const el = document.createElement(type);
    if (id) {
        el.id = id;
    }
    if (text) {
        el.textContent = text;
    }
    if (className) {
        el.className = className;
    }
    // Assigns properties to element
    Object.assign(el, props);
    // Adds events to element
    for (const evName in events) {
        const handler = events[evName];
        el.addEventListener(evName, handler);
    }
    if (appendTo) appendTo.appendChild(el);
    return el;
}

// Drag and drop functions
// https://www.w3schools.com/html/html5_draganddrop.asp
function dragStartHandler(ev) {
    ev.dataTransfer.setData("text/plain", ev.target.id);
}

function dragOverHandler(ev) {
    ev.preventDefault();
}

function dropHandler(ev) {
    ev.preventDefault();
    // Gets the closest group div to the drop location
    const groupDiv = ev.target.closest(".group-div");
    const userId = ev.dataTransfer.getData("text/plain");
    const draggedEl = document.getElementById(userId);
    const parentGroupDiv = draggedEl.closest(".group-div");
    const parentGroupKey = parentGroupDiv.dataset.groupKey;
    let response;
    // Remove from previous group
    if (parentGroupKey && state.matchedResponses[parentGroupKey]) {
        const groupArray = state.matchedResponses[parentGroupKey];
        let index = -1;
        for (let i = 0; i < groupArray.length; i++) {
            const user = groupArray[i][0];
            if (user === userId) {
                index = i;
                break;
            }
        }
        if (index !== -1) {
            response = groupArray[index][1];
            groupArray.splice(index, 1);
            // Delete group if empty
            if (groupArray.length === 0) {
                delete state.matchedResponses[parentGroupKey];
            }
        }
    }
    // Add to new group
    if (response !== undefined) {
        if (groupDiv.innerHTML === "") {
            const key = Date.now().toString();
            state.matchedResponses[key] = [[userId, response]];
        } else {
            const targetGroup = groupDiv.dataset.groupKey;
            state.matchedResponses[targetGroup].push([userId, response]);
        }
    refreshContainers(state.stage);
    }
}

function copyLink() {
    // Copy room link to clipboard
    const link = window.location.href + "/" + code;
    navigator.clipboard.writeText(link);
}

let activeTimer = null;

// Ensures only one timer can exist at a time
function clearActiveTimer() {
    if (activeTimer) {
        clearInterval(activeTimer);
        activeTimer = null;
    }
}

function renderLobby() {
    if (currentUser === currentHost) {
        const hostMenu = createElement("div", {id: "host-menu", className: "centered-div"}, menuContainer);
        const innerDiv = createElement("div", {}, hostMenu);
        createElement("button", {
                text: "Start Game", className: "small-button",
                events: {click: () => socket.emit("start-game")}
            }, innerDiv
        );
        createElement("button", {
                text: "Change Time Per Question [" + timePerQuestion + "]",
                className: "small-button", events: {click: () => socket.emit("change-time-per-question")}
            }, innerDiv
        );
        const link = window.location.href + "/" + code;
        createElement("button", {className: "small-button", text: "Copy Link", props: {href: link},
            events: {click: () => copyLink()}}, innerDiv
        );
        createElement("p", {}, hostMenu);
    } else {
        const userMenu = createElement("div", {id: "user-menu", className: "centered-div"}, menuContainer);
        createElement("p", {text: "Waiting for the host to start the game", className: "red-text"}, userMenu);
    }
    createElement("h1", {text: "Room " + code}, mainContainer);
    createElement("div", {id: "messages", className: "messages"}, mainContainer);
    createElement("label", {id: "label", props: {htmlFor: "message"}}, mainContainer);
    createElement("input", {id: "message", className: "small-input", props: {
        placeholder: "[message]", type: "text"}, events: {"keypress": function(e) {
            // Sends message to backend when enter key is pressed
            if (e.key === "Enter" && e.target.value !== "") {
                socket.send({data: e.target.value});
                e.target.value = "";
            }}
        }}, mainContainer
    );
}

function renderQuestions() {
    if (currentUser === currentHost) {
        const hostMenu = createElement("div", {id: "host-menu", className: "centered-div"}, menuContainer);
        const innerDiv = createElement("div", {}, hostMenu);
        createElement("button", {text: "End Game", className: "small-button",
            // Click the "End Game" button sends message to backend
            events: {click: () => socket.emit("end-game")}}, innerDiv
        );
    }
    if (state.noResponses) {
        const div = createElement("div", {id: "user-menu", className: "centered-div"}, menuContainer);
        createElement("p", {text: "No responses - moved onto next question", className: "red-text"}, div);
    }
    const timerDiv = createElement("div", {id: "timer-div", className: "centered-div"}, menuContainer);
    const timerText = createElement("p", {id: "timer-text", text: timePerQuestion, className: "red-text"},
        timerDiv
    );
    // Sets the duration of the timer to timePerQuestion
    let timeLeft = timePerQuestion;
    activeTimer = setInterval(() => {
        timeLeft--;
        timerText.textContent = timeLeft;
        if (timeLeft <= 0 || state.allUsersResponded) {
            // Stops timer
            clearActiveTimer();
            // Only sends when user is host to ensure that responses are only matched on
            if (currentUser === currentHost && state.stage === "questions") {
                socket.emit("match-responses");
            }
        }
    }, 1000);
    createElement("h1", {text: state.question}, mainContainer)
    const inputBox = createElement("input", {id: "input", className: "response", props: {placeholder: "[response]"},
        events: {"keypress": function(e) {
            if (e.key === "Enter") {
                const userResponse = e.target.value;
                socket.emit("answer-question", currentUser, userResponse);
                mainContainer.removeChild(e.target); // Removes inputBox
                createElement("p", {text: "Your response: " + userResponse}, mainContainer);
            }}
    }}, mainContainer
    );
    // Automatically focuses on the box - i.e. the user does not have to click on the box first
    inputBox.focus();
    inputBox.select();
}

function renderMatchedResponses() {
    if (currentUser === currentHost) {
        const hostMenu = createElement("div", {id: "host-menu", className: "centered-div"}, menuContainer)
        const innerDiv = createElement("div", {}, hostMenu)
        createElement("button", {
                text: "Next Question", className: "small-button",
                events: {click: () => socket.emit("next-question")}
            }, innerDiv
        );
        createElement("button", {text: "End Game", className: "small-button",
            events: {click: () => socket.emit("end-game")}}, innerDiv
        );
    }
    createElement("h1", {text: state.question}, mainContainer);
    const div = createElement("div", {id: "user-menu", className: "centered-div"}, menuContainer);
    let textContent;
    if (currentUser === state.cattleWrangler) {
        textContent = "You are the Cattle Wrangler: drag and drop to match similar responses";
    } else {
        // Creates a list of all the users who responded and their responses
        const ul = createElement("ul", {id: "ul"}, mainContainer);
        for (let key in state.responses) {
            createElement("li", {text: key + " :) said '" + state.responses[key] + "' "}, ul);
        }
        textContent = "Waiting for Cattle Wrangler";
    }
    createElement("p", {text: textContent, className: "red-text"}, div);
    if (currentUser === state.cattleWrangler) {
        for (const group in state.matchedResponses) {
            // Creates a box for matching responses
            const groupDiv = createElement("div", {
                    className: "group-div", events: {drop: dropHandler, dragover: dragOverHandler}
                }, mainContainer
            );
            groupDiv.dataset.groupKey = group;
            const numberOfResponsesInGroup = state.matchedResponses[group].length;
            for (let i = 0; i < numberOfResponsesInGroup; i++) {
                const user = state.matchedResponses[group][i][0];
                const response = state.matchedResponses[group][i][1];
                // Creates draggable text elements
                createElement("p", {
                        id: user, text: "[" + user + "] " + response, props: {draggable: true},
                        events: {dragstart: dragStartHandler}
                    }, groupDiv
                );
            }
        }
        // Make main container scrollable
        mainContainer.style.overflowY = "scroll";
        // Add a final empty group which allows the Cattle Wrangler to create new groups when matching responses
        const div = createElement("div", {
                className: "group-div", events: {drop: dropHandler, dragover: dragOverHandler}}, mainContainer
        );
        div.dataset.groupKey = Date.now().toString()
        createElement("button", {
                className: "small-button", text: "Submit", events: {
                    click: () => socket.emit("submit-matched-responses", state.matchedResponses)
                }
            }, mainContainer
        );
    }
}

function renderFinalResults() {
    if (currentUser === currentHost) {
        const hostMenu = createElement("div", {id: "host-menu", className: "centered-div"}, menuContainer);
        const innerDiv = createElement("div", {}, hostMenu);
        createElement("button", {text: "End Game", className: "small-button",
            events: {click: () => socket.emit("end-game")}}, innerDiv
        );
        createElement("p", {}, hostMenu);
    }
    let resultText, winnersText;
    // If current user is included on the winners list
    if (state.winners.includes(currentUser)) {
        resultText = "You won :)";
    } else {
        resultText = "You lost :(";
    }
    if (state.winners.length === 1) {
        // One winner
        winnersText = state.winners[0] + " won the game!";
    }
    else {
        // Multiple winners
        winnersText = "The Winners are " + state.winners.join(", ");
    }
    createElement("h1", {text: resultText}, mainContainer);
    createElement("p", {text: winnersText}, mainContainer);
}

refreshContainers(state.stage);

socket.on("message", function addMessage(data) {
    let textContent;
    if (data.user) {
        textContent = data.user + ": " + data.message;
    } else {
        textContent = data;
    }
    const messages = document.getElementById("messages")
    createElement("div", {text: textContent}, messages)
    messages.scrollTop = messages.scrollHeight;
});

socket.on("add-users", function addUser(data) {
    for (let item of data) {
        let displayName = item;
        if (item === currentHost) {
            // Add tag and crown emoji for host
            displayName += " [host] \uD83D\uDC51";
        }
        if (item === state.pinkCowToken) {
            displayName += "\uD83D\uDC37";
        }
        if (state.stage !== "lobby") {
            displayName += " [" + state.scores[item] + "] ";
        }
        const div = createElement("div", {id: "user: " + item, text: displayName}, usersContainer)
        if (currentUser === currentHost && item !== currentHost) {
            createElement("button", {className: "tiny-button", text: "kick", events: {
                click: () => socket.emit("kick-user", item)}}, div
        )}
    }
});

// users must be cleared first before adding users
socket.on("clear-users-list", function clearUsersList() {
    usersContainer.innerHTML = "";
});

socket.on("update-host", function(newHost) {
    currentHost = newHost;
    refreshContainers(state.stage);
});

socket.on("kick-user", function(data) {
   if (data === currentUser) {
        window.location.href = home;
    }
});

socket.on("change-time-per-question", function(time_per_question) {
    timePerQuestion = time_per_question;
    refreshContainers(state.stage);
});

socket.on("lobby", function() {
    state.stage = "lobby";
    refreshContainers(state.stage);
});

socket.on("questions", function([question, noResponses]) {
    state.allUsersResponded = false;
    state.question = question;
    state.noResponses = noResponses;
    state.stage = "questions";
    refreshContainers(state.stage);
});

socket.on("all-users-responded", function() {
    state.allUsersResponded = true;
});

socket.on("update-scores", function([scores, pinkCowToken]) {
    state.scores = scores;
    state.pinkCowToken = pinkCowToken;
});

socket.on("match-responses", function([responses, matchedResponses, cattleWrangler]){
    state.responses = responses;
    state.matchedResponses = matchedResponses;
    state.stage = "match-responses";
    state.cattleWrangler = cattleWrangler;
    refreshContainers(state.stage);
});

socket.on("final-results", function([scores, winners]){
    state.scores = scores;
    state.winners = winners;
    state.stage = "final-results";
    refreshContainers(state.stage);
});