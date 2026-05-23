# 履约跟踪设计文档

> 版本：V2.0 | 日期：2024-01-15

---

## 一、设计目标

实现合同履约全过程跟踪，包括里程碑管理、履约状态更新、到期提醒、变更管理、提前终止、续签流程。

---

## 二、里程碑管理

### 2.1 里程碑定义

```python
class Milestone(BaseModel):
    """合同里程碑"""
    id: int
    contract_id: int                   # 合同 ID
    name: str                          # 里程碑名称
    type: str                          # 里程碑类型（delivery/acceptance/payment/other）
    planned_date: date                 # 计划日期
    actual_date: Optional[date]        # 实际日期
    status: str                        # 状态（pending/in_progress/completed/delayed/abnormal）
    description: Optional[str]         # 描述
    responsible_person_id: int         # 责任人 ID
    attachments: List[str]             # 附件（交付物/验收单等）
    
    created_at: datetime
    updated_at: datetime
```

### 2.2 里程碑类型

| 类型 | 说明 | 示例 |
|------|------|------|
| **delivery** | 交付节点 | 交付产品、交付文档 |
| **acceptance** | 验收节点 | 初验、终验 |
| **payment** | 付款节点 | 预付款、进度款、尾款 |
| **other** | 其他节点 | 培训、上线、维保 |

---

## 三、履约状态管理

### 3.1 状态定义

| 状态 | 说明 | 触发条件 |
|------|------|---------|
| **pending** | 待执行 | 合同签署完成 |
| **in_progress** | 执行中 | 第一个里程碑开始 |
| **completed** | 已完成 | 所有里程碑完成 |
| **delayed** | 延期 | 里程碑逾期未完成 |
| **abnormal** | 异常 | 履约过程中出现重大问题 |
| **terminated** | 已终止 | 提前解除合同 |

### 3.2 状态流转

```
pending → in_progress → completed
              ↓
          delayed → abnormal → terminated
```

---

## 四、到期提醒

### 4.1 提醒规则

| 提醒时间 | 提醒对象 | 提醒方式 |
|---------|---------|---------|
| **到期前 30 天** | 起草人 + 部门主管 | 系统通知 + 邮件 |
| **到期前 15 天** | 起草人 + 部门主管 + 法务 | 系统通知 + 邮件 + 企微 |
| **到期前 7 天** | 起草人 + 部门主管 + 法务 + 高管 | 系统通知 + 邮件 + 企微 + 短信 |
| **已到期** | 起草人 + 部门主管 + 法务 + 高管 | 系统通知 + 邮件 + 企微 + 短信 + 电话 |

### 4.2 提醒逻辑

```python
class ExpirationReminder:
    """到期提醒服务"""
    
    async def check_expiration(self):
        """检查即将到期合同"""
        today = date.today()
        
        # 到期前 30/15/7 天
        for days in [30, 15, 7]:
            target_date = today + timedelta(days=days)
            contracts = await self.db.contracts.find({
                "end_date": target_date,
                "status": {"$in": ["approved", "sealed"]},
            })
            
            for contract in contracts:
                await self._send_reminder(contract, days)
        
        # 已到期
        expired = await self.db.contracts.find({
            "end_date": {"$lt": today},
            "status": {"$in": ["approved", "sealed"]},
        })
        
        for contract in expired:
            await self._send_reminder(contract, 0)
    
    async def _send_reminder(self, contract: Contract, days: int):
        """发送提醒"""
        message = {
            "title": f"合同到期提醒（剩余{days}天）",
            "content": f"合同{contract.contract_no}将于{contract.end_date}到期",
            "contract_id": contract.id,
            "days_remaining": days,
        }
        
        # 根据剩余天数决定提醒对象和方式
        if days == 30:
            recipients = [contract.creator_id, contract.department_head_id]
            channels = ["system", "email"]
        elif days == 15:
            recipients = [contract.creator_id, contract.department_head_id, contract.legal_id]
            channels = ["system", "email", "wechat"]
        elif days == 7:
            recipients = [contract.creator_id, contract.department_head_id, contract.legal_id, contract.executive_id]
            channels = ["system", "email", "wechat", "sms"]
        elif days == 0:
            recipients = [contract.creator_id, contract.department_head_id, contract.legal_id, contract.executive_id]
            channels = ["system", "email", "wechat", "sms", "phone"]
        
        for recipient in recipients:
            for channel in channels:
                await self.notification_service.send(recipient, channel, message)
```

---

## 五、变更管理

### 5.1 变更流程

```
起草变更申请 → 说明变更内容 + 原因 → 提交审批 → 
  ├─ 小额变更 → 部门主管审批 → 生效
  ├─ 中额变更 → 部门主管→法务→财务审批 → 生效
  └─ 大额变更 → 部门主管→法务→财务→高管审批 → 生效
```

### 5.2 变更类型

| 类型 | 说明 | 审批流程 |
|------|------|---------|
| **金额变更** | 合同金额调整 | 根据变更金额选择流程 |
| **期限变更** | 交付/付款日期调整 | 部门主管→法务 |
| **条款变更** | 合同条款修改 | 部门主管→法务→财务 |
| **主体变更** | 相对方变更 | 部门主管→法务→财务→高管 |

---

## 六、提前终止

### 6.1 终止流程

```
起草终止申请 → 说明终止原因 → 提交审批 → 
  部门主管→法务→财务→高管审批 → 终止生效
```

### 6.2 终止原因

