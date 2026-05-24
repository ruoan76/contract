import { client } from './client'

export interface AuditLogItem {
  id: number
  user_id?: number
  username?: string
  action?: string
  resource_type?: string
  resource_id?: number
  resource_name?: string
  detail?: unknown
  ip_address?: string
  status?: string
  created_at?: string
}

export const auditApi = {
  list: (params?: {
    page?: number
    page_size?: number
    action?: string
    resource_type?: string
  }) => {
    const q = new URLSearchParams()
    if (params?.page) q.set('page', String(params.page))
    if (params?.page_size) q.set('page_size', String(params.page_size))
    if (params?.action) q.set('action', params.action)
    if (params?.resource_type) q.set('resource_type', params.resource_type)
    const qs = q.toString()
    return client.get<{ items?: AuditLogItem[]; total?: number }>(
      `/api/v1/audit/${qs ? `?${qs}` : ''}`,
    )
  },
}
