import { client } from './client'

/** API 与认证配置 */
export const API_CONFIG = {
  baseUrl: import.meta.env.VITE_API_BASE_URL || '',
  // 演示模式默认密码，建议通过 VITE_DEMO_PASSWORD 环境变量配置
  password: import.meta.env.VITE_DEMO_PASSWORD || 'admin123',
  roleUsers: {
    drafter: 'drafter1',
    approver: 'approver1',
    legal: 'legal1',
    finance: 'finance1',
    executive: 'executive1',
    admin: 'admin',
    archivist: 'admin',
  } as Record<string, string>,
}

export const ROLE_LABELS: Record<string, string> = {
  drafter: '起草人',
  approver: '部门主管',
  legal: '法务专员',
  finance: '财务专员',
  executive: '高管',
  archivist: '档案管理员',
  admin: '系统管理员',
}

export interface ThresholdsConfig {
  simple_max: number
  standard_max: number
  board_threshold: number
}

export interface ApproverConfig {
  id: number
  flow_type: string
  step: number
  role: string
  user_id?: number
  user_name?: string
}

export interface FlowNodeConfig {
  node_id: string
  node_name: string
  approver_role?: string
  user_id?: number
}

export const configApi = {
  getThresholds: () => client.get<ThresholdsConfig>('/api/v1/config/thresholds'),
  updateThresholds: (body: Partial<ThresholdsConfig>) =>
    client.put<ThresholdsConfig>('/api/v1/config/thresholds', body),
  getApprovers: () => client.get<ApproverConfig[]>('/api/v1/config/approvers'),
  createApprover: (body: Partial<ApproverConfig>) =>
    client.post<ApproverConfig>('/api/v1/config/approvers', body),
  updateApprover: (id: number, body: Partial<ApproverConfig>) =>
    client.put<ApproverConfig>(`/api/v1/config/approvers/${id}`, body),
  deleteApprover: (id: number) => client.delete<null>(`/api/v1/config/approvers/${id}`),
  getFlowNodes: (flowType?: string) => {
    const q = flowType ? `?flow_type=${encodeURIComponent(flowType)}` : ''
    return client.get<FlowNodeConfig[] | Record<string, FlowNodeConfig[]>>(
      `/api/v1/config/flow-nodes${q}`,
    )
  },
}
