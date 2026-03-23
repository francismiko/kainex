import { useSyncExternalStore } from 'react'

const MOBILE_BREAKPOINT = 1024 // lg breakpoint

function subscribeMobile(callback: () => void) {
  const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`)
  mql.addEventListener('change', callback)
  return () => mql.removeEventListener('change', callback)
}

function getSnapshotMobile() {
  return window.innerWidth < MOBILE_BREAKPOINT
}

function getServerSnapshotMobile() {
  return false
}

export function useIsMobile() {
  return useSyncExternalStore(subscribeMobile, getSnapshotMobile, getServerSnapshotMobile)
}

/**
 * Returns a responsive chart height.
 * @param desktopHeight Height for lg+ screens
 * @param mobileHeight  Height for <lg screens (defaults to ~60% of desktop or 250, whichever is larger)
 */
export function useChartHeight(desktopHeight: number, mobileHeight?: number) {
  const isMobile = useIsMobile()
  const effectiveMobile = mobileHeight ?? Math.max(Math.round(desktopHeight * 0.6), 250)
  return isMobile ? effectiveMobile : desktopHeight
}