| 原因 | 说明 |
|------|------|
| **协商一致** | 双方协商一致终止 |
| **违约终止** | 对方违约，单方终止 |
| **不可抗力** | 不可抗力导致无法履行 |
| **业务调整** | 业务调整，不再需要 |

---

## 七、续签流程

### 7.1 续签触发

| 触发方式 | 说明 |
|---------|------|
| **自动触发** | 到期前 30 天自动触发续签流程 |
| **手动触发** | 业务人员手动发起续签 |

### 7.2 续签流程

```
续签申请 → 说明续签理由 + 新条款 → 提交审批 → 
  部门主管→法务→财务→高管审批 → 续签生效
```

---

## 八、数据库设计

### 8.1 里程碑表

```sql
CREATE TABLE milestones (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    contract_id BIGINT NOT NULL,
    name VARCHAR(200) NOT NULL COMMENT '里程碑名称',
    type VARCHAR(50) NOT NULL COMMENT '里程碑类型',
    planned_date DATE NOT NULL COMMENT '计划日期',
    actual_date DATE COMMENT '实际日期',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态',
    description TEXT COMMENT '描述',
    responsible_person_id BIGINT COMMENT '责任人 ID',
    attachments JSON COMMENT '附件',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (contract_id) REFERENCES contracts(id),
    INDEX idx_contract (contract_id),
    INDEX idx_status (status),
    INDEX idx_planned_date (planned_date)
);
```

### 8.2 变更申请表

```sql
CREATE TABLE contract_changes (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    contract_id BIGINT NOT NULL,
    change_type VARCHAR(50) NOT NULL COMMENT '变更类型',
    change_reason TEXT COMMENT '变更原因',
    change_content JSON COMMENT '变更内容',
    change_amount DECIMAL(15,2) COMMENT '变更金额',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态',
    applicant_id BIGINT NOT NULL COMMENT '申请人 ID',
    approved_by BIGINT COMMENT '审批人 ID',
    approved_at TIMESTAMP NULL COMMENT '审批时间',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (contract_id) REFERENCES contracts(id),
    INDEX idx_contract (contract_id),
    INDEX idx_status (status)
);
```

### 8.3 终止申请表

```sql
CREATE TABLE contract_terminations (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    contract_id BIGINT NOT NULL,
    termination_reason VARCHAR(100) NOT NULL COMMENT '终止原因',
    termination_description TEXT COMMENT '终止说明',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态',
    applicant_id BIGINT NOT NULL COMMENT '申请人 ID',
    approved_by BIGINT COMMENT '审批人 ID',
    approved_at TIMESTAMP NULL COMMENT '审批时间',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (contract_id) REFERENCES contracts(id),
    INDEX idx_contract (contract_id),
    INDEX idx_status (status)
);
```

### 8.4 续签申请表

```sql
CREATE TABLE contract_renewals (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    contract_id BIGINT NOT NULL COMMENT '原合同 ID',
    new_contract_id BIGINT COMMENT '新合同 ID',
    renewal_reason TEXT COMMENT '续签理由',
    new_terms JSON COMMENT '新条款',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态',
    applicant_id BIGINT NOT NULL COMMENT '申请人 ID',
    approved_by BIGINT COMMENT '审批人 ID',
    approved_at TIMESTAMP NULL COMMENT '审批时间',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (contract_id) REFERENCES contracts(id),
    FOREIGN KEY (new_contract_id) REFERENCES contracts(id),
    INDEX idx_contract (contract_id),
    INDEX idx_status (status)
);
```

---

## 九、API 设计

### 9.1 里程碑管理 API

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/v1/contracts/{id}/milestones` | GET | 里程碑列表 |
| `/api/v1/contracts/{id}/milestones` | POST | 创建里程碑 |
| `/api/v1/milestones/{id}` | PUT | 更新里程碑 |
| `/api/v1/milestones/{id}/complete` | POST | 完成里程碑 |

### 9.2 变更管理 API

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/v1/contracts/{id}/changes` | GET | 变更列表 |
| `/api/v1/contracts/{id}/changes` | POST | 创建变更申请 |
| `/api/v1/changes/{id}/approve` | POST | 审批变更 |

### 9.3 终止/续签 API

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/v1/contracts/{id}/termination` | POST | 申请终止 |
| `/api/v1/contracts/{id}/renewal` | POST | 申请续签 |

---

## 十、履约看板

### 10.1 看板设计

```
┌─────────────────────────────────────────────────────────────┐
│  履约看板                                                   │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────────────────────────────┐  │
│  │ 筛选        │  │ 里程碑列表                          │  │
│  │             │  │                                     │  │
│  │ 合同类型：  │  │ ● 交付产品  计划：2024-02-01        │  │
│  │ [全部▼]    │  │   实际：2024-02-01  ✓ 已完成        │  │
│  │             │  │                                     │  │
│  │ 状态：      │  │ ● 验收      计划：2024-02-15        │  │
│  │ [执行中▼]  │  │   实际：______  ○ 进行中            │  │
│  │             │  │                                     │  │
│  │ 到期提醒：  │  │ ● 付款      计划：2024-03-01        │  │
│  │ [30 天内▼] │  │   实际：______  ○ 待开始            │  │
│  │             │  │                                     │  │
│  │ [查询]     │  │ ● 维保      计划：2024-06-01        │  │
│  └─────────────┘  │   实际：______  ○ 待开始            │  │
│                   │                                     │  │
│                   │  [更新状态] [上传附件]               │  │
│                   └─────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

**文档维护者**：产品团队  
**最后更新**：2024-01-15
