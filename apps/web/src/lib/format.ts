export function formatCurrency(value: number, currency = 'CNY'): string {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency,
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
