# 模板管理设计文档

> 版本：V1.0 | 日期：2024-01-15

---

## 一、设计目标

建立标准合同模板库，降低起草风险、提升起草效率、统一条款标准。

---

## 二、模板结构

### 2.1 模板字段定义

```python
class ContractTemplate(BaseModel):
    """合同模板"""
    id: int
    name: str                          # 模板名称
    code: str                          # 模板编码（如 PUR-001）
    category: str                      # 模板分类（采购/销售/劳务/保密/NDA）
    version: int                       # 版本号
    status: str                        # 状态（draft/published/archived）
    
    # 模板内容
    content: str                       # 模板文本（含可变字段标记）
    variables: List[TemplateVariable]  # 可变字段定义
    
    # 元数据
    description: str                   # 模板描述
    applicable_scenarios: str          # 适用场景
    creator_id: int                    # 创建人 ID
    reviewer_id: Optional[int]         # 审批人 ID
    published_at: Optional[datetime]   # 发布时间
    archived_at: Optional[datetime]    # 废止时间
    archived_reason: Optional[str]     # 废止原因
```

### 2.2 可变字段定义

```python
class TemplateVariable(BaseModel):
    """模板可变字段"""
    name: str              # 字段名（如{金额}）
    label: str             # 字段标签（如"合同金额"）
    type: str              # 字段类型（text/number/date/select）
    required: bool         # 是否必填
    default: Optional[str] # 默认值
    options: Optional[List[str]]  # 选项（type=select 时）
    validation: Optional[str]     # 校验规则（正则表达式）
    hint: Optional[str]    # 填写提示
```

---

## 三、模板分类与标准模板

### 3.1 模板分类

| 分类 | 编码 | 适用场景 | 标准模板数 |
|------|------|---------|-----------|
| **采购合同** | PUR | 采购商品/服务 | 3 |
| **销售合同** | SAL | 销售商品/服务 | 3 |
| **劳务合同** | LAB | 劳务派遣/外包 | 2 |
| **保密协议** | NDA | 保密信息交换 | 2 |
| **其他** | OTH | 其他类型合同 | 2 |

### 3.2 标准模板清单（V1）

| 模板名称 | 编码 | 分类 | 可变字段 | 适用场景 |
|---------|------|------|---------|---------|
| **标准采购合同** | PUR-001 | 采购 | {金额}、{交付周期}、{相对方} | 常规采购 |
| **服务采购合同** | PUR-002 | 采购 | {金额}、{服务期限}、{相对方} | 服务类采购 |
| **框架采购协议** | PUR-003 | 采购 | {框架金额}、{有效期}、{相对方} | 长期采购 |
| **标准销售合同** | SAL-001 | 销售 | {金额}、{交付周期}、{相对方} | 常规销售 |
| **服务销售合同** | SAL-002 | 销售 | {金额}、{服务期限}、{相对方} | 服务类销售 |
| **框架销售协议** | SAL-003 | 销售 | {框架金额}、{有效期}、{相对方} | 长期销售 |
| **标准劳务合同** | LAB-001 | 劳务 | {劳务费}、{劳务期限}、{相对方} | 常规劳务 |
| **外包劳务合同** | LAB-002 | 劳务 | {外包费}、{外包期限}、{相对方} | 劳务外包 |
| **标准保密协议** | NDA-001 | 保密 | {保密期限}、{相对方} | 常规保密 |
| **双向保密协议** | NDA-002 | 保密 | {保密期限}、{相对方} | 双向保密 |

---

## 四、模板可变字段示例

### 4.1 标准采购合同（PUR-001）

