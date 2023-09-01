const twitch = window.Twitch.ext;
const extensionUri = "https://twitch.hv1.jaedolph.net"

twitch.onAuthorized((auth) => {
    channelId = auth.channelId;
    token = auth.token; //JWT passed to backend for authentication
    authorization = "Bearer " + auth.token;
    console.log("channel id is " + channelId);
    getFirsts(authorization)
});


function getFirsts(authorization) {

    var firstsUrl = 'https://twitch.hv1.jaedolph.net/firsts'

    console.log("getting firsts");
    fetch(
        firstsUrl, {
        headers: {
            "Content-Type": "application/json",
            "Authorization": authorization,
        }}).then(function (response) {
        return response.json();
    }).then(function (firsts) {
        var firstsGrouped = groupFirsts(firsts)
        console.log(firstsGrouped);
        var firstsString = "";

        for (var count in firstsGrouped) {
            var row = firstsGrouped[count]
            firstsString += row["count"] + "x | " + row["users"].join(", ") + "<br>";
        }
        const dateObject = new Date();
        var date = dateObject.toUTCString();

        document.getElementById("heading").innerHTML = "Verified First Chatters"
        document.getElementById("firsts").innerHTML = firstsString;
        document.getElementById("lastupdated").innerHTML = "Last updated: " + date;

    }).catch(function (error) {
        console.error("something went wrong");
        console.error(error);
    });
}


function groupFirsts(firsts) {
    var counts = {};
    for (var user in firsts) {
        var count = firsts[user];
        if (count in counts) {
            counts[count].push(user);
        } else {
            counts[count] = [user];
        }
    }

    var countsArray = [];
    for (var count in counts) {
        var users = counts[count]
        countsArray[countsArray.length] = { "count": count, "users": users };
    }
    countsArray.sort().reverse();

    return countsArray;
}
