import "@testing-library/jest-dom";
import { afterEach, beforeEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";
import { MockWebSocket } from "./mocks/websocket";

class StubResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

class StubIntersectionObserver {
  constructor(_callback: IntersectionObserverCallback) {}
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords() {
    return [];
  }
}

if (!("ResizeObserver" in globalThis)) {
  vi.stubGlobal("ResizeObserver", StubResizeObserver as unknown as typeof ResizeObserver);
}

if (!("IntersectionObserver" in globalThis)) {
  vi.stubGlobal("IntersectionObserver", StubIntersectionObserver as unknown as typeof IntersectionObserver);
}

vi.stubGlobal("WebSocket", MockWebSocket as unknown as typeof WebSocket);

beforeEach(() => {
  MockWebSocket.reset();
});

afterEach(() => {
  cleanup();
  MockWebSocket.reset();
});
