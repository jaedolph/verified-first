import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import Panel from "./Panel";
import { fetchFirsts, fetchAvatars } from "../shared/api.js";

vi.mock("../shared/api.js", () => ({
  fetchFirsts: vi.fn(),
  fetchAvatars: vi.fn(),
}));

describe("Panel", () => {
  let onAuthorizedCallback;
  let onChangedCallback;

  beforeEach(() => {
    vi.clearAllMocks();
    fetchAvatars.mockResolvedValue({});
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
  // Cards leaderboard style
  // -------------------------------------------------------------------------
  it("renders card rows instead of a classic list when cards style is configured", async () => {
    fetchFirsts.mockResolvedValue({ saundo__: 69, chetnitro: 37 });
    render(<Panel />);
    await applyConfig({ leaderboardStyle: "cards" });
    await authorize();

    await waitFor(() => {
      expect(document.querySelector("blockquote")).not.toBeInTheDocument();
      expect(document.querySelectorAll(".firsts-row")).toHaveLength(2);
    });
  });

  it("shows the firsts count (not rank) in the count badge", async () => {
    fetchFirsts.mockResolvedValue({ saundo__: 69, chetnitro: 37 });
    render(<Panel />);
    await applyConfig({ leaderboardStyle: "cards" });
    await authorize();

    await waitFor(() => {
      const counts = Array.from(
        document.querySelectorAll(".firsts-count"),
      ).map((el) => el.textContent.trim());
      expect(counts).toEqual(["69", "37"]);
    });
  });

  it("renders one avatar per tied user, plus an overflow badge past the max shown", async () => {
    fetchFirsts.mockResolvedValue({
      user1: 1,
      user2: 1,
      user3: 1,
      user4: 1,
      user5: 1,
    });
    render(<Panel />);
    await applyConfig({ leaderboardStyle: "cards" });
    await authorize();

    await waitFor(() => {
      expect(
        document.querySelectorAll(".firsts-avatar:not(.firsts-avatar--overflow)"),
      ).toHaveLength(3);
      expect(screen.getByText("+2")).toBeInTheDocument();
      expect(
        screen.getByText("user1, user2, user3, user4, user5"),
      ).toBeInTheDocument();
    });
  });

  it("does not show the classic 'Nx' count prefix in card row text", async () => {
    fetchFirsts.mockResolvedValue({ saundo__: 69 });
    render(<Panel />);
    await applyConfig({ leaderboardStyle: "cards" });
    await authorize();

    await waitFor(() => {
      expect(screen.getByText("saundo__")).toBeInTheDocument();
      expect(screen.queryByText(/69x/)).not.toBeInTheDocument();
    });
  });

  it("shows profile pictures where available and initials for everyone else", async () => {
    fetchFirsts.mockResolvedValue({ saundo__: 69, chetnitro: 37 });
    fetchAvatars.mockResolvedValue({ saundo__: "https://example.com/saundo.png" });
    render(<Panel />);
    await applyConfig({ leaderboardStyle: "cards" });
    await authorize("abc");

    await waitFor(() => {
      const images = document.querySelectorAll("img.firsts-avatar");
      expect(images).toHaveLength(1);
      expect(images[0]).toHaveAttribute("src", "https://example.com/saundo.png");
      expect(screen.getByText("CH")).toBeInTheDocument();
    });
    expect(fetchAvatars).toHaveBeenCalledWith("Bearer abc");
  });

  it("falls back to initials if a profile picture fails to load", async () => {
    fetchFirsts.mockResolvedValue({ saundo__: 69 });
    fetchAvatars.mockResolvedValue({ saundo__: "https://example.com/broken.png" });
    render(<Panel />);
    await applyConfig({ leaderboardStyle: "cards" });
    await authorize();

    const image = await waitFor(() => {
      const img = document.querySelector("img.firsts-avatar");
      expect(img).toBeInTheDocument();
      return img;
    });
    fireEvent.error(image);

    expect(document.querySelector("img.firsts-avatar")).not.toBeInTheDocument();
    expect(screen.getByText("SA")).toBeInTheDocument();
  });

  it("tries a new profile picture url after an earlier one failed to load", async () => {
    fetchFirsts.mockResolvedValue({ saundo__: 69 });
    fetchAvatars.mockResolvedValue({ saundo__: "https://example.com/broken.png" });
    render(<Panel />);
    await applyConfig({ leaderboardStyle: "cards" });
    await authorize();

    const image = await waitFor(() => {
      const img = document.querySelector("img.firsts-avatar");
      expect(img).toBeInTheDocument();
      return img;
    });
    fireEvent.error(image);
    expect(screen.getByText("SA")).toBeInTheDocument();

    // each fetch returns a new object, which is what triggers the profile picture refetch
    fetchFirsts.mockResolvedValue({ saundo__: 69 });
    fetchAvatars.mockResolvedValue({ saundo__: "https://example.com/fixed.png" });
    fireEvent.click(screen.getByRole("button", { name: "Month" }));

    await waitFor(() => {
      expect(document.querySelector("img.firsts-avatar")).toHaveAttribute(
        "src",
        "https://example.com/fixed.png",
      );
    });
  });

  it("refetches profile pictures when the leaderboard reloads", async () => {
    fetchFirsts.mockResolvedValue({ saundo__: 69 });
    fetchAvatars.mockResolvedValue({ saundo__: "https://example.com/saundo.png" });
    render(<Panel />);
    await applyConfig({ leaderboardStyle: "cards" });
    await authorize();

    await waitFor(() => {
      expect(document.querySelectorAll("img.firsts-avatar")).toHaveLength(1);
    });
    expect(fetchAvatars).toHaveBeenCalledTimes(1);

    // a new user gets their first while the panel is open
    fetchFirsts.mockResolvedValue({ saundo__: 69, newuser: 1 });
    fetchAvatars.mockResolvedValue({
      saundo__: "https://example.com/saundo.png",
      newuser: "https://example.com/newuser.png",
    });
    fireEvent.click(screen.getByRole("button", { name: "Month" }));

    await waitFor(() => {
      expect(document.querySelectorAll("img.firsts-avatar")).toHaveLength(2);
    });
    expect(fetchAvatars).toHaveBeenCalledTimes(2);
  });

  it("does not fetch profile pictures if the channel has no firsts", async () => {
    fetchFirsts.mockResolvedValue(null);
    render(<Panel />);
    await applyConfig({ leaderboardStyle: "cards" });
    await authorize();

    await waitFor(() => {
      expect(fetchFirsts).toHaveBeenCalled();
    });
    expect(fetchAvatars).not.toHaveBeenCalled();
  });

  it("still shows the leaderboard if profile pictures can't be fetched", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    fetchFirsts.mockResolvedValue({ saundo__: 69 });
    fetchAvatars.mockRejectedValue(new Error("server error"));
    render(<Panel />);
    await applyConfig({ leaderboardStyle: "cards" });
    await authorize();

    await waitFor(() => {
      expect(screen.getByText("saundo__")).toBeInTheDocument();
      expect(screen.getByText("SA")).toBeInTheDocument();
    });
    expect(fetchAvatars).toHaveBeenCalledTimes(1);
  });

  it("does not fetch profile pictures for the classic style", async () => {
    fetchFirsts.mockResolvedValue({ saundo__: 69 });
    render(<Panel />);
    await authorize();

    await waitFor(() => {
      expect(screen.getByText(/69x \| saundo__/)).toBeInTheDocument();
    });
    expect(fetchAvatars).not.toHaveBeenCalled();
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
