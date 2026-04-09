import React, { useState, useEffect, useRef, useCallback } from "react";
import { fetchFirsts } from "../shared/api.js";
import { defaultTitle } from "../shared/constants.js";

const TIME_RANGES = ["month", "year", "all_time", "custom"];
const RANGE_LABELS = {
  month: "Month",
  year: "Year",
  all_time: "All Time",
  custom: "Custom",
};

/**
 * Get the start/end Date objects for a given named time range.
 * Returns null for all_time; custom ranges must be passed in via customStart/customEnd.
 */
function getDateRange(range) {
  const now = new Date();
  if (range === "month") {
    return {
      startTime: new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1)),
      endTime: null,
    };
  }
  if (range === "year") {
    return {
      startTime: new Date(Date.UTC(now.getUTCFullYear(), 0, 1)),
      endTime: null,
    };
  }
  return { startTime: null, endTime: null };
}

/** Default custom range: previous calendar month in UTC */
function getDefaultCustomRange() {
  const now = new Date();
  const end = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
  const start = new Date(
    Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - 1, 1),
  );
  return {
    start: start.toISOString().split("T")[0],
    end: end.toISOString().split("T")[0],
  };
}

/**
 * Group { username: count } into sorted descending array of { count, users }.
 */
function groupFirsts(firsts) {
  const counts = {};
  for (const [user, count] of Object.entries(firsts)) {
    if (count in counts) {
      counts[count].push(user);
    } else {
      counts[count] = [user];
    }
  }
  return Object.entries(counts)
    .sort(([a], [b]) => Number(b) - Number(a))
    .map(([count, users]) => ({ count: Number(count), users }));
}

export default function Panel() {
  // Use refs for values set inside Twitch SDK callbacks to avoid stale closure issues
  const authRef = useRef(null);
  const configuredRangeRef = useRef("all_time");

  const [title, setTitle] = useState(defaultTitle);
  const [activeRange, setActiveRange] = useState(null);
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");
  const [firsts, setFirsts] = useState(undefined); // undefined = not yet loaded
  const [lastUpdated, setLastUpdated] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  /** Fetch leaderboard data for the given range/dates and update state */
  const loadFirsts = useCallback(async (range, start, end) => {
    const auth = authRef.current;
    if (!auth) return;

    setLoading(true);
    setError(null);

    let startTime = null;
    let endTime = null;

    if (range === "custom") {
      if (start) startTime = new Date(start + "T00:00:00Z");
      if (end) endTime = new Date(end + "T00:00:00Z");
    } else {
      ({ startTime, endTime } = getDateRange(range));
    }

    try {
      const result = await fetchFirsts(auth, startTime, endTime);
      setFirsts(result); // null = 404 (no firsts yet), object = data
      setLastUpdated(new Date());
    } catch (e) {
      console.error(e);
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Register Twitch SDK callbacks once on mount
  useEffect(() => {
    const twitch = window.Twitch.ext;

    // Apply Twitch light/dark theme to the root element
    twitch.onContext((context) => {
      document.getElementById("root").dataset.theme = context.theme ?? "light";
    });

    // Parse broadcaster config for title and default time range
    twitch.configuration.onChanged(() => {
      if (twitch.configuration.broadcaster) {
        try {
          const config = JSON.parse(twitch.configuration.broadcaster.content);
          if (config.title) setTitle(config.title);
          if (config.timeRange) configuredRangeRef.current = config.timeRange;
        } catch (e) {
          console.error("invalid config", e);
        }
      }
    });

    // Fetch leaderboard once auth token is available
    twitch.onAuthorized((authData) => {
      authRef.current = "Bearer " + authData.token;
      const range = configuredRangeRef.current;
      setActiveRange(range);
      loadFirsts(range);
    });
  }, [loadFirsts]);

  const handleRangeClick = (range) => {
    if (range === "custom") {
      const defaults = getDefaultCustomRange();
      setCustomStart(defaults.start);
      setCustomEnd(defaults.end);
      setActiveRange("custom");
      loadFirsts("custom", defaults.start, defaults.end);
    } else {
      setActiveRange(range);
      loadFirsts(range);
    }
  };

  const handleCustomStartChange = (e) => {
    const val = e.target.value;
    setCustomStart(val);
    if (val && customEnd) loadFirsts("custom", val, customEnd);
  };

  const handleCustomEndChange = (e) => {
    const val = e.target.value;
    setCustomEnd(val);
    if (customStart && val) loadFirsts("custom", customStart, val);
  };

  const renderLeaderboard = () => {
    if (loading) return <p>Loading...</p>;
    if (error) {
      return (
        <p>
          Could not get leaderboard.
          <br />
          The extension may not be configured yet.
        </p>
      );
    }
    if (firsts === null || (firsts && Object.keys(firsts).length === 0)) {
      return <p>{"No one has been first yet ¯\\_(ツ)_/¯"}</p>;
    }
    if (firsts === undefined) return null;

    return groupFirsts(firsts).map(({ count, users }, i) => (
      <p key={i}>
        {count}x | {users.join(", ")}
      </p>
    ));
  };

  return (
    <div id="panel">
      <h3 id="title">{title}</h3>
      <div className="timerange">
        {TIME_RANGES.map((range) => (
          <button
            key={range}
            onClick={() => handleRangeClick(range)}
            className={activeRange === range ? "active" : ""}
          >
            {RANGE_LABELS[range]}
          </button>
        ))}
      </div>
      {activeRange === "custom" && (
        <div id="date_picker">
          <input
            type="date"
            value={customStart}
            onChange={handleCustomStartChange}
          />{" "}
          <input
            type="date"
            value={customEnd}
            onChange={handleCustomEndChange}
          />
        </div>
      )}
      <div className="firsts">
        <blockquote>
          <div id="firsts">{renderLeaderboard()}</div>
        </blockquote>
      </div>
      <div className="footer">
        <p id="lastupdated">
          {lastUpdated && `Last updated: ${lastUpdated.toUTCString()}`}
        </p>
      </div>
    </div>
  );
}
