import { client } from './client'

export interface ContractTemplate {
  id: number
  name: string
  category: string
  content?: string
  status: string
  version?: number
}

export const templatesApi = {
  list: (params?: Record<string, string | number>) => {
    const q = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([k, v]) => q.set(k, String(v)))
    }
    const qs = q.toString()
    return client.get<{ items?: ContractTemplate[]; total?: number }>(
      `/api/v1/templates/${qs ? `?${qs}` : ''}`,
    )
  },

  get: (id: number) => client.get<ContractTemplate>(`/api/v1/templates/${id}`),

  create: (body: { name: string; category: string; content: string }) =>
    client.post<ContractTemplate>('/api/v1/templates/', body),

  update: (id: number, body: Partial<{ name: string; category: string; content: string; status: string }>) =>
    client.put<ContractTemplate>(`/api/v1/templates/${id}`, body),

  publish: (id: number) => client.post<ContractTemplate>(`/api/v1/templates/${id}/publish`, {}),

  submitPublish: (id: number) =>
    client.post<ContractTemplate>(`/api/v1/templates/${id}/submit-publish`, {}),

  approvePublish: (id: number) =>
    client.post<ContractTemplate>(`/api/v1/templates/${id}/approve-publish`, {}),

  rejectPublish: (id: number) =>
    client.post<ContractTemplate>(`/api/v1/templates/${id}/reject-publish`, {}),

  deprecate: (id: number) =>
    client.post<ContractTemplate>(`/api/v1/templates/${id}/deprecate`, {}),
}
