// The "Verified First Chatters" panel displayed to viewers

'use strict'
import { twitch, extensionUri } from './globals.js'

const firstsUrl = extensionUri + '/firsts'

let authorization

// Get "fists" counts after the user is authorized
twitch.onAuthorized(function (auth) {
  authorization = 'Bearer ' + auth.token
  getFirsts(authorization)
})

// read/parse the current config
twitch.configuration.onChanged(function () {
  if (twitch.configuration.broadcaster) {
    try {
      const config = JSON.parse(twitch.configuration.broadcaster.content)
      // set the title
      document.getElementById('title').textContent = config.title
    } catch (e) {
      console.log('invalid config')
    }
  }
})

/**
* Get first counts from the EBS and update the display
* @param {String} authorization - authorization header to send to the EBS
*/
function getFirsts (authorization) {
  fetch(
    firstsUrl, {
      headers: {
        'Content-Type': 'application/json',
        Authorization: authorization
      }
    }).then(function (response) {
    if (!response.ok) {
      return response.text().then(text => { throw new Error(text) })
    }
    return response.json()
  }).then(function (firsts) {
    const firstsGrouped = groupFirsts(firsts)
    let firstsString = ''

    for (const count in firstsGrouped) {
      const row = firstsGrouped[count]
      firstsString += row.count + 'x | ' + row.users.join(', ') + '<br>'
    }
    const dateObject = new Date()
    const date = dateObject.toUTCString()

    document.getElementById('firsts').innerHTML = firstsString
    document.getElementById('lastupdated').innerHTML = 'Last updated: ' + date
  }).catch(function (error) {
    console.error('failed to get firsts')
    console.error(error)
  })
}

/**
* Group first by count
* @summary Takes a "first" Object of counts by user and groups users by count
* @param {Object} firsts - first counts by user e.g. {"user1": 5, "user2": 2, "user3": 2}
* @return {Object} dictionary of first counts grouped by count
*                  e.g. {"5": ["user1"], "2" ["user2", "user3"]}
*/
function groupFirsts (firsts) {
  const counts = {}
  for (const user in firsts) {
    const count = firsts[user]
    if (count in counts) {
      counts[count].push(user)
    } else {
      counts[count] = [user]
    }
  }

  const countsArray = []
  for (const count in counts) {
    const users = counts[count]
    countsArray[countsArray.length] = { count, users }
  }
  countsArray.sort().reverse()

  return countsArray
}
