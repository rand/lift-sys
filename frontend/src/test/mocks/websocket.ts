export type WebSocketEventListener = (event: Event) => void;

const CONNECTING = 0;
const OPEN = 1;
const CLOSING = 2;
const CLOSED = 3;

export class MockWebSocket {
  static instances: MockWebSocket[] = [];
  static autoOpen = true;

  static reset() {
    for (const instance of MockWebSocket.instances) {
      instance.readyState = CLOSED;
    }
    MockWebSocket.instances = [];
    MockWebSocket.autoOpen = true;
  }

  readyState = CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;

  private listeners = new Map<string, Set<WebSocketEventListener>>();

  constructor(public readonly url: string) {
    MockWebSocket.instances.push(this);
    if (MockWebSocket.autoOpen) {
      queueMicrotask(() => this.simulateOpen());
    }
  }

  addEventListener(type: string, listener: WebSocketEventListener) {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set());
    }
    this.listeners.get(type)!.add(listener);
  }

  removeEventListener(type: string, listener: WebSocketEventListener) {
    this.listeners.get(type)?.delete(listener);
  }

  send(_data: unknown) {
    // noop for tests
  }

  close() {
    if (this.readyState === CLOSED) {
      return;
    }
    this.readyState = CLOSING;
    const event = new CloseEvent("close");
    this.onclose?.(event);
    this.dispatch("close", event);
    this.readyState = CLOSED;
  }

  emitMessage(data: unknown) {
    const payload = typeof data === "string" ? data : JSON.stringify(data);
    const event = new MessageEvent("message", { data: payload });
    this.onmessage?.(event);
    this.dispatch("message", event);
  }

  emitError(message: string) {
    const event = new Event("error");
    Object.defineProperty(event, "message", { value: message });
    this.onerror?.(event);
    this.dispatch("error", event);
  }

  simulateOpen() {
    if (this.readyState === OPEN) {
      return;
    }
    this.readyState = OPEN;
    const event = new Event("open");
    this.onopen?.(event);
    this.dispatch("open", event);
  }

  private dispatch(type: string, event: Event) {
    const listeners = this.listeners.get(type);
    if (!listeners) {
      return;
    }
    for (const listener of listeners) {
      listener(event);
    }
  }
}
