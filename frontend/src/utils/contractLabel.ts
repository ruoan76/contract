import type { Contract } from '@/types/models'
import { formatDate } from '@/utils/formatDate'

/** 合同下拉选项文案：含创建时间便于区分 */
export function formatContractOptionLabel(c: Contract): string {
  const datePart = formatDate(c.created_at)
  const suffix = datePart === '—' ? '' : ` · ${datePart}`
  return `#${c.id} ${c.title}${suffix}`
}
