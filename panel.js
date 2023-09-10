const twitch = window.Twitch.ext
const extensionUri = 'https://twitch.hv1.jaedolph.net'
const firstsUrl = extensionUri + '/firsts'

let authorization

twitch.onAuthorized((auth) => {
  authorization = 'Bearer ' + auth.token
  getFirsts(authorization)
})

function getFirsts (authorization) {
  console.log('getting firsts')
  fetch(
    firstsUrl, {
      headers: {
        'Content-Type': 'application/json',
        Authorization: authorization
      }
    }).then(function (response) {
    return response.json()
  }).then(function (firsts) {
    const firstsGrouped = groupFirsts(firsts)
    console.log(firstsGrouped)
    let firstsString = ''

    for (const count in firstsGrouped) {
      const row = firstsGrouped[count]
      firstsString += row.count + 'x | ' + row.users.join(', ') + '<br>'
    }
    const dateObject = new Date()
    const date = dateObject.toUTCString()

    document.getElementById('heading').innerHTML = 'Verified First Chatters'
    document.getElementById('firsts').innerHTML = firstsString
    document.getElementById('lastupdated').innerHTML = 'Last updated: ' + date
  }).catch(function (error) {
    console.error('something went wrong')
    console.error(error)
  })
}

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
