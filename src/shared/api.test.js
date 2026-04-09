import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  fetchFirsts,
  checkAuth,
  fetchRewards,
  createEventsub,
} from "./api.js";

const BASE_URL = "https://verifiedfirst.jaedolph.net";
const AUTH = "Bearer test-token";

function mockFetch(status, body) {
  const isJson = typeof body !== "string";
  global.fetch = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(isJson ? JSON.stringify(body) : body),
  });
}

beforeEach(() => {
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// fetchFirsts
// ---------------------------------------------------------------------------
describe("fetchFirsts", () => {
  it("fetches from /firsts with no date params", async () => {
    mockFetch(200, { user1: 5 });
    const result = await fetchFirsts(AUTH, null, null);
    expect(fetch).toHaveBeenCalledWith(
      `${BASE_URL}/firsts`,
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: AUTH }) }),
    );
    expect(result).toEqual({ user1: 5 });
  });

  it("appends start_time param when provided", async () => {
    mockFetch(200, {});
    const start = new Date("2026-01-01T00:00:00Z");
    await fetchFirsts(AUTH, start, null);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("start_time=2026-01-01T00%3A00%3A00.000Z"),
      expect.anything(),
    );
  });

  it("appends both start_time and end_time when provided", async () => {
    mockFetch(200, {});
    const start = new Date("2026-01-01T00:00:00Z");
    const end = new Date("2026-02-01T00:00:00Z");
    await fetchFirsts(AUTH, start, end);
    const url = fetch.mock.calls[0][0];
    expect(url).toContain("start_time=");
    expect(url).toContain("end_time=");
  });

  it("returns null on 404", async () => {
    mockFetch(404, "not found");
    const result = await fetchFirsts(AUTH, null, null);
    expect(result).toBeNull();
  });

  it("throws on non-ok responses other than 404", async () => {
    mockFetch(500, "server error");
    await expect(fetchFirsts(AUTH, null, null)).rejects.toThrow();
  });
});

// ---------------------------------------------------------------------------
// checkAuth
// ---------------------------------------------------------------------------
describe("checkAuth", () => {
  it("returns true when the EBS responds with 200", async () => {
    mockFetch(200, { auth_status: "OK" });
    expect(await checkAuth(AUTH)).toBe(true);
  });

  it("returns false when the EBS responds with 403", async () => {
    mockFetch(403, "forbidden");
    expect(await checkAuth(AUTH)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// fetchRewards
// ---------------------------------------------------------------------------
describe("fetchRewards", () => {
  it("returns the list of rewards", async () => {
    const rewards = [{ id: "abc", title: "First" }];
    mockFetch(200, rewards);
    expect(await fetchRewards(AUTH)).toEqual(rewards);
  });

  it("throws on error response", async () => {
    mockFetch(403, "forbidden");
    await expect(fetchRewards(AUTH)).rejects.toThrow();
  });
});

// ---------------------------------------------------------------------------
// createEventsub
// ---------------------------------------------------------------------------
describe("createEventsub", () => {
  it("POSTs to /eventsub/create with the reward_id", async () => {
    mockFetch(200, { eventsub_id: "xyz" });
    const result = await createEventsub(AUTH, "reward-123");
    expect(fetch).toHaveBeenCalledWith(
      `${BASE_URL}/eventsub/create?reward_id=reward-123`,
      expect.objectContaining({ method: "POST" }),
    );
    expect(result).toEqual({ eventsub_id: "xyz" });
  });

  it("throws on error response", async () => {
    mockFetch(500, "error");
    await expect(createEventsub(AUTH, "reward-123")).rejects.toThrow();
  });
});
