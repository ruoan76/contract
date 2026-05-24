import { client } from './client'

export interface CounterpartyItem {
  id: number
  name: string
  credit_code?: string
  is_blacklisted?: boolean | number
  status?: string
}

export const counterpartiesApi = {
  create: (body: { name: string; credit_code: string }) =>
    client.post<{ id: number }>('/api/v1/counterparties/', body),

  list: () => client.get<{ items?: CounterpartyItem[] }>('/api/v1/counterparties/'),

  blacklist: (cpId: number, reason = '违规') =>
    client.post<unknown>(`/api/v1/counterparties/${cpId}/blacklist`, { reason }),
}
