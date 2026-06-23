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
  creator_id?: number
  start_date?: string
  end_date?: string
  sign_date?: string
  archive_date?: string
}

export interface ApprovalPendingItem {
  flow_id: number
  contract_id: number
  contract_no?: string
  contract_title?: string
  title?: string
  amount?: number
  counterparty_name?: string
  contract_type?: string
  current_step?: number
  current_node?: string
  current_node_name?: string
  flow_type?: string
  ai_risk_level?: string
  ai_review_status?: string
  created_at?: string
}

export interface DashboardBucketItem {
  id: number
  contract_no?: string
  title?: string
  counterparty_name?: string
  amount?: number
  status?: string
  start_date?: string
  end_date?: string
}

export interface DashboardStats {
  total?: number
  pending_approval?: number
  executing_count?: number
  expiring_soon_count?: number
  expired_count?: number
}

export interface DashboardData {
  stats?: DashboardStats
  executing?: DashboardBucketItem[]
  expiring_soon?: DashboardBucketItem[]
  expired?: DashboardBucketItem[]
}

export interface FlowMatchResult {
  flow_type: string
  flow_label?: string
  steps?: Array<{ step: number; role: string; name?: string }>
  [key: string]: unknown
}
