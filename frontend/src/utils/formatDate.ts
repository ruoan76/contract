const EMPTY = '—'

function parseIso(iso?: string | null): Date | null {
  if (!iso) return null
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? null : d
}

/** 日期 YYYY-MM-DD */
export function formatDate(iso?: string | null): string {
  const d = parseIso(iso)
  if (!d) return EMPTY
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(d)
}

/** 日期时间 YYYY-MM-DD HH:mm */
export function formatDateTime(iso?: string | null): string {
  const d = parseIso(iso)
  if (!d) return EMPTY
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(d)
}

/** 履约期：起止日期 */
export function formatDateRange(start?: string | null, end?: string | null): string {
  const s = formatDate(start)
  const e = formatDate(end)
  if (s === EMPTY && e === EMPTY) return EMPTY
  if (s !== EMPTY && e !== EMPTY) return `${s} ~ ${e}`
  return s !== EMPTY ? s : e
}
