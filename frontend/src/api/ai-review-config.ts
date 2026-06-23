import { client } from './client'

function qs(params?: Record<string, string | number | boolean | undefined>) {
  if (!params) return ''
  const parts = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
  return parts.length ? `?${parts.join('&')}` : ''
}

export interface ChecklistItem {
  id: number
  legacy_id: number
  category: string
  item: string
  description?: string
  risk_level: string
  gate_id: string
  gate_priority: number
  auto_detectable: boolean
  detect_config?: Record<string, unknown> | null
  enabled: boolean
}

export interface RiskLabel {
  id: string
  name: string
  category?: string
  gate_id?: string
  color?: string
  enabled?: boolean
}

export interface RevisionRoute {
  id: number
  issue_type: string
  default_method: string
  auto_applicable: boolean
  self_check_questions?: string
  notes?: string
  priority: number
  enabled: boolean
}

export interface HardRule {
  id: number
  rule_id: string
  name: string
  enabled: boolean
  rule_type: string
  config: Record<string, unknown>
  risk_level: string
  label_id?: string
  gate_id?: string
  dimension: string
  title?: string
  suggestion?: string
}

export interface LegalSnippet {
  id: number
  snippet_id: string
  keywords: string[]
  text: string
  enabled: boolean
}

export interface FeedbackStat {
  rule_key: string
  source: string
  fp_count: number
  confirm_count: number
  fp_rate: number
  suggest_disable: boolean
}

const P = '/api/v1/ai-review'

export const aiReviewConfigApi = {
  getVersion: () => client.get<{ version: string | null }>(`${P}/config/version`),
  listChecklist: (params?: { gate_id?: string; auto_detectable?: boolean; enabled?: boolean }) =>
    client.get<{ items: ChecklistItem[]; count: number }>(`${P}/config/checklist-items${qs(params)}`),
  createChecklist: (body: Partial<ChecklistItem>) =>
    client.post<ChecklistItem>(`${P}/config/checklist-items`, body),
  updateChecklist: (id: number, body: Partial<ChecklistItem>) =>
    client.put<ChecklistItem>(`${P}/config/checklist-items/${id}`, body),
  deleteChecklist: (id: number) => client.delete(`${P}/config/checklist-items/${id}`),
  listRiskLabels: () => client.get<{ items: RiskLabel[] }>(`${P}/config/risk-labels`),
  updateRiskLabel: (id: string, body: Partial<RiskLabel>) =>
    client.put<RiskLabel>(`${P}/config/risk-labels/${id}`, body),
  listRouting: () => client.get<{ items: RevisionRoute[] }>(`${P}/config/revision-routing`),
  createRouting: (body: Partial<RevisionRoute>) =>
    client.post<RevisionRoute>(`${P}/config/revision-routing`, body),
  updateRouting: (id: number, body: Partial<RevisionRoute>) =>
    client.put<RevisionRoute>(`${P}/config/revision-routing/${id}`, body),
  deleteRouting: (id: number) => client.delete(`${P}/config/revision-routing/${id}`),
  listHardRules: () => client.get<{ items: HardRule[] }>(`${P}/config/hard-rules`),
  createHardRule: (body: Partial<HardRule>) => client.post<HardRule>(`${P}/config/hard-rules`, body),
  updateHardRule: (id: number, body: Partial<HardRule>) =>
    client.put<HardRule>(`${P}/config/hard-rules/${id}`, body),
  deleteHardRule: (id: number) => client.delete(`${P}/config/hard-rules/${id}`),
  testRule: (body: { text: string; detect_config?: Record<string, unknown>; hard_rule?: Record<string, unknown>; amount?: number }) =>
    client.post<{ hits: unknown[]; count: number }>(`${P}/config/rules/test`, body),
  listLegalSnippets: (keyword?: string) =>
    client.get<{ items: LegalSnippet[] }>(`${P}/config/legal-snippets${qs({ keyword })}`),
  createLegalSnippet: (body: Partial<LegalSnippet>) =>
    client.post<LegalSnippet>(`${P}/config/legal-snippets`, body),
  updateLegalSnippet: (id: number, body: Partial<LegalSnippet>) =>
    client.put<LegalSnippet>(`${P}/config/legal-snippets/${id}`, body),
  deleteLegalSnippet: (id: number) => client.delete(`${P}/config/legal-snippets/${id}`),
  importLegalCsv: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return client.post<{ created: number; updated: number; skipped: number; errors: string[] }>(
      `${P}/config/legal-snippets/import-csv`,
      fd,
    )
  },
  publish: (note?: string) => client.post(`${P}/config/publish`, { note }),
  importSeeds: () => client.post<{ version: string }>(`${P}/config/import-seeds`),
  feedbackStats: (days = 30) =>
    client.get<{ items: FeedbackStat[]; days: number }>(`${P}/config/feedback-stats${qs({ days })}`),
  disableRule: (rule_key: string) => client.post(`${P}/config/disable-rule`, { rule_key }),
}
