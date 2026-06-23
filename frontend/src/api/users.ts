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
  created_at?: string
}

export interface SystemRole {
  id: number
  name: string
  code: string
  description?: string
}

export const usersApi = {
  list: (params?: {
    page?: number
    page_size?: number
    keyword?: string
    role_id?: number
    status?: number
  }) => {
    const q = new URLSearchParams()
    if (params?.page) q.set('page', String(params.page))
    if (params?.page_size) q.set('page_size', String(params.page_size))
    if (params?.keyword) q.set('keyword', params.keyword)
    if (params?.role_id != null) q.set('role_id', String(params.role_id))
    if (params?.status != null) q.set('status', String(params.status))
    const qs = q.toString()
    return client.get<{ items?: SystemUser[]; total?: number; page?: number; page_size?: number }>(
      `/api/v1/system/users${qs ? `?${qs}` : ''}`,
    )
  },

  /** 委托等场景：非管理员也可拉取启用用户简要列表 */
  listOptions: (params?: { keyword?: string; page_size?: number }) => {
    const q = new URLSearchParams()
    if (params?.keyword) q.set('keyword', params.keyword)
    if (params?.page_size) q.set('page_size', String(params.page_size))
    const qs = q.toString()
    return client.get<{ items?: SystemUser[] }>(
      `/api/v1/system/users/options${qs ? `?${qs}` : ''}`,
    )
  },

  listRoles: () => client.get<SystemRole[]>('/api/v1/system/roles'),

  create: (body: {
    username: string
    password: string
    real_name: string
    email?: string
    phone?: string
    department_id?: number
    role_id?: number
  }) => client.post<SystemUser>('/api/v1/system/users', body),

  update: (id: number, body: { role_id?: number; status?: number }) =>
    client.put<SystemUser>(`/api/v1/system/users/${id}`, body),

  resetPassword: (id: number, password: string) =>
    client.post<unknown>(`/api/v1/system/users/${id}/reset-password`, { password }),
}
