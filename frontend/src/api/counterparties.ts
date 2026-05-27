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

  list: (params?: { page_size?: number }) => {
    let path = '/api/v1/counterparties/'
    if (params?.page_size) path += `?page_size=${params.page_size}`
    return client.get<{ items?: CounterpartyItem[] }>(path)
  },

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
