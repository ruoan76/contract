import { client } from './client'

export interface CounterpartyItem {
  id: number
  name: string
  credit_code?: string
  legal_person?: string
  contact_name?: string
  contact_phone?: string
  address?: string
  industry?: string
  credit_rating?: string
  is_blacklist?: boolean | number
  blacklist_reason?: string
  status?: number
  created_at?: string
  contract_count?: number
}

export interface CounterpartyListParams {
  page?: number
  page_size?: number
  keyword?: string
  is_blacklist?: number
  /** 1 启用，0 禁用，-1 不限 */
  status?: number
}

export interface CounterpartyListResult {
  items?: CounterpartyItem[]
  total?: number
  page?: number
  page_size?: number
}

export type CounterpartyPayload = {
  name: string
  credit_code?: string
  legal_person?: string
  contact_name?: string
  contact_phone?: string
  address?: string
  industry?: string
  credit_rating?: string
}

function buildQuery(params?: CounterpartyListParams): string {
  if (!params) return ''
  const q = new URLSearchParams()
  if (params.page != null) q.set('page', String(params.page))
  if (params.page_size != null) q.set('page_size', String(params.page_size))
  if (params.keyword) q.set('keyword', params.keyword)
  if (params.is_blacklist != null) q.set('is_blacklist', String(params.is_blacklist))
  if (params.status != null) q.set('status', String(params.status))
  const s = q.toString()
  return s ? `?${s}` : ''
}

export const counterpartiesApi = {
  create: (body: CounterpartyPayload) =>
    client.post<{ id: number }>('/api/v1/counterparties/', body),

  list: (params?: CounterpartyListParams) =>
    client.get<CounterpartyListResult>(`/api/v1/counterparties/${buildQuery(params)}`),

  get: (id: number) => client.get<CounterpartyItem>(`/api/v1/counterparties/${id}`),

  update: (id: number, body: Partial<CounterpartyPayload> & { status?: number }) =>
    client.put<CounterpartyItem>(`/api/v1/counterparties/${id}`, body),

  importCsv: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return client.post<{ created?: number; skipped?: number; errors?: string[] }>(
      '/api/v1/counterparties/import',
      fd,
    )
  },

  blacklist: (cpId: number, reason = '违规合作') =>
    client.post<CounterpartyItem>(`/api/v1/counterparties/${cpId}/blacklist`, { reason }),

  unblacklist: (cpId: number) =>
    client.post<CounterpartyItem>(`/api/v1/counterparties/${cpId}/unblacklist`, {}),

  disable: (cpId: number) =>
    client.post<CounterpartyItem>(`/api/v1/counterparties/${cpId}/disable`, {}),
}
