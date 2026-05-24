import { client } from './client'

export interface NotificationItem {
  id: number
  title: string
  message?: string
  resource_type?: string
  resource_id?: number
  is_read: number | boolean
  created_at?: string
  channel?: string
}

export const notificationsApi = {
  list: (params?: { page?: number; page_size?: number; unread_only?: boolean }) => {
    const q = new URLSearchParams()
    if (params?.page) q.set('page', String(params.page))
    if (params?.page_size) q.set('page_size', String(params.page_size))
    if (params?.unread_only) q.set('unread_only', 'true')
    const qs = q.toString()
    return client.get<{ items?: NotificationItem[]; total?: number }>(
      `/api/v1/notifications/${qs ? `?${qs}` : ''}`,
    )
  },
  markRead: (id: number) =>
    client.patch<{ success?: boolean }>(`/api/v1/notifications/${id}/read`, {}),
}
