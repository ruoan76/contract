# API 接口规范

> 版本：**v1.1** | 日期：2026-05-18  
> 状态枚举：[contract-status-dictionary.md](./contract-status-dictionary.md) | 数据字典：[data-dictionary.md](./data-dictionary.md)  
> 真相源：[DESIGN_STATUS.md](./DESIGN_STATUS.md)

## v1.1 变更摘要

| 变更 | 说明 |
|------|------|
| 合同 `status` | 取消 `reviewing`；流程中用 `pending` + `approval_status` |
| `approval_status` | 扩展为子阶段枚举（见状态字典 §2） |
| 相对方 | ✅ `GET/POST/PUT /api/v1/counterparties` + 黑名单 |
| 评审域 | ✅ `/api/v1/reviews/*` + 修订 `/contracts/{id}/revisions` |
| 看板/流程匹配 | ✅ `GET /contracts/dashboard`、`/match-flow` |
| 配置/通知 | ✅ `/api/v1/config/thresholds`、`/api/v1/notifications` |
| RBAC | ✅ 写接口 role 校验（config/counterparties/seals/reviews/approvals） |
| OpenAPI | ✅ `backend/openapi.json`（`scripts/export_openapi.py`） |
| 履约/绩效 API | 标注 **V2**，V1 仅看板聚合接口 |

## 📋 接口总览

| 模块 | 前缀 | 说明 |
|------|------|------|
| 合同管理 | `/api/v1/contracts` | 合同 CRUD、看板、上传、修订 |
| 相对方 | `/api/v1/counterparties` | 相对方 CRUD、黑名单 |
| 审批流程 | `/api/v1/approvals` | 审批流程、节点操作 |
| 评审管理 | `/api/v1/reviews` | 评审工作台、意见、退回 |
| AI 审查 | `/api/v1/ai-review` | 合同审查、报告、反馈 |
| 风险预警 | `/api/v1/risks` | 风险列表、预警处理 |
| 用印管理 | `/api/v1/seals` | 用印申请、记录查询 |
| 归档台账 | `/api/v1/archives` | 归档、台账查询 |
| 审计日志 | `/api/v1/audit` | 操作日志查询 |
| 数据统计 | `/api/v1/statistics` | 统计报表 |
| 系统管理 | `/api/v1/system` | 用户、角色、部门 |

## 🔐 认证方式

所有接口需携带 JWT Token：

```
Authorization: Bearer <token>
```

## 📝 统一响应格式

```json
{
    "code": 200,
    "message": "success",
    "data": {},
    "timestamp": 1705308800
}
```

## 1. 合同管理接口

### 1.1 创建合同

```
POST /api/v1/contracts
```

**请求体：**
```json
{
    "title": "XXX 采购合同",
    "contract_type": "purchase",
    "counterparty_name": "XXX 公司",
    "counterparty_credit_code": "91110000XXX",
    "amount": 500000,
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "content": "合同内容..."
}
```

**响应：**
```json
{
    "code": 200,
    "data": {
        "id": 1001,
        "contract_no": "CTR-2024-001",
        "status": "draft",
        "created_at": "2024-01-15T10:00:00Z"
    }
}
```

### 1.2 合同列表

```
GET /api/v1/contracts?page=1&page_size=20&status=pending&type=purchase
```

**查询参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码，默认 1 |
| page_size | int | 每页数量，默认 20 |
| status | string | 状态筛选 |
| type | string | 类型筛选 |
| keyword | string | 关键词搜索 |
| start_date | string | 开始日期 |
| end_date | string | 结束日期 |
| risk_level | string | 风险等级 |

**响应：**
```json
{
    "code": 200,
    "data": {
        "total": 100,
        "page": 1,
        "page_size": 20,
        "items": [
            {
                "id": 1001,
                "contract_no": "CTR-2024-001",
                "title": "XXX 采购合同",
                "contract_type": "purchase",
                "counterparty_name": "XXX 公司",
                "amount": 500000,
                "status": "pending",
                "risk_level": "medium",
                "creator_name": "张三",
                "created_at": "2024-01-15T10:00:00Z"
            }
        ]
    }
}
```

### 1.3 合同详情

```
GET /api/v1/contracts/{id}
```

**响应：**
```json
{
    "code": 200,
    "data": {
        "id": 1001,
        "contract_no": "CTR-2024-001",
        "title": "XXX 采购合同",
        "contract_type": "purchase",
        "status": "pending",
        "counterparty": {
            "name": "XXX 公司",
            "credit_code": "91110000XXX",
            "credit_rating": "A"
        },
        "amount": 500000,
        "currency": "CNY",
        "tax_rate": 13.0,
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "content": "合同全文...",
        "versions": [
            {
                "version": 1,
                "created_at": "2024-01-15T10:00:00Z",
                "creator_name": "张三",
                "file_path": "/files/contract_1001_v1.pdf"
            }
        ],
        "approval_flow": {
            "flow_id": 5001,
            "status": "approving",
            "current_node": "legal_review",
            "progress": 2
        },
        "ai_review": {
            "review_id": "REV-2024-001",
            "risk_level": "medium",
            "risk_score": 65.5,
            "reviewed_at": "2024-01-15T11:00:00Z"
        }
    }
}
```

