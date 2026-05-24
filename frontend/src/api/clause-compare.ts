import { client } from './client'

export interface ClauseCompareResult {
  similarity_percent?: number
  diff_lines?: string[]
  changes?: Array<{
    type: string
    left_snippet?: string
    right_snippet?: string
  }>
  change_count?: number
}

export const clauseCompareApi = {
  compare: (left_text: string, right_text: string, left_label = '基准版', right_label = '对比版') =>
    client.post<ClauseCompareResult>('/api/v1/clause-compare/', {
      left_text,
      right_text,
      left_label,
      right_label,
    }),
}
