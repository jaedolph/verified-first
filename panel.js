const twitch = window.Twitch.ext;

twitch.onAuthorized((auth) => {
    channelId = auth.channelId;
    console.log("channel id is " + channelId);
    getFirsts(channelId)
});


twitch.onContext((context) => {
    console.log(context.theme);
    if (context.theme == "dark") {
        document.getElementById("root").style.color = "rgb(239, 239, 241)";
        console.log("switched to dark theme");
    } else {
        document.getElementById("root").style.color = "rgb(14, 14, 16)";
        console.log("switched to light theme");
    }
});


function getFirsts(broadcasterId) {

    var firstsUrl = 'https://twitch.hv1.jaedolph.net/firsts?broadcaster_id=' + broadcasterId

    console.log("getting firsts");
    fetch(firstsUrl).then(function (response) {
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
