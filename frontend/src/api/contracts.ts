import type { Contract, DashboardData, FlowMatchResult } from '@/types/models'
import { client } from './client'

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

  dashboard: () => client.get<DashboardData>('/api/v1/contracts/dashboard'),

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
