/**
 * Native WebSocket client with automatic reconnection (exponential backoff).
 * Replaces the previous socket.io-based implementation.
 */

export type ConnectionState = 'connecting' | 'connected' | 'disconnected'

type MessageHandler = (channel: string, data: unknown) => void

const WS_URL =
  (import.meta.env.VITE_WS_URL as string | undefined) ??
  (import.meta.env.VITE_API_BASE_URL
    ? (import.meta.env.VITE_API_BASE_URL as string).replace(/^http/, 'ws') + '/api/ws/stream'
    : 'ws://localhost:8001/api/ws/stream')

const INITIAL_RECONNECT_MS = 1000
const MAX_RECONNECT_MS = 30000
const RECONNECT_MULTIPLIER = 2

let ws: WebSocket | null = null
let state: ConnectionState = 'disconnected'
let reconnectDelay = INITIAL_RECONNECT_MS
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let refCount = 0
let intentionalClose = false

const messageHandlers = new Set<MessageHandler>()
const stateListeners = new Set<() => void>()
const subscriptions = new Map<string, number>() // channel -> ref count

function notifyStateChange(): void {
  for (const listener of stateListeners) {
    try {
      listener()
    } catch {
      // ignore
    }
  }
}

function setState(next: ConnectionState): void {
  if (state !== next) {
    state = next
    notifyStateChange()
  }
}

function sendRaw(payload: Record<string, unknown>): void {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(payload))
  }
}

function resubscribeAll(): void {
  for (const channel of subscriptions.keys()) {
    sendRaw({ action: 'subscribe', channel })
  }
}

function scheduleReconnect(): void {
  if (intentionalClose) return
  if (reconnectTimer !== null) return
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null
    createConnection()
  }, reconnectDelay)
  reconnectDelay = Math.min(reconnectDelay * RECONNECT_MULTIPLIER, MAX_RECONNECT_MS)
}

function createConnection(): void {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return
  }

  setState('connecting')

  try {
    ws = new WebSocket(WS_URL)
  } catch {
    setState('disconnected')
    scheduleReconnect()
    return
  }

  ws.onopen = () => {
    setState('connected')
    reconnectDelay = INITIAL_RECONNECT_MS
    resubscribeAll()
  }

  ws.onmessage = (event: MessageEvent) => {
    try {
      const msg = JSON.parse(event.data as string) as Record<string, unknown>
      if (typeof msg.channel === 'string' && msg.data !== undefined) {
        for (const handler of messageHandlers) {
          try {
            handler(msg.channel as string, msg.data)
          } catch {
            // ignore handler errors
          }
        }
      }
    } catch {
      // ignore non-JSON messages
    }
  }

  ws.onclose = () => {
    ws = null
    setState('disconnected')
    scheduleReconnect()
  }

  ws.onerror = () => {
    // onclose will fire after onerror
  }
}

// --------------- Public API ---------------

/**
 * Increment reference count and ensure the connection is alive.
 */
export function acquire(): void {
  refCount++
  intentionalClose = false
  if (refCount === 1) {
    createConnection()
  }
}

/**
 * Decrement reference count; close the connection when nobody needs it.
 */
export function release(): void {
  refCount = Math.max(0, refCount - 1)
  if (refCount === 0) {
    intentionalClose = true
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    ws?.close()
    ws = null
    setState('disconnected')
  }
}

/**
 * Subscribe to a channel. Sends the subscribe command immediately if connected,
 * otherwise it will be sent on reconnect.
 */
export function subscribe(channel: string): void {
  const count = subscriptions.get(channel) ?? 0
  subscriptions.set(channel, count + 1)
  if (count === 0) {
    sendRaw({ action: 'subscribe', channel })
  }
}

/**
 * Unsubscribe from a channel.
 */
export function unsubscribe(channel: string): void {
  const count = subscriptions.get(channel) ?? 0
  if (count <= 1) {
    subscriptions.delete(channel)
    sendRaw({ action: 'unsubscribe', channel })
  } else {
    subscriptions.set(channel, count - 1)
  }
}

/**
 * Register a handler that receives all incoming channel messages.
 */
export function addMessageHandler(handler: MessageHandler): () => void {
  messageHandlers.add(handler)
  return () => {
    messageHandlers.delete(handler)
  }
}

/**
 * Subscribe to connection state changes (for useSyncExternalStore).
 */
export function subscribeToState(callback: () => void): () => void {
  stateListeners.add(callback)
  return () => {
    stateListeners.delete(callback)
  }
}

/**
 * Get the current connection state snapshot.
 */
export function getConnectionState(): ConnectionState {
  return state
}
