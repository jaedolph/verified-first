// Config form for the "Verified First" extension

'use strict'
import { twitch, extensionUri, defaultTitle } from './globals.js'

const twitchOuthUrl = 'https://id.twitch.tv/oauth2/authorize'
const scope = 'channel:read:redemptions'
const redirectUri = extensionUri + '/auth'

let configuredTitle = defaultTitle
let configuredTimeRange = null
let config = {}
let authorization, clientId, configuredRewardId, authWindow

// get list of rewards for a channel after the broadcaster is authorized
twitch.onAuthorized(async function (auth) {
  authorization = 'Bearer ' + auth.token
  clientId = auth.clientId

  // if the user has connected their twitch account to the extension, display the config form
  const isAuthorized = await checkAuth()
  if (isAuthorized) {
    displayConfigForm()
  } else {
    document.getElementById('config').innerHTML = '<p>Please connect to Twitch before configuring.</p>'
  }
})

// open the auth window when the user clicks the oauthButton
const authText = document.getElementById('auth')
const oauthButton = document.getElementById('oauth')
oauthButton.addEventListener('click', openAuthWindow)

// config form to configure which channel points reward will be counted as a "first"
const configForm = document.getElementById('config')
configForm.addEventListener('submit', submitConfig)

// read/parse the current config
twitch.configuration.onChanged(function () {
  console.log('getting current config')
  if (twitch.configuration.broadcaster) {
    try {
      console.log('current config: ' + twitch.configuration.broadcaster.content)
      config = JSON.parse(twitch.configuration.broadcaster.content)
      if (typeof config !== 'object') {
        throw new Error('could not parse config')
      }
      if (config.title) {
        configuredTitle = config.title
      }
      configuredRewardId = config.rewardId
      configuredTimeRange = config.timeRange
    } catch (error) {
      console.error('invalid config')
      console.error(error)
      config = {}
    }
  } else {
    console.log('config is empty')
  }
})

/**
* Get list of the broadcaster's rewards and display the config menu
*/
async function displayConfigForm () {
  getRewards().then((rewards) => {
    authText.innerHTML = '<p>Connected to Twitch successfully.</p>'
    oauthButton.disabled = true
    renderConfigForm(rewards, configuredTitle, configuredTimeRange, configuredRewardId)
  }).catch(function (error) {
    document.getElementById('config').innerHTML = '<p>ERROR: could not render configuration form.</p>'
    console.error(error)
  })
}

/**
* Checks if the broadcaster's twitch API auth credentials stored in the EBS are valid
* @return {Boolean} true if the broadcaster's auth credentials are valid
*/
async function checkAuth () {
  const authCheckUrl = extensionUri + '/auth/check'

  const response = await fetch(authCheckUrl, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      Authorization: authorization
    }
  }).catch(function (error) {
    document.getElementById('config').innerHTML = ''
    console.error('failed to retrieve rewards')
    console.error(error)
  })

  if (!response.ok) {
    const responseText = await response.text()
    const errorMsg = 'auth check failed: ' + response.status + ' ' + responseText
    console.error(errorMsg)
    return false
  }

  console.log('auth check passed')
  return true
}

/**
* Get the channel's rewards using the EBS=
*/
async function getRewards () {
  const rewardsUrl = extensionUri + '/rewards'

  // get list of a channel's rewards using the EBS
  const response = await fetch(rewardsUrl, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      Authorization: authorization
    }
  })

  if (!response.ok) {
    return await response.text().then(text => {
      const errorMessage = 'could not get rewards: ' + response.status + ' ' + text
      throw new Error(errorMessage)
    })
  }

  const rewards = await response.json()
  return rewards
}

/**
 * Renders the config form with pre-populated values
 * @param {Object} rewards - list of the broadcaster's rewards in json format
 * @param {String} title - currently configured title of the leaderboard
 * @param {String} timeRange - currently configured time range of the leaderboard
 * @param {String} rewardId - currently configured reward id used to track "Firsts"
 */
