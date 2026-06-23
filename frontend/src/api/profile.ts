import { client } from './client'

export interface UserProfile {
  id: number
  username: string
  real_name?: string
  email?: string
  phone?: string
  department_name?: string
  role_name?: string
  role_code?: string
}

export const profileApi = {
  get: () => client.get<UserProfile>('/api/v1/system/profile'),
}
