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
