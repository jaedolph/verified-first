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

    var authUrl = twitchOuthUrl + "?client_id=" + clientId + "&response_type=code&scope=" + scope + "&redirect_uri=" + redirectUri;
    document.getElementById("auth").innerHTML = "<a href='" + authUrl + "' target='_blank'>Click here</a> to authorise application"

    var configUrl = extensionUri + '/config';

    fetch(configUrl, {
        headers: {
            "Content-Type": "application/json",
            "Authorization": authorization,
        }
    }
    ).then(function (response) {
        return response.json();
    }).then(function (test) {
        console.log(test);
        document.getElementById("test").innerHTML = JSON.stringify(test)
    }).catch(function (error) {
        console.error("something went wrong");
        console.error(error);
    });

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
        // console.log(rewards);
        // document.getElementById("rewards").innerHTML = JSON.stringify(rewards)
        for (reward of rewards) {
            console.log(reward);
            const newOption = document.createElement("option");
            newOption.value = reward.id;
            newOption.text = reward.title;
            document.getElementById("reward_select").appendChild(newOption);
        }
    }).catch(function (error) {
        console.error("something went wrong");
        console.error(error);
    });

});

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
        document.getElementById("eventsub").innerHTML = JSON.stringify(eventsub)
    }).catch(function (error) {
        console.error("something went wrong");
        console.error(error);
    });
}

let configForm = document.getElementById("config");
configForm.addEventListener("submit", (e) => {
    e.preventDefault();

    let rewardId = document.getElementById("reward_select").value;
    createEventsub(rewardId)

});