```
采购合同

甲方（采购方）：{采购方名称}
乙方（供应方）：{相对方}

鉴于甲方有意采购，乙方同意供应以下商品/服务，双方经协商一致，达成如下协议：

第一条 采购内容
1.1 商品/服务名称：{商品名称}
1.2 数量：{数量}
1.3 单价：{单价}
1.4 合同总金额：{金额}（大写：{金额大写}）

第二条 交付与验收
2.1 交付时间：{交付日期}
2.2 交付地点：{交付地点}
2.3 验收标准：{验收标准}

第三条 付款方式
3.1 预付款：{预付款比例}%
3.2 尾款：验收合格后{尾款账期}个工作日内支付

第四条 违约责任
（标准条款，不可修改）

第五条 争议解决
（标准条款，不可修改）

甲方（盖章）：              乙方（盖章）：
授权代表：                  授权代表：
日期：{签署日期}            日期：{签署日期}
```

**可变字段定义：**

| 字段名 | 标签 | 类型 | 必填 | 校验 |
|--------|------|------|------|------|
| {采购方名称} | 采购方名称 | text | 是 | - |
| {相对方} | 供应方 | select | 是 | 从相对方库选择 |
| {商品名称} | 商品名称 | text | 是 | - |
| {数量} | 数量 | number | 是 | >0 |
| {单价} | 单价 | number | 是 | >0 |
| {金额} | 合同总金额 | number | 是 | >0 |
| {金额大写} | 金额大写 | text | 否 | 自动生成 |
| {交付日期} | 交付时间 | date | 是 | >今天 |
| {交付地点} | 交付地点 | text | 是 | - |
| {验收标准} | 验收标准 | text | 是 | - |
| {预付款比例} | 预付款比例 | select | 是 | 0/30/50 |
| {尾款账期} | 尾款账期 | number | 是 | >0 |
| {签署日期} | 签署日期 | date | 是 | 今天 |

---

## 五、模板管理流程

### 5.1 模板创建流程

```
法务创建模板 → 标记可变字段 → 提交审批 → 法务负责人审批 → 发布生效
```

### 5.2 模板修订流程

```
法务修订模板 → 生成新版本 → 提交审批 → 法务负责人审批 → 新版本发布，旧版本废止
```

### 5.3 模板废止流程

```
法务废止模板 → 填写废止原因 → 模板状态变为"已废止" → 不可被新建合同引用
```

---

## 六、模板引擎设计

### 6.1 模板解析器

```python
class TemplateParser:
    """模板解析器"""
    
    def parse(self, template_content: str) -> Dict:
        """解析模板，提取可变字段"""
        import re
        
        # 匹配{字段名}格式
        pattern = r'\{([^}]+)\}'
        variables = re.findall(pattern, template_content)
        
        return {
            "content": template_content,
            "variables": variables,
            "fixed_content": re.sub(pattern, '_______', template_content),
        }
    
    def fill(self, template_content: str, values: Dict[str, str]) -> str:
        """填充可变字段"""
        content = template_content
        for name, value in values.items():
            content = content.replace(f'{{{name}}}', value)
        return content
    
    def validate(self, template_content: str, values: Dict[str, str]) -> List[str]:
        """校验字段值"""
        errors = []
        variables = self.parse(template_content)["variables"]
        
        for var in variables:
            if var not in values:
                errors.append(f"缺少必填字段：{var}")
            elif not values[var]:
                errors.append(f"字段值不能为空：{var}")
        
        return errors
```

### 6.2 模板引用流程

```python
class TemplateService:
    """模板服务"""
    
    async def create_from_template(self, template_id: int, values: Dict) -> Contract:
        """从模板创建合同"""
        # 1. 获取模板
        template = await self.db.templates.find(template_id)
        
        if template.status != "published":
            raise ValueError("模板未发布，不可引用")
        
        # 2. 校验字段值
        errors = self.parser.validate(template.content, values)
        if errors:
            raise ValueError(f"字段校验失败：{', '.join(errors)}")
        
        # 3. 填充模板
        content = self.parser.fill(template.content, values)
        
        # 4. 创建合同
        contract = Contract(
            title=template.name,
            contract_type=template.category,
            content=content,
            template_id=template_id,
            template_version=template.version,
            template_values=values,
        )
        
        await self.db.contracts.insert(contract)
        return contract
```

---

## 七、模板偏离检测

### 7.1 偏离检测逻辑