function renderConfigForm (rewards, title, timeRange, rewardId) {
  // render the base config form
  document.getElementById('config').innerHTML = `
    <label for="panel_title">Leaderboard Title:</label><br>
    <input type="text" id="panel_title" form="config" maxlength="26"><br><br>
    <label for="reward_select">Select your "First" channel points reward:</label><br>
    <select name="reward_select" id="reward_select" form="config"></select><br><br>
    <label for="time_range">Default time range:</label><br>
    <select name="time_range" id="time_range" form="config">
      <option id="month" value="month">Month</option>
      <option id="year" value="year">Year</option>
      <option id="all_time" value="all_time">All Time</option>
    </select><br><br>
    <input type="submit" value="Submit">`

  document.getElementById('panel_title').value = title

  // ensure the currently configured time range is selected
  switch (timeRange) {
    case 'month':
      document.getElementById('time_range').options.namedItem('month').selected = true
      break
    case 'year':
      document.getElementById('time_range').options.namedItem('year').selected = true
      break
    default:
      document.getElementById('time_range').options.namedItem('all_time').selected = true
  }

  // add rewards to reward_select dropdown
  for (const reward of rewards) {
    const newOption = document.createElement('option')
    newOption.value = reward.id
    newOption.text = reward.title
    // select the currently configured reward id if possible
    if (reward.id === rewardId) {
      newOption.selected = true
    }
    document.getElementById('reward_select').appendChild(newOption)
  }
}

/**
* Create an eventsub in the EBS for a specific reward
* @summary This tells the EBS to listen for channel point redemptions of a specific reward
* @param {String} rewardId - id of the reward to create an eventsub for
*/
async function createEventsub (rewardId) {
  const createEventsubUrl = extensionUri + '/eventsub/create?reward_id=' + rewardId

  document.getElementById('eventsub').innerHTML = 'Configuring channel point event listener...'

  // create eventsub in the EBS
  const response = await fetch(createEventsubUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: authorization
    }
  })

  if (!response.ok) {
    const responseText = await response.text()
    const errorMsg = 'failed to create eventsub: ' + response.status + ' ' + responseText
    document.getElementById('eventsub').innerHTML = 'ERROR: Configuration failed'
    throw new Error(errorMsg)
  }

  const eventsub = await response.json()

  console.log('created eventsub id=' + eventsub.eventsub_id)
  // update config with the reward id (so the config form shows the currently selected reward)
  config.rewardId = rewardId
  twitch.configuration.set('broadcaster', '1', JSON.stringify(config))
  configuredRewardId = rewardId
  document.getElementById('eventsub').innerHTML = 'Configuration successful'
}

/**
* Submit the config form
* @param {Object} event - the submit event
*/
async function submitConfig (event) {
  console.log('submitting config')
  event.preventDefault()

  // get title
  const title = document.getElementById('panel_title').value

  // get time range
  const timeRange = document.getElementById('time_range').value

  // update broadcaster config
  config.title = title
  config.timeRange = timeRange

  twitch.configuration.set('broadcaster', '1', JSON.stringify(config))

  // get selected reward
  const rewardId = document.getElementById('reward_select').value

  // ensure the reward id is defined
  if (rewardId !== undefined) {
    console.log('creating eventsub for reward_id=' + rewardId)
    // create evensub for the selected reward
    await createEventsub(rewardId)
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

  authText.innerHTML = 'Auth in progress...'

  // open the popup window
  authWindow = window.open(authUrl, '_blank', 'width=500,height=700')
  window.addEventListener('message', parseAuthWindowResponse)
}

/**
 * Parses the response from the auth popup
 * @param {Object} msg - message returned from the auth popup
 */
function parseAuthWindowResponse (msg) {
  // close the window and delete the listener once the user has finished the prompt
  console.log('closing window')
  window.removeEventListener('message', parseAuthWindowResponse)
  authWindow.close()
  // check if the auth was successful from what is returned by the /auth endpoint of the EBS
  if (msg.data === 'AUTH_SUCCESSFUL') {
    authText.innerHTML = 'Auth success.'
    console.log('auth success')
    displayConfigForm()
  } else {
    authText.innerHTML = 'Auth failed, please try again.'
    console.log('auth fail')
  }
  window.removeEventListener('message', parseAuthWindowResponse)
}
