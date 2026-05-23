# 相对方管理设计文档

> 版本：V1.0 | 日期：2024-01-15

---

## 一、设计目标

建立相对方档案库，实现相对方信息统一管理、黑名单拦截、信用校验、历史履约追溯。

---

## 二、相对方档案结构

### 2.1 基础信息

```python
class Counterparty(BaseModel):
    """相对方档案"""
    id: int
    name: str                          # 相对方名称
    credit_code: str                   # 统一社会信用代码
    legal_representative: str          # 法定代表人
    contact_person: str                # 联系人
    contact_phone: str                 # 联系电话
    contact_email: str                 # 联系邮箱
    address: str                       # 注册地址
    industry: str                      # 行业分类
    company_type: str                  # 企业类型（国企/民企/外资/其他）
    registered_capital: float          # 注册资本（万元）
    establishment_date: date           # 成立日期
    business_scope: str                # 经营范围
    
    # 信用与风险
    credit_rating: str                 # 信用评级（A/B/C/D）
    blacklist_status: bool             # 是否在黑名单
    blacklist_reason: Optional[str]    # 黑名单原因
    blacklist_added_at: Optional[datetime]  # 加入黑名单时间
    
    # 元数据
    creator_id: int                    # 创建人 ID
    source: str                        # 数据来源（manual/tianyancha/qichacha）
    verified_at: Optional[datetime]    # 最后核验时间
    
    created_at: datetime
    updated_at: datetime
```

### 2.2 信用评级标准

| 等级 | 标准 | 处理策略 |
|------|------|---------|
| **A** | 注册资本>1000 万，无失信记录，经营状态正常 | 正常合作 |
| **B** | 注册资本 100-1000 万，无重大失信记录 | 正常合作，关注风险 |
| **C** | 注册资本<100 万，或有轻微失信记录 | 限制合作，需法务复核 |
| **D** | 有重大失信记录，或经营异常 | 禁止合作，加入黑名单 |

---

## 三、信用校验集成

### 3.1 天眼查/企查查 API 对接

```python
class CreditChecker:
    """信用校验服务"""
    
    def __init__(self):
        self.api_key = settings.TIANYANCHA_API_KEY
        self.base_url = "https://api.tianyancha.com/services/open"
    
    async def check_company(self, credit_code: str) -> Dict:
        """校验企业信息"""
        # 1. 调用天眼查 API
        response = await self._request("/company/baseinfo", {
            "creditCode": credit_code,
            "apiKey": self.api_key,
        })
        
        # 2. 解析返回数据
        company_info = {
            "name": response["name"],
            "legal_representative": response["legalRepresentative"],
            "registered_capital": response["registeredCapital"],
            "establishment_date": response["establishDate"],
            "business_status": response["openStatus"],
            "industry": response["industry"],
            "credit_rating": self._calculate_rating(response),
            "risk_info": self._extract_risk_info(response),
        }
        
        return company_info
    
    def _calculate_rating(self, company_info: Dict) -> str:
        """计算信用评级"""
        registered_capital = company_info.get("registered_capital", 0)
        risk_count = len(company_info.get("risk_info", []))
        business_status = company_info.get("business_status", "")
        
        if business_status != "存续":
            return "D"
        elif risk_count > 5:
            return "D"
        elif risk_count > 2:
            return "C"
        elif registered_capital > 1000:
            return "A"
        elif registered_capital > 100:
            return "B"
        else:
            return "C"
    
    def _extract_risk_info(self, company_info: Dict) -> List[Dict]:
        """提取风险信息"""
        risks = []
        
        # 失信被执行人
        if company_info.get("dishonest"):
            risks.append({
                "type": "dishonest",
                "description": "失信被执行人",
                "severity": "high",
            })
        
        # 经营异常
        if company_info.get("abnormal"):
            risks.append({
                "type": "abnormal",
                "description": "经营异常",
                "severity": "medium",
            })
        
        # 司法诉讼
        if company_info.get("lawsuits"):
            risks.append({
                "type": "lawsuit",
                "description": f"司法诉讼{len(company_info['lawsuits'])}起",
                "severity": "medium",
            })
        
        return risks
```

---

## 四、黑名单管理

### 4.1 黑名单规则

| 规则 | 触发条件 | 处理策略 |
|------|---------|---------|
| **失信被执行人** | 天眼查查询到失信记录 | 自动加入黑名单 |
| **经营异常** | 连续 2 年经营异常 | 自动加入灰名单 |
| **重大诉讼** | 司法诉讼>5 起 | 人工评估后加入黑名单 |
| **手动添加** | 法务/业务人员手动添加 | 立即生效 |

### 4.2 黑名单拦截流程

```
起草合同 → 选择相对方 → 检查黑名单 → 
  ├─ 不在黑名单 → 正常起草
  └─ 在黑名单 → 弹出警告 → 
      ├─ 法务复核通过 → 继续起草（标记"黑名单相对方 - 法务已复核"）
      └─ 法务复核拒绝 → 终止起草
```

---

## 五、历史履约统计

### 5.1 统计指标

| 指标 | 计算方式 | 用途 |
|------|---------|------|
| **合同总数** | COUNT(contracts) | 合作规模 |
| **合同总金额** | SUM(amount) | 合作规模 |
| **违约次数** | COUNT(risk_alerts WHERE type='breach') | 履约风险 |
| **平均账期** | AVG(payment_days) | 付款效率 |
| **逾期次数** | COUNT(delivery WHERE delayed) | 交付风险 |
| **纠纷次数** | COUNT(lawsuits) | 法律风险 |

### 5.2 统计查询

