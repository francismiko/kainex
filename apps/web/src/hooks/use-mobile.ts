import { useState, useEffect } from 'react'

const MOBILE_BREAKPOINT = 1024 // lg breakpoint

export function useIsMobile() {
  const [isMobile, setIsMobile] = useState(
    typeof window !== 'undefined' ? window.innerWidth < MOBILE_BREAKPOINT : false,
  )

  useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`)
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches)
    mql.addEventListener('change', handler)
    setIsMobile(mql.matches)
    return () => mql.removeEventListener('change', handler)
  }, [])

  return isMobile
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
