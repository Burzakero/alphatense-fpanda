import { useEffect, useState } from 'react'
import { useInView } from '../../hooks/useInView'

function easeOutQuad(t: number) {
  return 1 - (1 - t) * (1 - t)
}

export function CountUpNumber({
  value,
  durationMs = 1200,
  prefix = '',
  suffix = '',
  decimals = 0,
}: {
  value: number
  durationMs?: number
  prefix?: string
  suffix?: string
  decimals?: number
}) {
  const { ref, inView } = useInView<HTMLSpanElement>()
  const [display, setDisplay] = useState(0)

  useEffect(() => {
    if (!inView) return
    let frame: number
    const start = performance.now()

    function tick(now: number) {
      const progress = Math.min((now - start) / durationMs, 1)
      setDisplay(value * easeOutQuad(progress))
      if (progress < 1) frame = requestAnimationFrame(tick)
    }

    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [inView, value, durationMs])

  return (
    <span ref={ref} className="tabular-nums">
      {prefix}
      {display.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}
      {suffix}
    </span>
  )
}
