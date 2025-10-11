import { describe, it, expect, vi, beforeEach } from "vitest";
import * as sessionApi from "../sessionApi";
import { api } from "../api";

vi.mock("../api");

const mockSession = {
  session_id: "session-123",
  status: "active",
  source: "prompt",
  created_at: "2025-01-01T00:00:00Z",
  updated_at: "2025-01-01T00:00:00Z",
  current_draft: {
    version: 1,
    ir: { intent: { summary: "Test" } },
    validation_status: "incomplete",
    ambiguities: ["hole_1"],
    smt_results: [],
    created_at: "2025-01-01T00:00:00Z",
    metadata: {},
  },
  ambiguities: ["hole_1"],
  revision_count: 1,
  metadata: {},
};

describe("sessionApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("createSession", () => {
    it("sends POST request to create session from prompt", async () => {
      vi.mocked(api.post).mockResolvedValue({ data: mockSession });

      const result = await sessionApi.createSession({
        prompt: "Test prompt",
      });

      expect(api.post).toHaveBeenCalledWith("/spec-sessions", {
        prompt: "Test prompt",
      });
      expect(result).toEqual(mockSession);
    });

    it("sends POST request to create session from IR", async () => {
      vi.mocked(api.post).mockResolvedValue({ data: mockSession });

      const ir = { intent: { summary: "Test" } };
      const result = await sessionApi.createSession({
        ir,
        source: "reverse_mode",
      });

      expect(api.post).toHaveBeenCalledWith("/spec-sessions", {
        ir,
        source: "reverse_mode",
      });
      expect(result).toEqual(mockSession);
    });

    it("includes metadata when provided", async () => {
      vi.mocked(api.post).mockResolvedValue({ data: mockSession });

      await sessionApi.createSession({
        prompt: "Test",
        metadata: { key: "value" },
      });

      expect(api.post).toHaveBeenCalledWith("/spec-sessions", {
        prompt: "Test",
        metadata: { key: "value" },
      });
    });
  });

  describe("listSessions", () => {
    it("fetches session list", async () => {
      const mockResponse = { sessions: [mockSession] };
      vi.mocked(api.get).mockResolvedValue({ data: mockResponse });

      const result = await sessionApi.listSessions();

      expect(api.get).toHaveBeenCalledWith("/spec-sessions");
      expect(result).toEqual(mockResponse);
    });
  });

  describe("getSession", () => {
    it("fetches specific session by ID", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: mockSession });

      const result = await sessionApi.getSession("session-123");

      expect(api.get).toHaveBeenCalledWith("/spec-sessions/session-123");
      expect(result).toEqual(mockSession);
    });
  });

  describe("resolveHole", () => {
    it("sends resolution request for hole", async () => {
      const updatedSession = { ...mockSession, ambiguities: [] };
      vi.mocked(api.post).mockResolvedValue({ data: updatedSession });

      const result = await sessionApi.resolveHole("session-123", "hole_1", {
        resolution_text: "int",
        resolution_type: "clarify_intent",
      });

      expect(api.post).toHaveBeenCalledWith(
        "/spec-sessions/session-123/holes/hole_1/resolve",
        {
          resolution_text: "int",
          resolution_type: "clarify_intent",
        }
      );
      expect(result).toEqual(updatedSession);
    });

    it("uses default resolution type if not provided", async () => {
      vi.mocked(api.post).mockResolvedValue({ data: mockSession });

      await sessionApi.resolveHole("session-123", "hole_1", {
        resolution_text: "int",
      });

      expect(api.post).toHaveBeenCalledWith(
        "/spec-sessions/session-123/holes/hole_1/resolve",
        {
          resolution_text: "int",
        }
      );
    });
  });

  describe("finalizeSession", () => {
    it("sends finalize request", async () => {
      const mockIRResponse = {
        ir: mockSession.current_draft!.ir,
        metadata: {},
      };
      vi.mocked(api.post).mockResolvedValue({ data: mockIRResponse });

      const result = await sessionApi.finalizeSession("session-123");

      expect(api.post).toHaveBeenCalledWith(
        "/spec-sessions/session-123/finalize"
      );
      expect(result).toEqual(mockIRResponse);
    });
  });

  describe("getAssists", () => {
    it("fetches assist suggestions for session", async () => {
      const mockAssists = {
        session_id: "session-123",
        assists: [
          {
            hole_id: "hole_1",
            suggestions: ["int", "float"],
            context: "Missing type",
          },
        ],
      };
      vi.mocked(api.get).mockResolvedValue({ data: mockAssists });

      const result = await sessionApi.getAssists("session-123");

      expect(api.get).toHaveBeenCalledWith(
        "/spec-sessions/session-123/assists"
      );
      expect(result).toEqual(mockAssists);
    });
  });

  describe("deleteSession", () => {
    it("sends delete request", async () => {
      vi.mocked(api.delete).mockResolvedValue({ data: {} });

      await sessionApi.deleteSession("session-123");

      expect(api.delete).toHaveBeenCalledWith("/spec-sessions/session-123");
    });
  });

  describe("error handling", () => {
    it("propagates errors from API", async () => {
      const error = new Error("Network error");
      vi.mocked(api.get).mockRejectedValue(error);

      await expect(sessionApi.getSession("session-123")).rejects.toThrow(
        "Network error"
      );
    });

    it("propagates 404 errors", async () => {
      const error = { response: { status: 404 } };
      vi.mocked(api.get).mockRejectedValue(error);

      await expect(sessionApi.getSession("nonexistent")).rejects.toEqual(error);
    });
  });
});
