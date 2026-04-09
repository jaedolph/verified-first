import { extensionUri } from "./constants.js";

/**
 * Fetch "firsts" counts from the EBS.
 * Returns null if no data exists yet (404), throws on other errors.
 * @param {string} authorization - "Bearer <token>"
 * @param {Date|null} startTime
 * @param {Date|null} endTime
 * @returns {Object|null} - { username: count } or null
 */
export async function fetchFirsts(authorization, startTime, endTime) {
  let url = extensionUri + "/firsts";
  const params = {};
  if (startTime) params.start_time = startTime.toISOString();
  if (endTime) params.end_time = endTime.toISOString();

  if (Object.keys(params).length > 0) {
    url += "?" + new URLSearchParams(params);
  }

  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      Authorization: authorization,
    },
  });

  if (response.status === 404) return null;
  if (!response.ok) throw new Error(await response.text());
  return await response.json();
}

/**
 * Check if the broadcaster has connected their Twitch account to the EBS.
 * @param {string} authorization - "Bearer <token>"
 * @returns {boolean}
 */
export async function checkAuth(authorization) {
  const response = await fetch(extensionUri + "/auth/check", {
    headers: {
      "Content-Type": "application/json",
      Authorization: authorization,
    },
  });
  return response.ok;
}

/**
 * Fetch the broadcaster's channel points rewards from the EBS.
 * @param {string} authorization - "Bearer <token>"
 * @returns {Array} - list of reward objects
 */
export async function fetchRewards(authorization) {
  const response = await fetch(extensionUri + "/rewards", {
    headers: {
      "Content-Type": "application/json",
      Authorization: authorization,
    },
  });
  if (!response.ok) throw new Error(await response.text());
  return await response.json();
}

/**
 * Create an EventSub subscription in the EBS for the given reward.
 * @param {string} authorization - "Bearer <token>"
 * @param {string} rewardId
 * @returns {Object} - { eventsub_id: "..." }
 */
export async function createEventsub(authorization, rewardId) {
  const response = await fetch(
    extensionUri + "/eventsub/create?reward_id=" + rewardId,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: authorization,
      },
    },
  );
  if (!response.ok) throw new Error(await response.text());
  return await response.json();
}
