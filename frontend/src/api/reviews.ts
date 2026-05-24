import { client } from './client'

export const reviewsApi = {
  submitOpinion: (contractId: number, role: string, action = 'approve', comment = '') =>
    client.post<unknown>(`/api/v1/reviews/contracts/${contractId}/opinions`, {
      role,
      action,
      comment,
    }),

  returnForRevision: (contractId: number, role = 'legal', comment = '') =>
    client.post<unknown>(`/api/v1/reviews/contracts/${contractId}/return`, { role, comment }),

  pending: (role?: string) => {
    const q = role ? `?role=${encodeURIComponent(role)}` : ''
    return client.get<{ items?: unknown[] }>(`/api/v1/reviews/pending${q}`)
  },

  workspace: (contractId: number) =>
    client.get<Record<string, unknown>>(`/api/v1/reviews/contracts/${contractId}`),

  history: (contractId: number) =>
    client.get<{ contract_id: number; opinions?: Array<Record<string, unknown>> }>(
      `/api/v1/reviews/contracts/${contractId}/history`,
    ),
}
