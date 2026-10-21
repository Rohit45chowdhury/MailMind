/** Format confidence as a percentage. Accepts 0-1 or 0-100. */
export function pct(value) {
  const n = Number(value)
  if (value === null || value === undefined || Number.isNaN(n)) return '—'
  return `${Math.round(n <= 1 ? n * 100 : n)}%`
}
