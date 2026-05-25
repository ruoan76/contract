import { client } from './client'

export interface CounterpartyItem {
  id: number
  name: string
  credit_code?: string
  is_blacklist?: boolean | number
  status?: string
}

export const counterpartiesApi = {
  create: (body: { name: string; credit_code: string }) =>
    client.post<{ id: number }>('/api/v1/counterparties/', body),

  list: () => client.get<{ items?: CounterpartyItem[] }>('/api/v1/counterparties/'),

  importCsv: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return client.post<{ created?: number; skipped?: number; errors?: string[] }>(
      '/api/v1/counterparties/import',
      fd,
    )
  },

  blacklist: (cpId: number, reason = '违规') =>
    client.post<unknown>(`/api/v1/counterparties/${cpId}/blacklist`, { reason }),
}
