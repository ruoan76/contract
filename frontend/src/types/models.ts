/** 应用角色（与 seed_dev / permission-matrix 对齐） */
export type AppRole =
  | 'drafter'
  | 'approver'
  | 'legal'
  | 'finance'
  | 'executive'
  | 'archivist'
  | 'admin'

export interface ApiUser {
  id: number
  username: string
  real_name?: string
  role?: string
  department?: string
}

export interface Contract {
  id: number
  title: string
  contract_type: string
  counterparty_name: string
  amount: number
  status: string
  approval_status?: string
  content?: string
  current_flow_id?: number
  created_at?: string
}

export interface ApprovalPendingItem {
  flow_id: number
  contract_id: number
  contract_title?: string
  current_step?: number
  flow_type?: string
}

export interface DashboardData {
  pending_approval?: number
  in_review?: number
  sealed_or_archived?: number
  [key: string]: unknown
}

export interface FlowMatchResult {
  flow_type: string
  steps?: Array<{ step: number; role: string; name?: string }>
  [key: string]: unknown
}
