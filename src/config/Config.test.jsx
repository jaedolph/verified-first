import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import Config from "./Config";
import { checkAuth, fetchRewards, createEventsub } from "../shared/api.js";

vi.mock("../shared/api.js", () => ({
  checkAuth: vi.fn(),
  fetchRewards: vi.fn(),
  createEventsub: vi.fn(),
}));

const MOCK_REWARDS = [
  { id: "reward-1", title: "First" },
  { id: "reward-2", title: "Hydrate" },
];

describe("Config", () => {
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
    window.Twitch.ext.configuration.set.mockImplementation(() => {});
    window.Twitch.ext.configuration.broadcaster = null;
  });

  /** Simulate Twitch SDK firing onAuthorized */
  async function authorize({ authed = true } = {}) {
    checkAuth.mockResolvedValue(authed);
    if (authed) fetchRewards.mockResolvedValue(MOCK_REWARDS);
    await act(async () => {
      onAuthorizedCallback({ token: "test-token", clientId: "client-abc" });
    });
  }

  // -------------------------------------------------------------------------
  // Static content
  // -------------------------------------------------------------------------
  it("renders the channel points setup instructions", () => {
    render(<Config />);
    expect(
      screen.getByText(/Create a new channel points reward/),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Click here" })).toHaveAttribute(
      "href",
      "https://link.twitch.tv/myChannelPoints",
    );
  });

  it("renders the Connect to Twitch button", () => {
    render(<Config />);
    expect(
      screen.getByRole("button", { name: "Connect to Twitch" }),
    ).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Auth states
  // -------------------------------------------------------------------------
  it("shows config form when broadcaster is already authenticated", async () => {
    render(<Config />);
    await authorize({ authed: true });

    await waitFor(() => {
      expect(
        screen.getByLabelText(/Leaderboard title/i),
      ).toBeInTheDocument();
    });
  });

  it("disables the Connect button when already authenticated", async () => {
    render(<Config />);
    await authorize({ authed: true });

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: "Connect to Twitch" }),
      ).toBeDisabled();
    });
  });

  it("keeps the Connect button enabled when not authenticated", async () => {
    render(<Config />);
    await authorize({ authed: false });

    expect(
      screen.getByRole("button", { name: "Connect to Twitch" }),
    ).toBeEnabled();
  });

  it("does not show the config form when not authenticated", async () => {
    render(<Config />);
    await authorize({ authed: false });

    expect(screen.queryByLabelText(/Leaderboard title/i)).not.toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Config form
  // -------------------------------------------------------------------------
  it("populates the reward dropdown with rewards from the EBS", async () => {
    render(<Config />);
    await authorize({ authed: true });

    await waitFor(() => {
      expect(screen.getByRole("option", { name: "First" })).toBeInTheDocument();
      expect(
        screen.getByRole("option", { name: "Hydrate" }),
      ).toBeInTheDocument();
    });
  });

  it("pre-populates title from existing broadcaster config", async () => {
    window.Twitch.ext.configuration.broadcaster = {
      content: JSON.stringify({ title: "Saved Title", timeRange: "month" }),
    };
    render(<Config />);
    await act(async () => { onChangedCallback(); });
    await authorize({ authed: true });

    await waitFor(() => {
      expect(screen.getByDisplayValue("Saved Title")).toBeInTheDocument();
    });
  });

  it("submits config and calls createEventsub with selected reward", async () => {
    createEventsub.mockResolvedValue({ eventsub_id: "sub-123" });
    render(<Config />);
    await authorize({ authed: true });

    await waitFor(() => screen.getByLabelText(/Leaderboard title/i));

    await act(async () => {
      fireEvent.change(screen.getByLabelText(/Leaderboard title/i), {
        target: { value: "My Leaderboard" },
      });
      fireEvent.change(screen.getByRole("combobox", { name: /reward/i }), {
        target: { value: "reward-1" },
      });
      fireEvent.submit(screen.getByRole("button", { name: "Save" }).closest("form"));
    });

    await waitFor(() => {
      expect(createEventsub).toHaveBeenCalledWith(
        "Bearer test-token",
        "reward-1",
      );
      expect(screen.getByText(/Configuration saved successfully/)).toBeInTheDocument();
    });
  });

  it("saves title and time range to Twitch configuration on submit", async () => {
    createEventsub.mockResolvedValue({ eventsub_id: "sub-123" });
    render(<Config />);
    await authorize({ authed: true });

    await waitFor(() => screen.getByLabelText(/Leaderboard title/i));

    await act(async () => {
      fireEvent.change(screen.getByLabelText(/Leaderboard title/i), {
        target: { value: "Test Title" },
      });
      fireEvent.change(screen.getByRole("combobox", { name: /time range/i }), {
        target: { value: "month" },
      });
      fireEvent.submit(screen.getByRole("button", { name: "Save" }).closest("form"));
    });

    await waitFor(() => {
      expect(window.Twitch.ext.configuration.set).toHaveBeenCalledWith(
        "broadcaster",
        "1",
        expect.stringContaining('"title":"Test Title"'),
      );
      expect(window.Twitch.ext.configuration.set).toHaveBeenCalledWith(
        "broadcaster",
        "1",
        expect.stringContaining('"timeRange":"month"'),
      );
    });
  });

  it("shows error message when createEventsub fails", async () => {
    createEventsub.mockRejectedValue(new Error("eventsub failed"));
    render(<Config />);
    await authorize({ authed: true });

    await waitFor(() => screen.getByLabelText(/Leaderboard title/i));

    await act(async () => {
      fireEvent.submit(screen.getByRole("button", { name: "Save" }).closest("form"));
    });

    await waitFor(() => {
      expect(screen.getByText(/ERROR: Configuration failed/)).toBeInTheDocument();
    });
  });
});
