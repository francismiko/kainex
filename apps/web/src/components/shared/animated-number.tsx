import { useEffect, useRef, useState } from 'react'
import { cn } from '@/lib/utils'

interface AnimatedNumberProps {
  value: number
  formatter?: (value: number) => string
  className?: string
  /** Duration of the flash animation in milliseconds (default: 600) */
  flashDuration?: number
}

/**
 * Displays a number that briefly flashes green (increase) or red (decrease)
 * when the value changes. Uses CSS transitions for lightweight animation.
 */
export function AnimatedNumber({
  value,
  formatter = (v) => v.toLocaleString(),
  className,
  flashDuration = 600,
}: AnimatedNumberProps) {
  const prevValueRef = useRef(value)
  const [flash, setFlash] = useState<'up' | 'down' | null>(null)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    const prev = prevValueRef.current
    if (prev !== value) {
      setFlash(value > prev ? 'up' : 'down')
      prevValueRef.current = value

      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
      timeoutRef.current = setTimeout(() => {
        setFlash(null)
        timeoutRef.current = null
      }, flashDuration)
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [value, flashDuration])

  return (
    <span
      className={cn(
        'inline-block transition-colors duration-300',
        flash === 'up' && 'text-profit',
        flash === 'down' && 'text-loss',
        className,
      )}
    >
      {formatter(value)}
    </span>
  )
}
