import { client } from './client'

export interface SystemUser {
  id: number
  username: string
  real_name?: string
  email?: string
  phone?: string
  department_name?: string
  role_name?: string
  role_id?: number
  status?: number
}

export const usersApi = {
  list: (params?: {
    page?: number
    page_size?: number
    keyword?: string
    role_id?: number
  }) => {
    const q = new URLSearchParams()
    if (params?.page) q.set('page', String(params.page))
    if (params?.page_size) q.set('page_size', String(params.page_size))
    if (params?.keyword) q.set('keyword', params.keyword)
    if (params?.role_id != null) q.set('role_id', String(params.role_id))
    const qs = q.toString()
    return client.get<{ items?: SystemUser[]; total?: number }>(
      `/api/v1/system/users${qs ? `?${qs}` : ''}`,
    )
  },

  update: (id: number, body: { role_id?: number; status?: number }) =>
    client.put<SystemUser>(`/api/v1/system/users/${id}`, body),
}
