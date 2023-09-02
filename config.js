const twitch = window.Twitch.ext;
const twitchOuthUrl = "https://id.twitch.tv/oauth2/authorize";
//const scope = "channel:read:redemptions%20channel:manage:redemptions";
const scope = "channel:read:redemptions";
const extensionUri = "https://twitch.hv1.jaedolph.net"
const redirectUri = extensionUri + "/auth"


// onAuthorized callback called each time JWT is fired
twitch.onAuthorized((auth) => {
    // save our credentials
    token = auth.token; //JWT passed to backend for authentication
    userId = auth.userId; //opaque userID
    authorization = "Bearer " + auth.token;
    clientId = auth.clientId;
    channelId = auth.channelId;

    getRewards();

});

function getRewards() {
    var rewardsUrl = extensionUri + '/rewards';
    fetch(rewardsUrl, {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
            "Authorization": authorization,
        }
    }).then(function (response) {
        return response.json();
    }).then(function (rewards) {

        document.getElementById("config").innerHTML = `
            <label for="reward_select">Select your "First" channel points reward:</label><br>
            <select name="reward_select" id="reward_select" form="config"></select>
            <input type="submit" value="Submit" onclick="createEventsub()">`

        for (reward of rewards) {
            const newOption = document.createElement("option");
            newOption.value = reward.id;
            newOption.text = reward.title;
            document.getElementById("reward_select").appendChild(newOption);
        }
    }).catch(function (error) {
        console.error("something went wrong");
        console.error(error);
    });
}

function createEventsub(rewardId) {

    var createEventsubUrl = extensionUri + '/eventsub/create?reward_id=' + rewardId;

    fetch(createEventsubUrl, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": authorization,
        }
    }
    ).then(function (response) {
        return response.json();
    }).then(function (eventsub) {
        document.getElementById("eventsub").innerHTML = "Configuration successful"
    }).catch(function (error) {
        console.error("something went wrong");
        console.error(error);
    });
}

let configForm = document.getElementById("config");
configForm.addEventListener("submit", (e) => {
    e.preventDefault();

    let rewardId = document.getElementById("reward_select").value;
    createEventsub(rewardId);

});

let oauthButton = document.getElementById("oauth");

oauthButton.addEventListener("click", () => {
    var authUrl = twitchOuthUrl + "?client_id=" + clientId + "&response_type=code&scope=" + scope + "&redirect_uri=" + redirectUri;
    console.log("auth window open");
    var authText = document.getElementById("auth")
    authText.innerHTML = "Auth in progress";
    // This opens a popup window
    var authWindow = window.open(authUrl, "_blank", "width=500,height=700");
    window.addEventListener('message', (msg) => {
        console.log("closing window");
        authWindow.close();
        if (msg.data == "AUTH_SUCCESSFUL") {
            authText.innerHTML = "Auth success.";
            console.log("auth success");
            getRewards();
        } else {
            authText.innerHTML = "Auth failed, please try again.";
            console.log("auth fail");
        }
    });

});
