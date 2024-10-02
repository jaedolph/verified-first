// The "Verified First Chatters" panel displayed to viewers

'use strict'
import { twitch, extensionUri, defaultTitle } from './globals.js'

let authorization
let timeRange = null
let title = defaultTitle

const monthButton = document.getElementById('month')
const yearButton = document.getElementById('year')
const allTimeButton = document.getElementById('all_time')
const customRangeButton = document.getElementById('custom_range')
const datePicker = document.getElementById('date_picker')
const firstsText = document.getElementById('firsts')
const lastUpdatedText = document.getElementById('lastupdated')
const startDateInput = document.getElementById('start_date_input')
const endDateInput = document.getElementById('end_date_input')

monthButton.addEventListener('click', getFirstsMonth)
yearButton.addEventListener('click', getFirstsYear)
allTimeButton.addEventListener('click', getFirstsAllTime)
customRangeButton.addEventListener('click', showDateRangePicker)
startDateInput.addEventListener('change', getFirstsCustom)
endDateInput.addEventListener('change', getFirstsCustom)

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
      if (typeof config !== 'object') {
        throw new Error('could not parse config')
      }
      // set the title
      if (config.title) {
        title = config.title
      }
      // set the time range
      timeRange = config.timeRange
    } catch (error) {
      console.error('invalid config')
      console.error(error)
    }
    document.getElementById('title').textContent = title
  }
})

/**
* Get first counts from the EBS and update the display
* @param {String} authorization - authorization header to send to the EBS
* @param {Date} startTime - get all firsts from this date
* @param {Date} endTime - get all firsts to this date
*/
async function getFirsts (authorization, startTime, endTime) {
  let firstsUrl = extensionUri + '/firsts'
  if (startTime && endTime) {
    firstsUrl = firstsUrl + '?' + new URLSearchParams({ start_time: startTime.toISOString(), end_time: endTime.toISOString() })
  }
  if (startTime && !endTime) {
    firstsUrl = firstsUrl + '?' + new URLSearchParams({ start_time: startTime.toISOString() })
  }

  try {
    const response = await fetch(
      firstsUrl, {
        headers: {
          'Content-Type': 'application/json',
          Authorization: authorization
        }
      }
    )

    // 404 response means the extension is configured but no "firsts" are in the database yet
    if (response.status === 404) {
      firstsText.innerHTML = 'No one has been first yet ¯\\_(ツ)_/¯'
      return
    }

    // other errors could mean the extension is not configured yet
    if (!response.ok) {
      firstsText.innerHTML = 'Could not get leaderboard.<br>The extension may not be configured yet.'
      const errorMsg = await response.text()
      console.error(errorMsg)
      return
    }

    // group firsts and display leaderboard
    const firsts = await response.json()
    const firstsGrouped = groupFirsts(firsts)
    let firstsString = ''

    for (const count in firstsGrouped) {
      const row = firstsGrouped[count]
      firstsString += row.count + 'x | ' + row.users.join(', ') + '<br>'
    }
    const dateObject = new Date()
    const date = dateObject.toUTCString()

    firstsText.innerHTML = firstsString
    lastUpdatedText.innerHTML = 'Last updated: ' + date
  } catch (error) {
    console.error(error)
    firstsText.innerHTML = 'ERROR: Could not get leaderboard<br>(╯°□°）╯︵ ┻━┻'
  }
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
* Show the custom date range picker
*/
function showDateRangePicker () {
  // set default custom range to the previous month
  const currentTime = new Date()
  const lastMonthEnd = new Date(Date.UTC(currentTime.getUTCFullYear(), currentTime.getUTCMonth(), 1))
  const lastMonthStart = new Date(Date.UTC(currentTime.getUTCFullYear(), currentTime.getUTCMonth() - 1, 1))

  // set the default input values
  datePicker.className = ''
  firstsText.innerHTML = ''
  startDateInput.value = formatDate(lastMonthStart)
  endDateInput.value = formatDate(lastMonthEnd)

  // get firsts using the default input values
  getFirstsCustom()

  // highlight the "Custom" button
  monthButton.innerHTML = 'Month'
  yearButton.innerHTML = 'Year'
  allTimeButton.innerHTML = 'All Time'
  customRangeButton.innerHTML = '<strong>Custom</strong>'
}

/**
* Hide the custom date range picker
*/
function hideDateRangePicker () {
  datePicker.className = 'hidden'
}

/**
* Convert a date to a format compatible with an html date input
*/
function formatDate (date) {
  const dateString = date.toISOString().split('T')[0]
  return dateString
}

/**
* Get first counts for current month
*/
function getFirstsMonth () {
  // hide the date picker if required
  hideDateRangePicker()

  // set start time to the first day of the current month
  const currentTime = new Date()
  const startTime = new Date(Date.UTC(currentTime.getUTCFullYear(), currentTime.getUTCMonth(), 1))

  getFirsts(authorization, startTime, null)

  // highlight the "Month" button
  monthButton.innerHTML = '<strong>Month</strong>'
  yearButton.innerHTML = 'Year'
  allTimeButton.innerHTML = 'All Time'
  customRangeButton.innerHTML = 'Custom'
}

/**
* Get first counts for current year
*/
function getFirstsYear () {
  // hide the date picker if required
  hideDateRangePicker()

  // set start time to the first day of the current year
  const currentTime = new Date()
  const startTime = new Date(Date.UTC(currentTime.getUTCFullYear(), 0, 1))

  getFirsts(authorization, startTime, null)

  // highlight the "Year" button
  monthButton.innerHTML = 'Month'
  yearButton.innerHTML = '<strong>Year</strong>'
  allTimeButton.innerHTML = 'All Time'
  customRangeButton.innerHTML = 'Custom'
}

/**
* Get first counts for all time
*/
function getFirstsAllTime () {
  // hide the date picker if required
  hideDateRangePicker()

  getFirsts(authorization, null, null)

  // highlight the "All Time" button
  monthButton.innerHTML = 'Month'
  yearButton.innerHTML = 'Year'
  allTimeButton.innerHTML = '<strong>All Time</strong>'
  customRangeButton.innerHTML = 'Custom'
}

/**
* Get first counts for a custom range
*/
function getFirstsCustom () {
  const startDateInput = document.getElementById('start_date_input')
  const endDateInput = document.getElementById('end_date_input')

  getFirsts(authorization, startDateInput.valueAsDate, endDateInput.valueAsDate)
}
