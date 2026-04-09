import "@testing-library/jest-dom";

// Mock the Twitch extension helper SDK
window.Twitch = {
  ext: {
    onAuthorized: vi.fn(),
    onContext: vi.fn(),
    configuration: {
      onChanged: vi.fn(),
      set: vi.fn(),
      broadcaster: null,
    },
  },
};
