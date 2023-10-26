// Global vars

export const twitch = window.Twitch.ext
export const defaultTitle = 'Verified First Chatters'
const params = new URLSearchParams(window.location.search)
const state = params.get('state')
export let extensionUri = 'https://verifiedfirst.jaedolph.net'
if (state === 'testing') {
  extensionUri = 'https://verifiedfirst-test.jaedolph.net'
}
