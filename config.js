'use strict'
const twitch = window.Twitch.ext
const twitchOuthUrl = 'https://id.twitch.tv/oauth2/authorize'
const scope = 'channel:read:redemptions'
const extensionUri = 'https://verifiedfirst.jaedolph.net'
const redirectUri = extensionUri + '/auth'

let authorization, clientId

// get list of rewards for a channel after the broadcaster is authorized
twitch.onAuthorized(function (auth) {
  authorization = 'Bearer ' + auth.token
  clientId = auth.clientId

  getRewards()
})

// open the auth window when the user clicks the oauthButton
const oauthButton = document.getElementById('oauth')
oauthButton.addEventListener('click', openAuthWindow)

// config form to configure which channel points reward will be counted as a "first"
const configForm = document.getElementById('config')
configForm.addEventListener('submit', submitConfig)

/**
* Get the channel's rewards using the EBS and add them to a dropdown menu
*/
function getRewards () {
  const rewardsUrl = extensionUri + '/rewards'

  // get list of a channel's rewards using the EBS
  fetch(rewardsUrl, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      Authorization: authorization
    }
  }).then(function (response) {
    if (!response.ok) {
      return response.text().then(text => { throw new Error(text) })
    }
    return response.json()
  }).then(function (rewards) {
    // create config menu once rewards have been retrieved
    document.getElementById('config').innerHTML = `
      <label for="reward_select">Select your "First" channel points reward:</label><br>
      <select name="reward_select" id="reward_select" form="config"></select>
      <input type="submit" value="Submit">`

    // add rewards to reward_select dropdown
    for (const reward of rewards) {
      const newOption = document.createElement('option')
      newOption.value = reward.id
      newOption.text = reward.title
      document.getElementById('reward_select').appendChild(newOption)
    }
  }).catch(function (error) {
    document.getElementById('config').innerHTML = ''
    console.error('failed to retrieve rewards')
    console.error(error)
  })
}

/**
* Create an eventsub in the EBS for a specific reward
* @summary This tells the EBS to listen for channel point redemptions of a specific reward
* @param {String} rewardId - id of the reward to create an eventsub for
*/
function createEventsub (rewardId) {
  const createEventsubUrl = extensionUri + '/eventsub/create?reward_id=' + rewardId

  document.getElementById('eventsub').innerHTML = 'Configuring channel point event listener...'

  // create eventsub in the EBS
  fetch(createEventsubUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: authorization
    }
  }).then(function (response) {
    if (!response.ok) {
      return response.text().then(text => { throw new Error(text) })
    }
    return response.json().eventsub_id
  }).then(function (eventsubId) {
    console.log('created eventsub id=' + eventsubId)
    document.getElementById('eventsub').innerHTML = 'Configuration successful'
  }).catch(function (error) {
    console.error('failed to create eventsub')
    console.error(error)
    document.getElementById('eventsub').innerHTML = 'ERROR: Configuration failed'
  })
}

/**
* Submit the config form
* @param {Object} event - the submit event
*/
function submitConfig (event) {
  event.preventDefault()

  // get selected reward
  const rewardId = document.getElementById('reward_select').value

  console.log('submitting config')
  // ensure the reward id is defined
  if (rewardId !== undefined) {
    console.log('creating eventsub for reward_id=' + rewardId)
    // create evensub for the selected reward
    createEventsub(rewardId)
  } else {
    const errorMsg = 'ERROR: could not configure, try refreshing the page'
    document.getElementById('eventsub').innerHTML = errorMsg
    console.error(errorMsg)
  }
}

/**
* Opens a pop up window to prompt the user to authorize the extension.
*/
function openAuthWindow () {
  // twitch oauth url that redirects user to the EBS
  const authUrl = (twitchOuthUrl + '?client_id=' + clientId + '&response_type=code&scope=' + scope +
    '&redirect_uri=' + redirectUri)

  const authText = document.getElementById('auth')
  authText.innerHTML = 'Auth in progress...'

  // open the popup window
  const authWindow = window.open(authUrl, '_blank', 'width=500,height=700')
  window.addEventListener('message', (msg) => {
    // close the window once the user has finished the prompt
    console.log('closing window')
    authWindow.close()
    // check if the auth was successful from what is returned by the /auth endpoint of the EBS
    if (msg.data === 'AUTH_SUCCESSFUL') {
      authText.innerHTML = 'Auth success.'
      console.log('auth success')
      getRewards()
    } else {
      authText.innerHTML = 'Auth failed, please try again.'
      console.log('auth fail')
    }
  })
}
