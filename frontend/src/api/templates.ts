import { client } from './client'

export interface ContractTemplate {
  id: number
  code?: string
  name: string
  category: string
  content?: string
  status: string
  version?: number
  variables?: string[]
  variable_count?: number
  archived_reason?: string
  created_at?: string
  updated_at?: string
}

export const templatesApi = {
  list: (params?: Record<string, string | number>) => {
    const q = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== '' && v != null) q.set(k, String(v))
      })
    }
    const qs = q.toString()
    return client.get<{ items?: ContractTemplate[]; total?: number; page?: number; page_size?: number }>(
      `/api/v1/templates/${qs ? `?${qs}` : ''}`,
    )
  },

  get: (id: number) => client.get<ContractTemplate>(`/api/v1/templates/${id}`),

  create: (body: { name: string; category: string; content: string }) =>
    client.post<ContractTemplate>('/api/v1/templates/', body),

  update: (id: number, body: Partial<{ name: string; category: string; content: string; status: string }>) =>
    client.put<ContractTemplate>(`/api/v1/templates/${id}`, body),

  fill: (id: number, values: Record<string, string | number>) =>
    client.post<{ content: string; template_id: number; template_version?: number; variables?: string[] }>(
      `/api/v1/templates/${id}/fill`,
      { values },
    ),

  publish: (id: number) => client.post<ContractTemplate>(`/api/v1/templates/${id}/publish`, {}),

  submitPublish: (id: number) =>
    client.post<ContractTemplate>(`/api/v1/templates/${id}/submit-publish`, {}),

  approvePublish: (id: number) =>
    client.post<ContractTemplate>(`/api/v1/templates/${id}/approve-publish`, {}),

  rejectPublish: (id: number) =>
    client.post<ContractTemplate>(`/api/v1/templates/${id}/reject-publish`, {}),

  deprecate: (id: number, reason?: string) =>
    client.post<ContractTemplate>(`/api/v1/templates/${id}/deprecate`, reason ? { reason } : {}),
}
