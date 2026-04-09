export const defaultTitle = "Verified First Chatters";

const params = new URLSearchParams(window.location.search);
const state = params.get("state");
export const extensionUri =
  state === "testing"
    ? "https://verifiedfirst-test.jaedolph.net"
    : "https://verifiedfirst.jaedolph.net";
