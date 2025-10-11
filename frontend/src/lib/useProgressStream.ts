import { useEffect, useState } from "react";
import { api } from "./api";

export type ProgressStatus = "idle" | "connecting" | "open" | "closed" | "error";

export interface ProgressMessage {
  type: string;
  timestamp?: string;
  message?: string;
  scope?: string;
  stage?: string;
  status?: string;
  [key: string]: unknown;
}

type EventListener = (event: ProgressMessage) => void;
type StatusListener = (status: ProgressStatus) => void;

const eventListeners = new Set<EventListener>();
const statusListeners = new Set<StatusListener>();
const MAX_HISTORY = 200;
let cachedEvents: ProgressMessage[] = [];
let socket: WebSocket | null = null;
let currentStatus: ProgressStatus = "idle";
let activeChannel = "/ws/progress";

function normaliseEvent(data: unknown): ProgressMessage {
  if (typeof data === "string") {
    try {
      const parsed = JSON.parse(data);
      if (parsed && typeof parsed === "object") {
        return {
          timestamp: new Date().toISOString(),
          type: typeof (parsed as Record<string, unknown>).type === "string" ? (parsed as Record<string, string>).type : "event",
          ...parsed,
        } as ProgressMessage;
      }
    } catch (error) {
      return {
        type: "text",
        message: data,
        timestamp: new Date().toISOString(),
      };
    }
    return {
      type: "text",
      message: data,
      timestamp: new Date().toISOString(),
    };
  }
  if (data && typeof data === "object") {
    return {
      timestamp: new Date().toISOString(),
      type: "event",
      ...(data as Record<string, unknown>),
    };
  }
  return {
    type: "unknown",
    timestamp: new Date().toISOString(),
    value: data,
  } as ProgressMessage;
}

function resolveChannelUrl(channel: string): string {
  const base = api.defaults.baseURL ?? window.location.origin;
  const url = new URL(channel, base);
  url.protocol = url.protocol.replace("http", "ws");
  return url.toString();
}

function notifyEvent(event: ProgressMessage) {
  cachedEvents = [...cachedEvents, event].slice(-MAX_HISTORY);
  for (const listener of eventListeners) {
    listener(event);
  }
}

function notifyStatus(status: ProgressStatus) {
  currentStatus = status;
  for (const listener of statusListeners) {
    listener(status);
  }
}

function ensureSocket(channel: string) {
  if (socket && activeChannel !== channel) {
    socket.close();
    socket = null;
  }
  if (socket) {
    return;
  }
  activeChannel = channel;
  queueMicrotask(() => notifyStatus("connecting"));
  try {
    socket = new WebSocket(resolveChannelUrl(channel));
  } catch (error) {
    notifyStatus("error");
    return;
  }
  socket.addEventListener("open", () => notifyStatus("open"));
  socket.addEventListener("close", () => {
    notifyStatus("closed");
    socket = null;
  });
  socket.addEventListener("error", () => notifyStatus("error"));
  socket.addEventListener("message", (event) => {
    notifyEvent(normaliseEvent(event.data));
  });
}

export function useProgressStream(channel = "/ws/progress") {
  const [events, setEvents] = useState<ProgressMessage[]>(() => cachedEvents);
  const [status, setStatus] = useState<ProgressStatus>(currentStatus);

  useEffect(() => {
    ensureSocket(channel);
    const handleEvent: EventListener = (event) => {
      setEvents((prev) => {
        const next = [...prev, event];
        return next.length > MAX_HISTORY ? next.slice(next.length - MAX_HISTORY) : next;
      });
    };
    const handleStatus: StatusListener = (next) => {
      setStatus(next);
    };

    eventListeners.add(handleEvent);
    statusListeners.add(handleStatus);

    return () => {
      eventListeners.delete(handleEvent);
      statusListeners.delete(handleStatus);
      if (!eventListeners.size && socket) {
        socket.close();
        socket = null;
        notifyStatus("closed");
      }
    };
  }, [channel]);

  const clear = () => {
    setEvents([]);
    cachedEvents = [];
  };

  return { events, status, clear };
}