### 1.4 上传合同文件

```
POST /api/v1/contracts/{id}/upload
Content-Type: multipart/form-data
```

**请求体：**
| 参数 | 类型 | 说明 |
|------|------|------|
| file | file | 合同文件（PDF/Word/图片） |
| version_desc | string | 版本说明 |

**响应：**
```json
{
    "code": 200,
    "data": {
        "version_id": 2001,
        "version": 2,
        "file_path": "/files/contract_1001_v2.pdf",
        "file_size": 1024000,
        "file_hash": "abc123..."
    }
}
```

## 2. 审批流程接口

### 2.1 提交审批

```
POST /api/v1/approvals/submit
```

**请求体：**
```json
{
    "contract_id": 1001,
    "flow_type": "standard"
}
```

**响应：**
```json
{
    "code": 200,
    "data": {
        "flow_id": 5001,
        "status": "pending",
        "current_node": "dept_approval",
        "next_approvers": [
            {
                "id": 101,
                "name": "李四",
                "role": "部门主管"
            }
        ]
    }
}
```

### 2.2 审批操作

```
POST /api/v1/approvals/{flow_id}/approve
```

**请求体：**
```json
{
    "action": "approve",
    "comment": "同意，注意履约风险"
}
```

**action 可选值：**
| 值 | 说明 |
|----|------|
| approve | 通过 |
| reject | 拒绝 |
| return | 退回 |
| delegate | 委托 |
| countersign | 会签 |

### 2.3 待办列表

```
GET /api/v1/approvals/pending
```

**响应：**
```json
{
    "code": 200,
    "data": {
        "total": 12,
        "items": [
            {
                "flow_id": 5001,
                "contract_id": 1001,
                "contract_no": "CTR-2024-001",
                "title": "XXX 采购合同",
                "amount": 500000,
                "current_node": "legal_review",
                "initiator_name": "张三",
                "created_at": "2024-01-15T10:00:00Z",
                "deadline": "2024-01-17T10:00:00Z",
                "urgency": "normal"
            }
        ]
    }
}
```

### 2.4 审批历史

```
GET /api/v1/approvals/{flow_id}/history
```

**响应：**
```json
{
    "code": 200,
    "data": {
        "flow_id": 5001,
        "status": "approving",
        "steps": [
            {
                "step": 1,
                "node_name": "部门主管审批",
                "approver_name": "李四",
                "action": "approve",
                "comment": "同意",
                "status": "completed",
                "duration_hours": 2.5,
                "completed_at": "2024-01-15T12:30:00Z"
            },
            {
                "step": 2,
                "node_name": "法务审核",
                "approver_name": "王五",
                "action": null,
                "comment": null,
                "status": "pending",
                "duration_hours": null,
                "completed_at": null
            }
        ]
    }
}
```

## 3. AI 审查接口

### 3.1 发起审查

```
POST /api/v1/ai-review/review
```

**请求体：**
```json
{
    "contract_id": 1001,
    "version_id": 2001,
    "review_options": {
        "check_compliance": true,
        "check_risk": true,
        "check_finance": true,
        "check_performance": true,
        "check_anomaly": true
    }
}
```

**响应：**
```json
{
    "code": 200,
    "data": {
        "review_id": "REV-2024-001",
        "status": "reviewing",
        "estimated_seconds": 30
    }
}
```

### 3.2 审查结果

```
GET /api/v1/ai-review/{review_id}/result
```

**响应：**
```json
{
    "code": 200,
    "data": {
        "review_id": "REV-2024-001",
        "contract_id": 1001,
        "review_time": "2024-01-15T11:00:00Z",
        "overall": {
            "risk_level": "medium",
            "risk_score": 65.5,
            "recommendation": "中风险 - 建议修改关键条款后签署"
        },
        "clauses": [
            {
                "title": "违约责任",
                "risk_level": "high",
                "risk_score": 85,
                "issues": [
                    {
                        "type": "赔偿上限",
                        "description": "未设置赔偿上限",
                        "severity": "high",
                        "legal_basis": "《民法典》第 584 条"
                    }
                ],
                "suggestions": [
                    "建议增加赔偿上限条款"
                ]
            }
        ],
        "summary": {
            "total_clauses": 15,
            "high_risk": 3,
            "medium_risk": 5,
            "low_risk": 7,
            "total_issues": 12
        }
    }
}
```

### 3.3 审查报告导出

```
GET /api/v1/ai-review/{review_id}/report?format=pdf
```

**支持格式：** pdf, docx, json

## 4. 风险预警接口

### 4.1 风险列表

```
GET /api/v1/risks?level=high&status=pending
```

