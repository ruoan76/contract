/** 合同正文标题识别 — 与后端 heading_utils 逻辑镜像 */

export const HEADING_LABEL_MAX = 80
export const HEADING_TITLE_SEGMENT_MAX = 36
export const HEADING_LINE_MAX = 80

const PAGE_MARKER_RE = /^---\s*第\s*(\d+)\s*页\s*---$/
const CLAUSE_HEADING_RE = /^(第[一二三四五六七八九十百零〇两]+条)/
const NUMBERED_SECTION_RE = /^(\d+(?:\.\d+){0,4})\s+(.+)$/
export const HEADING_LINE_START_RE = /^(?:第[一二三四五六七八九十百零〇两]+条|\d+(?:\.\d+){0,4}\s+)/

export function isPageMarker(line: string): boolean {
  return PAGE_MARKER_RE.test(line.trim())
}

export function parsePageNumber(line: string): number | null {
  const m = line.trim().match(PAGE_MARKER_RE)
  return m ? Number(m[1]) : null
}

export function isHeadingLineStart(line: string): boolean {
  return HEADING_LINE_START_RE.test(line.trim())
}

export function splitMixedHeadingLine(line: string): [string, string] | null {
  const stripped = line.trim()
  if (!stripped) return null

  if (CLAUSE_HEADING_RE.test(stripped)) {
    if (stripped.length <= HEADING_LINE_MAX) return [stripped, '']
    return [stripped.slice(0, HEADING_LINE_MAX), stripped.slice(HEADING_LINE_MAX).trim()]
  }

  const m = stripped.match(NUMBERED_SECTION_RE)
  if (!m) return null

  const number = m[1]
  const rest = m[2].trim()
  if (stripped.length <= HEADING_LINE_MAX && rest.length <= HEADING_TITLE_SEGMENT_MAX) {
    return [stripped, '']
  }

  let titlePart = rest
  let bodyPart = ''

  const parenNum = rest.match(/\(\d+\)\s*/)
  if (parenNum && parenNum.index != null) {
    const cut = parenNum.index + parenNum[0].length
    const candidateTitle = rest.slice(0, cut).trim()
    if (candidateTitle.length <= HEADING_TITLE_SEGMENT_MAX) {
      titlePart = candidateTitle
      bodyPart = rest.slice(cut).trim()
    }
  } else if (rest.length > HEADING_TITLE_SEGMENT_MAX) {
    titlePart = rest.slice(0, HEADING_TITLE_SEGMENT_MAX).trimEnd()
    bodyPart = rest.slice(HEADING_TITLE_SEGMENT_MAX).trim()
  }

  let headingText = `${number} ${titlePart}`.trim()
  if (headingText.length > HEADING_LABEL_MAX) {
    headingText = headingText.slice(0, HEADING_LABEL_MAX)
  }

  if (bodyPart) return [headingText, bodyPart]
  if (stripped.length <= HEADING_LINE_MAX) return [stripped, '']
  return [headingText, '']
}

export function outlineLabelForLine(line: string): string | null {
  const split = splitMixedHeadingLine(line)
  if (split) return split[0].slice(0, HEADING_LABEL_MAX)
  if (isPageMarker(line)) return line.trim()
  return null
}
