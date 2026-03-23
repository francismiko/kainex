export function formatCurrency(value: number, currency = 'CNY'): string {
  const locale = currency === 'USD' ? 'en-US' : 'zh-CN'
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    maximumFractionDigits: 2,
  }).format(value)
}

export function formatPercent(value: number): string {
  return new Intl.NumberFormat('zh-CN', {
    style: 'percent',
    minimumFractionDigits: 2,
  }).format(value / 100)
}

export function formatNumber(value: number, decimals = 2): string {
  return new Intl.NumberFormat('zh-CN', {
    maximumFractionDigits: decimals,
  }).format(value)
}

/**
 * Format large numbers compactly (e.g. 1.2M, 340K).
 */
export function formatCompactNumber(value: number): string {
  const abs = Math.abs(value)
  const sign = value < 0 ? '-' : ''
  if (abs >= 1_000_000_000) {
    return `${sign}${(abs / 1_000_000_000).toFixed(1)}B`
  }
  if (abs >= 1_000_000) {
    return `${sign}${(abs / 1_000_000).toFixed(1)}M`
  }
  if (abs >= 1_000) {
    return `${sign}${(abs / 1_000).toFixed(1)}K`
  }
  return `${sign}${abs.toFixed(0)}`
}

/**
 * Format PnL value with +/- sign and return an object with the
 * formatted string and a tailwind class name for coloring.
 */
export function formatPnl(value: number, currency = 'CNY'): { text: string; className: string } {
  const formatted = formatCurrency(Math.abs(value), currency)
  if (value > 0) {
    return { text: `+${formatted}`, className: 'text-profit' }
  }
  if (value < 0) {
    return { text: `-${formatted}`, className: 'text-loss' }
  }
  return { text: formatted, className: 'text-muted-foreground' }
}

/**
 * Format a date string or Date into YYYY-MM-DD.
 */
export function formatDate(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

/**
 * Format a date string or Date into YYYY-MM-DD HH:mm:ss.
 */
export function formatDateTime(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}
