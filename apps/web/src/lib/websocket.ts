import { io, type Socket } from 'socket.io-client'

let socket: Socket | null = null
let refCount = 0

export function getSocket(): Socket {
  if (!socket) {
    socket = io(import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000', {
      autoConnect: false,
      transports: ['websocket'],
    })
  }
  return socket
}

export function acquireSocket(): Socket {
  const s = getSocket()
  refCount++
  if (!s.connected) {
    s.connect()
  }
  return s
}

export function releaseSocket(): void {
  refCount = Math.max(0, refCount - 1)
  if (refCount === 0 && socket?.connected) {
    socket.disconnect()
  }
}

export function getConnectionState(): boolean {
  return socket?.connected ?? false
}
