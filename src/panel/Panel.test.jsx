import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import Panel from "./Panel";
import { fetchFirsts } from "../shared/api.js";

vi.mock("../shared/api.js", () => ({
  fetchFirsts: vi.fn(),
}));

describe("Panel", () => {
  let onAuthorizedCallback;
  let onChangedCallback;

  beforeEach(() => {
    vi.clearAllMocks();
    onAuthorizedCallback = null;
    onChangedCallback = null;

    window.Twitch.ext.onAuthorized.mockImplementation((cb) => {
      onAuthorizedCallback = cb;
    });
    window.Twitch.ext.configuration.onChanged.mockImplementation((cb) => {
      onChangedCallback = cb;
    });
    window.Twitch.ext.onContext.mockImplementation(() => {});
    window.Twitch.ext.configuration.broadcaster = null;
  });

  /** Simulate the Twitch SDK firing onAuthorized */
  async function authorize(token = "test-token") {
    await act(async () => {
      onAuthorizedCallback({ token });
    });
  }

  /** Simulate the Twitch SDK firing configuration.onChanged */
  async function applyConfig(config) {
    window.Twitch.ext.configuration.broadcaster = {
      content: JSON.stringify(config),
    };
    await act(async () => {
      onChangedCallback();
    });
  }

  // -------------------------------------------------------------------------
  // Rendering
  // -------------------------------------------------------------------------
  it("renders the default title before auth", () => {
    render(<Panel />);
    expect(screen.getByText("Verified First Chatters")).toBeInTheDocument();
  });

  it("renders all four time-range buttons", () => {
    render(<Panel />);
    ["Month", "Year", "All Time", "Custom"].forEach((label) => {
      expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
    });
  });

  it("applies title from broadcaster config", async () => {
    fetchFirsts.mockResolvedValue({});
    render(<Panel />);
    await applyConfig({ title: "My Stream Firsts", timeRange: "all_time" });
    expect(screen.getByText("My Stream Firsts")).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Leaderboard states
  // -------------------------------------------------------------------------
  it("shows leaderboard rows after authorization", async () => {
    fetchFirsts.mockResolvedValue({ saundo__: 69, chetnitro: 37, simkintv: 10 });
    render(<Panel />);
    await authorize();

    await waitFor(() => {
      expect(screen.getByText(/69x \| saundo__/)).toBeInTheDocument();
      expect(screen.getByText(/37x \| chetnitro/)).toBeInTheDocument();
      expect(screen.getByText(/10x \| simkintv/)).toBeInTheDocument();
    });
  });

  it("groups users that share the same count", async () => {
    fetchFirsts.mockResolvedValue({ alice: 3, bob: 3, carol: 1 });
    render(<Panel />);
    await authorize();

    await waitFor(() => {
      expect(screen.getByText(/3x \| alice, bob/)).toBeInTheDocument();
      expect(screen.getByText(/1x \| carol/)).toBeInTheDocument();
    });
  });

  it("shows empty message when API returns null (404)", async () => {
    fetchFirsts.mockResolvedValue(null);
    render(<Panel />);
    await authorize();

    await waitFor(() => {
      expect(screen.getByText(/No one has been first yet/)).toBeInTheDocument();
    });
  });

  it("shows empty message when API returns an empty object", async () => {
    fetchFirsts.mockResolvedValue({});
    render(<Panel />);
    await authorize();

    await waitFor(() => {
      expect(screen.getByText(/No one has been first yet/)).toBeInTheDocument();
    });
  });

  it("shows error message when the API call fails", async () => {
    fetchFirsts.mockRejectedValue(new Error("network error"));
    render(<Panel />);
    await authorize();

    await waitFor(() => {
      expect(screen.getByText(/Could not get leaderboard/)).toBeInTheDocument();
    });
  });

  it("shows last-updated timestamp after a successful fetch", async () => {
    fetchFirsts.mockResolvedValue({ user1: 5 });
    render(<Panel />);
    await authorize();

    await waitFor(() => {
      expect(screen.getByText(/Last updated:/)).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Time-range selection
  // -------------------------------------------------------------------------
  it("uses the configured default time range on first load", async () => {
    fetchFirsts.mockResolvedValue({});
    render(<Panel />);
    await applyConfig({ timeRange: "month" });
    await authorize();

    await waitFor(() => {
      const [, startTime] = fetchFirsts.mock.calls[0]; // [auth, startTime, endTime]
      // start of current month in UTC
      const now = new Date();
      expect(startTime).toEqual(
        new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1)),
      );
    });
  });

  it("fetches with no date params when All Time is clicked", async () => {
    fetchFirsts.mockResolvedValue({});
    render(<Panel />);
    await authorize();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "All Time" }));
    });

    await waitFor(() => {
      const lastCall = fetchFirsts.mock.calls.at(-1);
      expect(lastCall[1]).toBeNull(); // startTime
      expect(lastCall[2]).toBeNull(); // endTime
    });
  });

  it("fetches from start of current month when Month is clicked", async () => {
    fetchFirsts.mockResolvedValue({});
    render(<Panel />);
    await authorize();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Month" }));
    });

    await waitFor(() => {
      const [, startTime] = fetchFirsts.mock.calls.at(-1);
      const now = new Date();
      expect(startTime).toEqual(
        new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1)),
      );
    });
  });

  it("fetches from start of current year when Year is clicked", async () => {
    fetchFirsts.mockResolvedValue({});
    render(<Panel />);
    await authorize();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Year" }));
    });

    await waitFor(() => {
      const [, startTime] = fetchFirsts.mock.calls.at(-1);
      const now = new Date();
      expect(startTime).toEqual(new Date(Date.UTC(now.getUTCFullYear(), 0, 1)));
    });
  });

  // -------------------------------------------------------------------------
  // Custom date range
  // -------------------------------------------------------------------------
  it("shows date picker when Custom is clicked", async () => {
    fetchFirsts.mockResolvedValue({});
    render(<Panel />);
    await authorize();

    expect(document.getElementById("date_picker")).not.toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Custom" }));
    });

    expect(document.getElementById("date_picker")).toBeInTheDocument();
  });

  it("hides date picker when a named range is clicked after Custom", async () => {
    fetchFirsts.mockResolvedValue({});
    render(<Panel />);
    await authorize();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Custom" }));
    });
    expect(document.getElementById("date_picker")).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Month" }));
    });
    expect(document.getElementById("date_picker")).not.toBeInTheDocument();
  });

  it("defaults the custom range to the previous calendar month", async () => {
    fetchFirsts.mockResolvedValue({});
    render(<Panel />);
    await authorize();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Custom" }));
    });

    const now = new Date();
    const expectedEnd = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
    const expectedStart = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - 1, 1));

    const [, startTime, endTime] = fetchFirsts.mock.calls.at(-1);
    expect(startTime).toEqual(expectedStart);
    expect(endTime).toEqual(expectedEnd);
  });
});
