/** 模板 {变量} 解析与填充（与后端 template_parser 规则一致） */
const VAR_PATTERN = /\{([^{}]+)\}/g

export function extractTemplateVariables(content?: string | null): string[] {
  const seen = new Set<string>()
  const ordered: string[] = []
  const text = content || ''
  let m: RegExpExecArray | null
  const re = new RegExp(VAR_PATTERN.source, 'g')
  while ((m = re.exec(text)) !== null) {
    const name = m[1].trim()
    if (name && !seen.has(name)) {
      seen.add(name)
      ordered.push(name)
    }
  }
  return ordered
}

export function fillTemplateContent(content: string, values: Record<string, string | number>): string {
  let result = content
  for (const [name, value] of Object.entries(values)) {
    if (value == null) continue
    result = result.split(`{${name}}`).join(String(value))
  }
  return result
}

/** 常见变量名自动映射到起草表单字段 */
export const TEMPLATE_VAR_FORM_BIND: Record<string, 'counterparty_name' | 'amount' | 'title'> = {
  相对方: 'counterparty_name',
  供应方: 'counterparty_name',
  采购方名称: 'counterparty_name',
  金额: 'amount',
  合同金额: 'amount',
  合同标题: 'title',
}