```python
class CounterpartyStatistics:
    """相对方统计服务"""
    
    async def get_statistics(self, counterparty_id: int) -> Dict:
        """获取相对方统计"""
        # 合同统计
        contracts = await self.db.contracts.find(
            {"counterparty_id": counterparty_id}
        )
        
        total_contracts = len(contracts)
        total_amount = sum(c.amount for c in contracts if c.amount)
        
        # 违约统计
        breaches = await self.db.risk_alerts.find({
            "counterparty_id": counterparty_id,
            "alert_type": "breach",
        })
        breach_count = len(breaches)
        
        # 逾期统计
        delays = await self.db.delivery_records.find({
            "counterparty_id": counterparty_id,
            "status": "delayed",
        })
        delay_count = len(delays)
        
        # 平均账期
        payment_days = [c.payment_days for c in contracts if c.payment_days]
        avg_payment_days = sum(payment_days) / len(payment_days) if payment_days else 0
        
        return {
            "total_contracts": total_contracts,
            "total_amount": total_amount,
            "breach_count": breach_count,
            "delay_count": delay_count,
            "avg_payment_days": round(avg_payment_days, 2),
            "risk_score": self._calculate_risk_score(breach_count, delay_count),
        }
    
    def _calculate_risk_score(self, breach_count: int, delay_count: int) -> float:
        """计算风险评分"""
        score = 0
        score += breach_count * 20
        score += delay_count * 10
        
        if score >= 60:
            return "D"
        elif score >= 40:
            return "C"
        elif score >= 20:
            return "B"
        else:
            return "A"
```

---

## 六、数据库设计

### 6.1 相对方表

```sql
CREATE TABLE counterparties (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(200) NOT NULL COMMENT '相对方名称',
    credit_code VARCHAR(50) UNIQUE NOT NULL COMMENT '统一社会信用代码',
    legal_representative VARCHAR(100) COMMENT '法定代表人',
    contact_person VARCHAR(100) COMMENT '联系人',
    contact_phone VARCHAR(50) COMMENT '联系电话',
    contact_email VARCHAR(100) COMMENT '联系邮箱',
    address VARCHAR(500) COMMENT '注册地址',
    industry VARCHAR(100) COMMENT '行业分类',
    company_type VARCHAR(50) COMMENT '企业类型',
    registered_capital DECIMAL(15,2) COMMENT '注册资本（万元）',
    establishment_date DATE COMMENT '成立日期',
    business_scope TEXT COMMENT '经营范围',
    
    -- 信用与风险
    credit_rating VARCHAR(10) DEFAULT 'B' COMMENT '信用评级',
    blacklist_status BOOLEAN DEFAULT FALSE COMMENT '是否在黑名单',
    blacklist_reason TEXT COMMENT '黑名单原因',
    blacklist_added_at TIMESTAMP NULL COMMENT '加入黑名单时间',
    
    -- 元数据
    creator_id BIGINT NOT NULL COMMENT '创建人 ID',
    source VARCHAR(50) DEFAULT 'manual' COMMENT '数据来源',
    verified_at TIMESTAMP NULL COMMENT '最后核验时间',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_name (name),
    INDEX idx_credit_code (credit_code),
    INDEX idx_blacklist (blacklist_status),
    INDEX idx_credit_rating (credit_rating),
    INDEX idx_creator (creator_id)
);
```

### 6.2 相对方统计视图

```sql
CREATE VIEW v_counterparty_statistics AS
SELECT 
    c.id AS counterparty_id,
    c.name AS counterparty_name,
    c.credit_rating,
    c.blacklist_status,
    COUNT(ct.id) AS total_contracts,
    SUM(ct.amount) AS total_amount,
    SUM(CASE WHEN ct.status = 'breach' THEN 1 ELSE 0 END) AS breach_count,
    AVG(ct.payment_days) AS avg_payment_days
FROM counterparties c
LEFT JOIN contracts ct ON c.id = ct.counterparty_id
GROUP BY c.id, c.name, c.credit_rating, c.blacklist_status;
```

---

## 七、API 设计

### 7.1 相对方管理 API

| 接口                                         | 方法   | 描述    |
| ------------------------------------------ | ---- | ----- |
| `/api/v1/counterparties`                   | GET  | 相对方列表 |
| `/api/v1/counterparties/{id}`              | GET  | 相对方详情 |
| `/api/v1/counterparties`                   | POST | 创建相对方 |
| `/api/v1/counterparties/{id}`              | PUT  | 更新相对方 |
| `/api/v1/counterparties/{id}/blacklist`    | POST | 加入黑名单 |
| `/api/v1/counterparties/{id}/credit-check` | POST | 信用校验  |
| `/api/v1/counterparties/{id}/statistics`   | GET  | 相对方统计 |
| `/api/v1/counterparties/import`            | POST | 批量导入  |
|                                            |      |       |

---

## 八、批量导入

### 8.1 Excel 导入格式

| 列名 | 必填 | 说明 |
|------|------|------|
| 相对方名称 | 是 | 企业全称 |
| 信用代码 | 是 | 18 位统一社会信用代码 |
| 法定代表人 | 否 | 法人姓名 |
| 联系人 | 否 | 业务联系人 |
| 联系电话 | 否 | 联系人电话 |
| 注册资本（万元） | 否 | 注册资本 |
| 行业分类 | 否 | 行业分类 |

### 8.2 导入流程

```
上传 Excel → 解析数据 → 校验格式 → 
  ├─ 校验通过 → 批量插入数据库
  └─ 校验失败 → 返回错误行号 + 错误原因
```

---

**文档维护者**：产品团队  
**最后更新**：2024-01-15
