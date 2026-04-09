import React, { useState, useEffect, useRef, useCallback } from "react";
import { checkAuth, fetchRewards, createEventsub } from "../shared/api.js";
import { extensionUri, defaultTitle } from "../shared/constants.js";

const TWITCH_OAUTH_URL = "https://id.twitch.tv/oauth2/authorize";
const SCOPE = "channel:read:redemptions";

export default function Config() {
  // Values set inside Twitch SDK callbacks — stored in refs to avoid stale closures
  const authRef = useRef(null);
  const clientIdRef = useRef(null);
  const configRef = useRef({});

  const [isAuthed, setIsAuthed] = useState(null); // null = checking, true/false = result
  const [rewards, setRewards] = useState(null);
  const [configuredTitle, setConfiguredTitle] = useState(defaultTitle);
  const [configuredRewardId, setConfiguredRewardId] = useState(null);
  const [configuredTimeRange, setConfiguredTimeRange] = useState("all_time");
  const [rewardsLoading, setRewardsLoading] = useState(false);
  const [rewardsError, setRewardsError] = useState(null);
  const [authStatus, setAuthStatus] = useState(null); // null | "connecting" | "success" | "failed"
  const [submitStatus, setSubmitStatus] = useState(null); // null | "loading" | "success" | "error"
  const [submitError, setSubmitError] = useState(null);
  const authWindowRef = useRef(null);

  const loadRewards = useCallback(async () => {
    const auth = authRef.current;
    if (!auth) return;

    setRewardsLoading(true);
    setRewardsError(null);
    try {
      const rewardsList = await fetchRewards(auth);
      setRewards(rewardsList);
    } catch (e) {
      console.error("Failed to load rewards:", e);
      setRewardsError("Could not load channel points rewards.");
    } finally {
      setRewardsLoading(false);
    }
  }, []);

  // Register Twitch SDK callbacks once on mount
  useEffect(() => {
    const twitch = window.Twitch.ext;

    // Apply Twitch light/dark theme to the root element
    twitch.onContext((context) => {
      document.getElementById("root").dataset.theme = context.theme ?? "light";
    });

    // Parse existing broadcaster config
    twitch.configuration.onChanged(() => {
      if (twitch.configuration.broadcaster) {
        try {
          const config = JSON.parse(twitch.configuration.broadcaster.content);
          configRef.current = config;
          if (config.title) setConfiguredTitle(config.title);
          if (config.rewardId) setConfiguredRewardId(config.rewardId);
          if (config.timeRange) setConfiguredTimeRange(config.timeRange);
        } catch (e) {
          console.error("invalid config", e);
          configRef.current = {};
        }
      }
    });

    twitch.onAuthorized(async (authData) => {
      authRef.current = "Bearer " + authData.token;
      clientIdRef.current = authData.clientId;

      const authed = await checkAuth(authRef.current);
      setIsAuthed(authed);
      if (authed) {
        loadRewards();
      }
    });
  }, [loadRewards]);

  const openAuthWindow = () => {
    const clientId = clientIdRef.current;
    const redirectUri = extensionUri + "/auth";
    const authUrl =
      `${TWITCH_OAUTH_URL}?client_id=${clientId}` +
      `&response_type=code&scope=${SCOPE}&redirect_uri=${redirectUri}`;

    setAuthStatus("connecting");
    authWindowRef.current = window.open(
      authUrl,
      "_blank",
      "width=500,height=700",
    );

    const handleMessage = (msg) => {
      window.removeEventListener("message", handleMessage);
      if (authWindowRef.current) authWindowRef.current.close();

      if (msg.data === "AUTH_SUCCESSFUL") {
        setAuthStatus("success");
        setIsAuthed(true);
        loadRewards();
      } else {
        setAuthStatus("failed");
      }
    };

    window.addEventListener("message", handleMessage);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const form = e.target;
    const title = form.elements["panel_title"].value;
    const timeRange = form.elements["time_range"].value;
    const rewardId = form.elements["reward_select"].value;

    if (!rewardId) {
      setSubmitStatus("error");
      setSubmitError("No reward selected. Try refreshing the page.");
      return;
    }

    setSubmitStatus("loading");
    setSubmitError(null);

    // Save title and time range to Twitch broadcaster config storage
    const twitch = window.Twitch.ext;
    const updatedConfig = { ...configRef.current, title, timeRange };
    twitch.configuration.set("broadcaster", "1", JSON.stringify(updatedConfig));
    configRef.current = updatedConfig;

    // Create/update the EventSub subscription for the selected reward
    try {
      await createEventsub(authRef.current, rewardId);

      const finalConfig = { ...updatedConfig, rewardId };
      twitch.configuration.set("broadcaster", "1", JSON.stringify(finalConfig));
      configRef.current = finalConfig;
      setConfiguredRewardId(rewardId);
      setSubmitStatus("success");
    } catch (e) {
      console.error("Failed to create eventsub:", e);
      setSubmitError(e.message);
      setSubmitStatus("error");
    }
  };

  const showConfigForm = isAuthed && rewards && !rewardsLoading;

  return (
    <div id="config-page">
      <h3>
        You must be an affiliate or partner to use this extension as it relies
        on channel points
      </h3>

      <section>
        <h2>1. Configure &ldquo;First&rdquo; channel points reward</h2>
        <p>
          Create a new channel points reward called &ldquo;First&rdquo; (or
          something similar).
        </p>
        <p>
          Viewers can claim this reward to show that they were the first to get
          to your stream.
        </p>
        <p>
          Set the cost to 1 point. Tick &ldquo;Cooldown &amp; Limits&rdquo; and
          set &ldquo;Limit Redemptions Per Stream&rdquo; to 1 so that only one
          viewer can claim it per stream.
        </p>
        <p>
          If you already have a reward set up like this, you don&rsquo;t need to
          create a new one.
        </p>
        <p>
          <a
            href="https://link.twitch.tv/myChannelPoints"
            target="_blank"
            rel="noopener noreferrer"
          >
            Click here
          </a>{" "}
          to configure a new reward.
        </p>
      </section>

      <section>
        <h2>2. Connect your Twitch account</h2>
        <p>
          The extension needs access to your channel points rewards so it can
          listen for redemptions.
        </p>
        <button
          id="oauth"
          type="button"
          onClick={openAuthWindow}
          disabled={isAuthed === true || authStatus === "connecting"}
        >
          Connect to Twitch
        </button>
        {authStatus === "connecting" && (
          <p className="status">Auth in progress&hellip;</p>
        )}
        {authStatus === "success" && (
          <p className="status success">Connected to Twitch successfully.</p>
        )}
        {authStatus === "failed" && (
          <p className="status error">Auth failed, please try again.</p>
        )}
        {isAuthed === true && authStatus === null && (
          <p className="status success">Connected to Twitch successfully.</p>
        )}
        {isAuthed === false && authStatus === null && (
          <p className="status">
            Not connected. Click &ldquo;Connect to Twitch&rdquo; above.
          </p>
        )}
      </section>

      <section>
        <h2>3. Configure extension</h2>
        {isAuthed === null && (
          <p className="status">Checking connection&hellip;</p>
        )}
        {rewardsLoading && <p className="status">Loading rewards&hellip;</p>}
        {rewardsError && <p className="status error">{rewardsError}</p>}
        {isAuthed === false && authStatus === null && (
          <p>Please connect to Twitch before configuring.</p>
        )}

        {showConfigForm && (
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="panel_title">Leaderboard title:</label>
              <input
                type="text"
                id="panel_title"
                name="panel_title"
                defaultValue={configuredTitle}
                maxLength={26}
              />
            </div>

            <div className="form-group">
              <label htmlFor="reward_select">
                Select your &ldquo;First&rdquo; channel points reward:
              </label>
              <select
                name="reward_select"
                id="reward_select"
                defaultValue={configuredRewardId ?? ""}
              >
                {rewards.map((reward) => (
                  <option key={reward.id} value={reward.id}>
                    {reward.title}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="time_range">Default time range:</label>
              <select
                name="time_range"
                id="time_range"
                defaultValue={configuredTimeRange}
              >
                <option value="month">Month</option>
                <option value="year">Year</option>
                <option value="all_time">All Time</option>
              </select>
            </div>

            <input
              type="submit"
              value="Save"
              disabled={submitStatus === "loading"}
            />

            {submitStatus === "loading" && (
              <p className="status">
                Configuring channel point event listener&hellip;
              </p>
            )}
            {submitStatus === "success" && (
              <p className="status success">
                Configuration saved successfully.
              </p>
            )}
            {submitStatus === "error" && (
              <p className="status error">
                ERROR: Configuration failed &mdash; {submitError}
              </p>
            )}
          </form>
        )}
      </section>
    </div>
  );
}