```python
class TemplateDeviationDetector:
    """模板偏离检测器"""
    
    def detect(self, contract_content: str, template_content: str) -> Dict:
        """检测合同与模板的偏离"""
        # 1. 提取固定条款
        template_fixed = self._extract_fixed_clauses(template_content)
        contract_fixed = self._extract_fixed_clauses(contract_content)
        
        # 2. 对比固定条款
        deviations = []
        for clause in template_fixed:
            if clause not in contract_fixed:
                deviations.append({
                    "clause": clause,
                    "type": "modified",  # modified/deleted/added
                    "severity": "high" if self._is_critical(clause) else "medium",
                })
        
        # 3. 检测新增条款
        for clause in contract_fixed:
            if clause not in template_fixed:
                deviations.append({
                    "clause": clause,
                    "type": "added",
                    "severity": "medium",
                })
        
        return {
            "deviations": deviations,
            "deviation_rate": len(deviations) / len(template_fixed),
            "risk_level": "high" if len(deviations) > 3 else "medium" if deviations else "low",
        }
    
    def _extract_fixed_clauses(self, content: str) -> List[str]:
        """提取固定条款（去除可变字段）"""
        import re
        # 移除可变字段标记
        cleaned = re.sub(r'\{[^}]+\}', '', content)
        # 按段落分割
        return [p.strip() for p in cleaned.split('\n\n') if p.strip()]
    
    def _is_critical(self, clause: str) -> bool:
        """判断是否为关键条款"""
        critical_keywords = ["违约责任", "争议解决", "管辖", "保密", "知识产权"]
        return any(keyword in clause for keyword in critical_keywords)
```

---

## 八、数据库设计

### 8.1 模板表

```sql
CREATE TABLE contract_templates (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(50) UNIQUE NOT NULL COMMENT '模板编码',
    name VARCHAR(200) NOT NULL COMMENT '模板名称',
    category VARCHAR(50) NOT NULL COMMENT '模板分类',
    version INT NOT NULL DEFAULT 1 COMMENT '版本号',
    status VARCHAR(20) NOT NULL DEFAULT 'draft' COMMENT 'draft/published/archived',
    
    -- 模板内容
    content LONGTEXT NOT NULL COMMENT '模板文本',
    variables JSON COMMENT '可变字段定义',
    
    -- 元数据
    description TEXT COMMENT '模板描述',
    applicable_scenarios TEXT COMMENT '适用场景',
    creator_id BIGINT NOT NULL COMMENT '创建人 ID',
    reviewer_id BIGINT COMMENT '审批人 ID',
    published_at TIMESTAMP NULL COMMENT '发布时间',
    archived_at TIMESTAMP NULL COMMENT '废止时间',
    archived_reason TEXT COMMENT '废止原因',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_code (code),
    INDEX idx_category (category),
    INDEX idx_status (status),
    INDEX idx_creator (creator_id)
);
```

### 8.2 模板审批记录表

```sql
CREATE TABLE template_approvals (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    template_id BIGINT NOT NULL,
    action VARCHAR(20) NOT NULL COMMENT 'approve/reject',
    comment TEXT COMMENT '审批意见',
    approver_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (template_id) REFERENCES contract_templates(id),
    INDEX idx_template (template_id)
);
```

---

## 九、API 设计

### 9.1 模板管理 API

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/v1/templates` | GET | 模板列表 |
| `/api/v1/templates/{id}` | GET | 模板详情 |
| `/api/v1/templates` | POST | 创建模板 |
| `/api/v1/templates/{id}` | PUT | 更新模板 |
| `/api/v1/templates/{id}/publish` | POST | 发布模板 |
| `/api/v1/templates/{id}/archive` | POST | 废止模板 |
| `/api/v1/templates/{id}/approve` | POST | 审批模板 |

### 9.2 模板引用 API

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/v1/contracts/from-template` | POST | 从模板创建合同 |
| `/api/v1/contracts/{id}/deviation` | GET | 检测模板偏离 |

---

**文档维护者**：产品团队  
**最后更新**：2024-01-15
