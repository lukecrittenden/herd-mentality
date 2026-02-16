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
    menuContainer.innerHTML = "";
    mainContainer.innerHTML = "";
    (stageHandlers[stage] || (() => {}))();
}

// Create element utility function
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
    Object.assign(el, props)
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
    const groupDiv = ev.target.closest(".group-div")
    const user = ev.dataTransfer.getData("text/plain");
    let response;
    // TODO: Change code so it gets parent id instead of looping though all responses
    for (const group in state.matchedResponses) {
        const numberOfResponsesInGroup = state.matchedResponses[group].length;
        for (let i = 0; i < numberOfResponsesInGroup; i++) {
            if (state.matchedResponses[group][i][0] === user) {
                response = state.matchedResponses[group][i][1];
                // Delete user-response pair from group
                state.matchedResponses[group].splice(i, 1)
                // Delete group if empty
                if (state.matchedResponses[group].length === 0) {
                    delete state.matchedResponses[group];
                }
            }
        }
    }
    // If target group is empty, create a new group in currentMatchedResponses
    if (groupDiv.innerHTML === "") {
        const key = Date.now().toString();
        state.matchedResponses[key] = [[user, response]];
    } else {
        // Otherwise, append to existing group
        const targetGroup = groupDiv.dataset.groupKey;
        state.matchedResponses[targetGroup].push([user, response]);
    }
    refreshContainers(state.stage);
}

function copyLink() {
    const link = window.location.href + "/" + code
    navigator.clipboard.writeText(link);
}

function renderLobby() {
    if (currentUser === currentHost) {
        const hostMenu = createElement("div", {id: "host-menu", className: "centered-div"}, menuContainer)
        const innerDiv = createElement("div", {}, hostMenu)
        createElement("button", {
                text: "Start Game", className: "small-button",
                events: {click: () => socket.emit("start-game")}
            }, innerDiv
        );
        // Not implemented yet
        createElement("button", {text: "Select Custom Questions", className: "small-button"}, innerDiv);
        createElement("button", {
                text: "Change Time Per Question [" + timePerQuestion + "]",
                className: "small-button", events: {click: () => socket.emit("change-time-per-question")}
            }, innerDiv
        );
        const link = window.location.href + "/" + code
        createElement("button", {className: "small-button", text: "Copy Link", props: {href: link},
            events: {click: () => copyLink()}}, innerDiv
        );
        createElement("p", {}, hostMenu)
    } else {
        const userMenu = createElement("div", {id: "user-menu", className: "centered-div"}, menuContainer);
        createElement("p", {text: "Waiting for the host to start the game", className: "red-text"}, userMenu);
    }
    createElement("h1", {text: "Room " + code}, mainContainer);
    createElement("div", {id: "messages", className: "messages"}, mainContainer);
    createElement("label", {id: "label", props: {htmlFor: "message"}}, mainContainer);
    createElement("input", {id: "message", className: "message-input", props: {
        placeholder: "[message]", type: "text"}, events: {"keypress": function(e) {
            if (e.key === "Enter") {
                socket.send({data: e.target.value});
                e.target.value = "";
            }}
        }}, mainContainer
    );
}

function renderQuestions() {
    if (currentUser === currentHost) {
        const hostMenu = createElement("div", {id: "host-menu", className: "centered-div"}, menuContainer)
        const innerDiv = createElement("div", {}, hostMenu)
        createElement("button", {text: "End Game", className: "small-button",
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
    let timeLeft = timePerQuestion;
    let timerInterval = setInterval(() => {
        timeLeft--;
        timerText.textContent = timeLeft;
        if (timeLeft <= 0 || state.allUsersResponded) {
            clearInterval(timerInterval)
            // Only sends when user is host to ensure that responses are only matched on
            if (currentUser === currentHost && state.stage === "questions") {
                socket.emit("match-responses");
            }
        }
    }, 1000);
    createElement("h1", {text: state.question}, mainContainer)
    const inputBox = createElement("input", {id: "input", props: {placeholder: "[response]"},
        events: {"keypress": function(e) {
            if (e.key === "Enter") {
                const userResponse = e.target.value;
                socket.emit("answer-question", currentUser, userResponse);
                mainContainer.removeChild(e.target);
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
    const div = createElement("div", {id: "user-menu", className: "centered-div"}, menuContainer);
    let textContent;
    if (currentUser === state.cattleWrangler) {
        textContent = "You are the Cattle Wrangler: drag and drop to match similar responses";
    } else {
        textContent = "Waiting for Cattle Wrangler";
    }
    createElement("p", {text: textContent, className: "red-text"}, div);
    createElement("h1", {text: state.question}, mainContainer);
    const ul = createElement("ul", {id: "ul"}, mainContainer);
    for (let key in state.responses) {
        createElement("li", {text: key + " :) said '" + state.responses[key] + "' "}, ul);
    }
    if (currentUser === state.cattleWrangler) {
        for (const group in state.matchedResponses) {
            const groupDiv = createElement("div", {
                    className: "group-div", events: {drop: dropHandler, dragover: dragOverHandler}
                }, mainContainer
            );
            groupDiv.dataset.groupKey = group;
            const numberOfResponsesInGroup = state.matchedResponses[group].length;
            for (let i = 0; i < numberOfResponsesInGroup; i++) {
                const user = state.matchedResponses[group][i][0];
                const response = state.matchedResponses[group][i][1];
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
        const hostMenu = createElement("div", {id: "host-menu", className: "centered-div"}, menuContainer)
        const innerDiv = createElement("div", {}, hostMenu)
        createElement("button", {text: "End Game", className: "small-button",
            events: {click: () => socket.emit("end-game")}}, innerDiv
        );
    }
    let resultText, winnersText;
    if (state.winners.includes(currentUser)) {
        resultText = "You won :)";
    } else {
        resultText = "You lost :(";
    }
    if (state.winners.length === 1) {
        winnersText = state.winners[0] + " won the game!";
    }
    else {
        // TODO: Make winners list look like A, B, and C; not A, B, C,
        winnersText = "The Winners are ";
        for (let i = 0; i < state.winners.length; i++) {
            winnersText = winnersText.concat(state.winners[i].toString(), ", ");
        }
    }
    createElement("h1", {text: resultText}, mainContainer);
    createElement("p", {text: winnersText}, mainContainer)
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
            displayName += " [" + state.scores[item] + "]";
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