**响应：**
```json
{
    "code": 200,
    "data": {
        "total": 5,
        "items": [
            {
                "id": 3001,
                "contract_id": 1001,
                "contract_no": "CTR-2024-001",
                "type": "high_risk_clause",
                "level": "high",
                "title": "违约责任条款风险",
                "message": "未设置赔偿上限，存在无限责任风险",
                "source": "ai",
                "status": "pending",
                "created_at": "2024-01-15T11:00:00Z"
            }
        ]
    }
}
```

### 4.2 处理风险

```
POST /api/v1/risks/{id}/handle
```

**请求体：**
```json
{
    "status": "resolved",
    "comment": "已修改条款，增加赔偿上限"
}
```

## 5. 统计接口

### 5.1 合同统计

```
GET /api/v1/statistics/contracts?period=month&year=2024
```

**响应：**
```json
{
    "code": 200,
    "data": {
        "total_contracts": 150,
        "total_amount": 50000000,
        "by_type": [
            {"type": "purchase", "count": 80, "amount": 30000000},
            {"type": "sales", "count": 50, "amount": 15000000},
            {"type": "labor", "count": 20, "amount": 5000000}
        ],
        "by_status": [
            {"status": "approved", "count": 120},
            {"status": "pending", "count": 20},
            {"status": "rejected", "count": 10}
        ],
        "by_risk_level": [
            {"level": "high", "count": 5},
            {"level": "medium", "count": 30},
            {"level": "low", "count": 115}
        ]
    }
}
```

### 5.2 审批效率

```
GET /api/v1/statistics/approval-efficiency?period=month
```

**响应：**
```json
{
    "code": 200,
    "data": {
        "avg_approval_hours": 28.5,
        "max_approval_hours": 96,
        "min_approval_hours": 2,
        "overtime_rate": 0.15,
        "bottleneck_nodes": [
            {
                "node_name": "法务审核",
                "avg_hours": 45.2,
                "count": 50
            }
        ]
    }
}
```

## 6. 状态看板与到期提醒（V1 新增）

### 6.1 合同状态看板

```
GET /api/v1/contracts/dashboard
```

**查询参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| status | string | 执行状态：executing/completed/expired |
| days | int | 到期天数阈值，默认 30 |

**响应：**
```json
{
    "code": 200,
    "data": {
        "executing": [
            {
                "id": 1001,
                "contract_no": "CTR-2024-001",
                "title": "XXX 采购合同",
                "amount": 500000,
                "end_date": "2024-12-31",
                "days_remaining": 180,
                "status": "executing",
                "milestones": [
                    {"name": "交付产品", "planned_date": "2024-06-01", "status": "completed"},
                    {"name": "验收", "planned_date": "2024-07-01", "status": "pending"}
                ]
            }
        ],
        "expiring_soon": [
            {
                "id": 1002,
                "contract_no": "CTR-2024-002",
                "title": "YYY 服务合同",
                "amount": 200000,
                "end_date": "2024-02-10",
                "days_remaining": 12,
                "status": "expiring",
                "reminder_sent": true
            }
        ],
        "expired": [
            {
                "id": 1003,
                "contract_no": "CTR-2023-015",
                "title": "ZZZ 采购合同",
                "amount": 800000,
                "end_date": "2024-01-01",
                "days_overdue": 15,
                "status": "expired",
                "renewal_status": "pending"
            }
        ]
    }
}
```

### 6.2 到期提醒配置

```
POST /api/v1/reminders/expiration
```

**请求体：**
```json
{
    "contract_id": 1001,
    "reminder_days": [30, 15, 7],
    "recipients": ["creator", "dept_head", "legal"],
    "channels": ["system", "email", "feishu"]
}
```

### 6.3 审批规则配置 API（V1 新增）

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/v1/config/thresholds` | GET | 金额阈值配置列表 |
| `/api/v1/config/thresholds` | POST | 新增金额阈值 |
| `/api/v1/config/thresholds/{id}` | PUT | 更新金额阈值 |
| `/api/v1/config/approvers` | GET | 审批人配置列表 |
| `/api/v1/config/approvers` | POST | 新增审批人配置 |
| `/api/v1/config/approvers/{id}` | PUT | 更新审批人配置 |

## ❌ 错误码定义

| 错误码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 500 | 服务器内部错误 |
| 1001 | 合同状态异常 |
| 1002 | 审批流程异常 |
| 2001 | AI 审查失败 |
| 3001 | 文件上传失败 |

## 🔄 WebSocket 实时通知

```
WS /api/v1/ws/notifications
```

**消息格式：**
```json
{
    "type": "approval_pending",
    "data": {
        "flow_id": 5001,
        "contract_id": 1001,
        "message": "您有一条合同待审批"
    },
    "timestamp": 1705308800
}
```

**消息类型：**
| 类型 | 说明 |
|------|------|
| approval_pending | 待审批通知 |
| approval_completed | 审批完成通知 |
| ai_review_done | AI 审查完成 |
| risk_alert | 风险预警 |
| contract_expired | 合同到期提醒 |
| seal_approved | 用印审批通过 |
