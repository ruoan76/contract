import type { Contract, DashboardData, FlowMatchResult } from '@/types/models'
import { client } from './client'

export interface ContractVersion {
  version: number
  content?: string
  change_description?: string
  file_path?: string
  file_hash?: string
  created_at?: string
}

export interface ContractUploadResult {
  contract_id: number
  file_path: string
  file_hash: string
  file_type?: string
  file_size?: number
  version_id?: number
  char_count?: number
  ocr_used?: boolean
}

export interface ContractParseFields {
  title?: string
  party_a?: string
  party_b?: string
  amount?: number
  contract_type?: string
  text_preview?: string
  full_text?: string
  char_count?: number
  ocr_used?: boolean
  needs_ocr?: boolean
  confidence?: number
  party_parse_warning?: boolean
  counterparty_corrections?: string[]
  parse_source?: string
}

export interface ContractParseResult {
  filename: string
  fields: ContractParseFields
  extracted_metadata?: Record<string, unknown>
  ocr_used?: boolean
  char_count?: number
}

export const contractsApi = {
  create: (payload: {
    title: string
    contract_type: string
    counterparty_name: string
    amount: number
    content?: string
  }) => client.post<Contract>('/api/v1/contracts/', payload),

  get: (id: number) => client.get<Contract>(`/api/v1/contracts/${id}`),

  list: (params?: Record<string, string | number>) => {
    const q = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([k, v]) => q.set(k, String(v)))
    }
    const qs = q.toString()
    return client.get<{ items?: Contract[]; total?: number }>(
      `/api/v1/contracts/${qs ? `?${qs}` : ''}`,
    )
  },

  listVersions: (id: number) =>
    client.get<ContractVersion[]>(`/api/v1/contracts/${id}/versions`),

  upload: (id: number, file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return client.post<ContractUploadResult>(`/api/v1/contracts/${id}/upload`, fd)
  },

  /** OCR 扫描件可能耗时数分钟，默认 15 分钟超时 */
  parse: (file: File, timeoutMs = 900_000) => {
    const fd = new FormData()
    fd.append('file', file)
    return client.post<ContractParseResult>('/api/v1/contracts/parse', fd, { timeoutMs })
  },

  dashboard: () => client.get<DashboardData>('/api/v1/contracts/dashboard'),

  update: (id: number, body: Partial<{
    title: string
    contract_type: string
    counterparty_name: string
    amount: number
    content: string
  }>) => client.put<Contract>(`/api/v1/contracts/${id}`, body),

  matchFlow: (amount: number) =>
    client.get<FlowMatchResult>(`/api/v1/contracts/match-flow?amount=${encodeURIComponent(amount)}`),

  submitRevision: (id: number, body: { content: string; change_description?: string }) =>
    client.post<{ version?: number }>(`/api/v1/contracts/${id}/revisions`, body),
}

/** 根据金额推断流程类型（与原型 resolveFlowType 简化版一致） */
export function resolveFlowType(contractType: string, amount: number): string {
  if (contractType === 'labor' || contractType === 'nda') return 'standard'
  if (amount > 1_000_000) return 'large_amount'
  if (amount > 100_000) return 'standard'
  return 'simple'
}

export function mapFlowTypeForApi(flowType: string): string {
  return flowType === 'special' ? 'large_amount' : flowType
}
