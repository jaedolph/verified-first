// The "Verified First Chatters" panel displayed to viewers

'use strict'
import { twitch, extensionUri } from './globals.js'

let authorization
let timeRange = null

const monthButton = document.getElementById('month')
const yearButton = document.getElementById('year')
const allTimeButton = document.getElementById('all_time')

monthButton.addEventListener('click', getFirstsMonth)
yearButton.addEventListener('click', getFirstsYear)
allTimeButton.addEventListener('click', getFirstsAllTime)

// Get "fists" counts after the user is authorized
twitch.onAuthorized(function (auth) {
  authorization = 'Bearer ' + auth.token
  switch (timeRange) {
    case 'month':
      getFirstsMonth()
      break
    case 'year':
      getFirstsYear()
      break
    default:
      getFirstsAllTime()
  }
})

// read/parse the current config
twitch.configuration.onChanged(function () {
  if (twitch.configuration.broadcaster) {
    try {
      const config = JSON.parse(twitch.configuration.broadcaster.content)
      // set the title
      document.getElementById('title').textContent = config.title
      // set the time range
      timeRange = config.timeRange
    } catch (e) {
      console.log('invalid config')
    }
  }
})

/**
* Get first counts from the EBS and update the display
* @param {String} authorization - authorization header to send to the EBS
* @param {Date} startTime - get all firsts from this date
*/
function getFirsts (authorization, startTime) {
  let firstsUrl = extensionUri + '/firsts'
  if (startTime) {
    firstsUrl = firstsUrl + '?' + new URLSearchParams({ start_time: startTime.toISOString() })
  }
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

/**
* Get first counts for current month
*/
function getFirstsMonth () {
  // set start time to the first day of the current month
  const currentTime = new Date()
  const startTime = new Date(Date.UTC(currentTime.getUTCFullYear(), currentTime.getUTCMonth(), 1))

  getFirsts(authorization, startTime)

  // highlight the "Month" button
  monthButton.innerHTML = '<strong>Month</strong>'
  yearButton.innerHTML = 'Year'
  allTimeButton.innerHTML = 'All Time'
}

/**
* Get first counts for current year
*/
function getFirstsYear () {
  // set start time to the first day of the current year
  const currentTime = new Date()
  const startTime = new Date(Date.UTC(currentTime.getUTCFullYear(), 0, 1))

  getFirsts(authorization, startTime)

  // highlight the "Year" button
  monthButton.innerHTML = 'Month'
  yearButton.innerHTML = '<strong>Year</strong>'
  allTimeButton.innerHTML = 'All Time'
}

/**
* Get first counts for all time
*/
function getFirstsAllTime () {
  getFirsts(authorization, null)

  // highlight the "All Time" button
  monthButton.innerHTML = 'Month'
  yearButton.innerHTML = 'Year'
  allTimeButton.innerHTML = '<strong>All Time</strong>'
}
