import { useEffect, useRef, useSyncExternalStore } from 'react'
import { type Socket } from 'socket.io-client'
import { acquireSocket, releaseSocket, getSocket, getConnectionState } from '@/lib/websocket'

export function useWebSocket(
  event: string,
  handler: (data: unknown) => void,
): Socket {
  const handlerRef = useRef(handler)
  handlerRef.current = handler

  const socketRef = useRef<Socket | null>(null)

  useEffect(() => {
    const socket = acquireSocket()
    socketRef.current = socket

    const stableHandler = (data: unknown) => handlerRef.current(data)
    socket.on(event, stableHandler)

    return () => {
      socket.off(event, stableHandler)
      releaseSocket()
    }
  }, [event])

  return socketRef.current ?? getSocket()
}

function subscribeToConnection(callback: () => void): () => void {
  const socket = getSocket()
  socket.on('connect', callback)
  socket.on('disconnect', callback)
  return () => {
    socket.off('connect', callback)
    socket.off('disconnect', callback)
  }
}

export function useWebSocketStatus(): boolean {
  return useSyncExternalStore(subscribeToConnection, getConnectionState)
}
