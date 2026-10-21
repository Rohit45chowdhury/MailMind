/** Format confidence as a percentage. Accepts 0-1 or 0-100. */
export function pct(value) {
  const n = Number(value)
  if (value === null || value === undefined || Number.isNaN(n)) return '—'
  return `${Math.round(n <= 1 ? n * 100 : n)}%`
}

/** "5 min ago" style time from an ISO string. */
export function timeAgo(iso) {
  const sec = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
  if (sec < 60) return 'just now'
  if (sec < 3600) return `${Math.floor(sec / 60)} min ago`
  if (sec < 86400) return `${Math.floor(sec / 3600)} h ago`
  return `${Math.floor(sec / 86400)} d ago`
}