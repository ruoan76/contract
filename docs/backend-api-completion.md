# 后端 API 完成度报告

**检查日期**: 2026-05-26  
**检查范围**: `backend/app/api/v1/` 下所有路由文件  
**对照文档**: `api-page-mapping.md` v1.2.0

---

## ✅ 已实现 API 列表（有业务逻辑）

| 页面ID | API路径 | 文件 | 状态 | 备注 |
|--------|---------|------|------|------|
| dashboard | `GET /api/v1/contracts/dashboard` | contracts.py:86 | ✅ 已实现 | 返回 executing/expiring_soon/expired 三栏 |
| contracts | `GET /api/v1/contracts` | contracts.py:102 | ✅ 已实现 | 支持 status/type/risk_level/scope 参数 |
| contracts | `POST /api/v1/contracts` | contracts.py:49 | ✅ 已实现 | 支持 draft 创建 + AI 自动审查 |
| contracts | `GET /api/v1/contracts/{id}` | contracts.py:152 | ✅ 已实现 | 单合同详情 |
| contracts | `PUT /api/v1/contracts/{id}` | contracts.py:167 | ✅ 已实现 | 仅 draft 可编辑 |
| contracts | `POST /api/v1/contracts/{id}/upload` | contracts.py:211 | ✅ 已实现 | 上传文件并触发 AI |
| create | `POST /api/v1/contracts` | contracts.py:49 | ✅ 已实现 | 同上 |
| templates | `GET /api/v1/templates` | templates.py:41 | ✅ 已实现 | 支持分页 + 状态过滤 |
| templates | `POST /api/v1/templates` | templates.py:64 | ✅ 已实现 | 创建模板（仅 admin） |
| templates | `PUT /api/v1/templates/{id}` | templates.py:74 | ✅ 已实现 | 更新模板 |
| templates | `POST /api/v1/templates/{id}/publish` | templates.py:89 | ✅ 已实现 | 发布模板 |
| templates | `POST /api/v1/templates/{id}/deprecate` | templates.py:129 | ✅ 已实现 | 废止模板 |
| ai-review | `POST /api/v1/ai-review/review` | ai_review.py:41 | ✅ 已实现 | 发起 AI 审查 |
| ai-review | `GET /api/v1/ai-review/{id}/result` | ai_review.py:98 | ✅ 已实现 | 获取审查结果 |
| ai-review | `GET /api/v1/ai-review/{id}/report` | ai_review.py:153 | ✅ 已实现 | 导出报告 PDF/HTML/JSON |
| ai-review | `POST /api/v1/ai-review/{id}/feedback` | ai_review.py:178 | ✅ 已实现 | 误报/漏报反馈 |
| approvals | `POST /api/v1/approvals/submit` | approvals.py:42 | ✅ 已实现 | 提交审批流程 |
| approvals | `GET /api/v1/approvals/pending` | approvals.py:118 | ✅ 已实现 | 待办列表 |
| approvals | `POST /api/v1/approvals/{flow_id}/approve` | approvals.py:65 | ✅ 已实现 | 审批/拒绝/退回/委托 |
| approvals | `GET /api/v1/approvals/{flow_id}/history` | approvals.py:137 | ✅ 已实现 | 审批历史时间线 |
| archives | `GET /api/v1/archives/ledger` | archives.py:40 | ✅ 已实现 | 合同台账 + 导出 |
| archives | `POST /api/v1/archives/{id}/archive` | archives.py:18 | ✅ 已实现 | 归档合同 |
| counterparties | `GET /api/v1/counterparties` | counterparties.py:27 | ✅ 已实现 | 相对方列表 + 黑名单过滤 |
| counterparties | `POST /api/v1/counterparties` | counterparties.py:66 | ✅ 已实现 | 创建相对方 |
| counterparties | `PUT /api/v1/counterparties/{id}` | counterparties.py:79 | ✅ 已实现 | 更新相对方 |
| counterparties | `GET /api/v1/counterparties/{id}` | counterparties.py:57 | ✅ 已实现 | 相对方详情 |
| counterparties | `POST /api/v1/counterparties/import` | counterparties.py:41 | ✅ 已实现 | CSV 批量导入 |
| counterparties | `POST /api/v1/counterparties/{id}/blacklist` | counterparties.py:93 | ✅ 已实现 | 加入黑名单 |
| notifications | `GET /api/v1/notifications` | notifications.py:17 | ✅ 已实现 | 通知列表 + 未读过滤 |
| notifications | `PATCH /api/v1/notifications/{id}/read` | notifications.py:31 | ✅ 已实现 | 标记已读 |
| config | `GET /api/v1/config/thresholds` | config.py:20 | ✅ 已实现 | 获取审批阈值 |
| config | `PUT /api/v1/config/thresholds` | config.py:25 | ✅ 已实现 | 更新阈值（admin） |
| config | `GET /api/v1/config/approvers` | config.py:34 | ✅ 已实现 | 审批人配置 |
| config | `POST /api/v1/config/approvers` | config.py:39 | ✅ 已实现 | 新增审批人 |
| config | `PUT /api/v1/config/approvers/{id}` | config.py:48 | ✅ 已实现 | 更新审批人 |
| users | `GET /api/v1/system/users` | system.py:42 | ✅ 已实现 | 用户列表 + 部门/角色信息 |
| users | `POST /api/v1/system/users` | system.py:98 | ✅ 已实现 | 创建用户（admin） |
| users | `PUT /api/v1/system/users/{id}` | system.py:160 | ✅ 已实现 | 更新用户（admin） |
| users | `POST /api/v1/system/users/{id}/reset-password` | system.py:144 | ✅ 已实现 | 重置密码（admin） |
| audit | `GET /api/v1/audit` | audit.py:17 | ✅ 已实现 | 操作日志列表 |
| seals | `GET /api/v1/seals` | seals.py:21 | ✅ 已实现 | 用印列表 |
| seals | `POST /api/v1/seals/apply` | seals.py:54 | ✅ 已实现 | 用印申请 |
| seals | `POST /api/v1/seals/{id}/approve` | seals.py:85 | ✅ 已实现 | 审批用印（admin） |
| seals | `POST /api/v1/seals/{id}/upload-scan` | seals.py:101 | ✅ 已实现 | 上传用印扫描件 |
| messages | 规划 `GET /api/v1/notifications` | notifications.py:17 | ✅ 已实现 | 消息中心使用通知 API |
| review-center | `GET /api/v1/reviews/pending` | reviews.py:38 | ✅ 已实现 | 评审待办列表 |
| review-center | `GET /api/v1/reviews/conflicts` | reviews.py:25 | ⚠️ 骨架 | 冲突管理返回空列表 |
| review-workspace | `GET /api/v1/reviews/contracts/{id}` | reviews.py:49 | ✅ 已实现 | 评审工作台 |
| review-workspace | `POST /api/v1/reviews/contracts/{id}/opinions` | reviews.py:55 | ✅ 已实现 | 提交评审意见 |
| review-workspace | `POST /api/v1/reviews/contracts/{id}/return` | reviews.py:75 | ✅ 已实现 | 退回修改 |
| revision-workspace | `POST /api/v1/contracts/{id}/revisions` | contracts.py:262 | ✅ 已实现 | 提交修订 |
| seal | `GET /api/v1/seals` + `POST /api/v1/seals/apply` | seals.py | ✅ 已实现 | 用印管理全链路 |
| clause-compare | `POST /api/v1/clause-compare` | clause_compare.py:45 | ✅ 已实现 | 文本比对 |
| clause-compare | `POST /api/v1/clause-compare/upload` | clause_compare.py:60 | ✅ 已实现 | 文件比对 |
| risk-alerts | `GET /api/v1/risks` | risks.py:17 | ✅ 已实现 | 风险列表 |
| risk-alerts | `POST /api/v1/risks/{id}/handle` | risks.py:116 | ✅ 已实现 | 处理风险 |
| contract-ledger | `GET /api/v1/archives/ledger` | archives.py:40 | ✅ 已实现 | 合同台账 |
| expiring提醒 | `POST /api/v1/reminders/expiration` | reminders.py:29 | ✅ 已实现 | 到期提醒 |

---

## ⚠️ 骨架 API 列表（仅有路由，业务逻辑空白）

| 页面ID | API路径 | 文件 | 行号 | 说明 |
|--------|---------|------|------|------|
| review-center | `GET /api/v1/reviews/conflicts` | reviews.py:25 | 25-35 | 返回空列表，占位用 |
| messages | WebSocket | ws_notifications.py | - | 连接处理，支持广播 |

---

## ❌ 未实现 API

**无** - 所有页面主要功能 API 均已实现

---

## 🔍 重点检查项

### dashboard API
- ✅ **status**: `GET /api/v1/contracts/dashboard` (contracts.py:86)
- ✅ **实现**: `list_dashboard_buckets()` service 函数返回三栏数据
- ✅ **功能**: executing / expiring_soon / expired 桶划分完整

### counterparties API
- ✅ **status**: 完整 CRUD + 黑名单 + CSV 批量导入
- ✅ **实现**: counterparties.py 完整实现
- ✅ **权限**: admin 可加入黑名单

### templates API
- ✅ **status**: 完整模板管理（创建/更新/发布/废止）
- ✅ **实现**: templates.py 完整实现
- ✅ **审批流**: 支持 submit/approve/reject publish

### notifications API
- ✅ **status**: 完整通知系统（列表/已读/WebSocket）
- ✅ **实现**: notifications.py + ws_notifications.py
- ✅ **功能**: 飞书 webhook 已接（需配置 FEISHU_WEBHOOK_URL）

### dashboard 功能验证
```python
# contracts.py:86-90
@router.get("/dashboard", summary="合同看板")
async def dashboard(db: AsyncSession = Depends(get_db)):
    """executing / expiring_soon / expired 三栏"""
    data = await list_dashboard_buckets(db)
    return {"code": 200, "data": data}
```

### counterparties 完整性验证
```python
# counterparties.py:27-105
- GET /        → list_counterparties()
- POST /       → create_counterparty()
- PUT /{id}    → update_counterparty()
- GET /{id}    → get_counterparty()
- POST /import → import_counterparties_csv()
- POST /{id}/blacklist → add_to_blacklist()
```

### templates 完整性验证
```python
# templates.py:41-136
- GET /              → list_templates()
- GET /{id}          → get_template()
- POST /             → create_template() [admin]
- PUT /{id}          → update_template() [admin]
- POST /{id}/publish → publish_template() [admin]
- POST /{id}/submit-publish → submit_for_publish() [admin]
- POST /{id}/approve-publish → approve_publish() [admin/approver]
- POST /{id}/reject-publish → reject_publish() [admin/approver]
- POST /{id}/deprecate → deprecate_template() [admin]
```

---

## 📊 统计

| 分类 | 数量 |
|------|------|
| **已实现 API** | 47+ |
| **骨架 API** | 1 (conflicts 占位) |
| **未实现 API** | 0 |
| **文件总数** | 17 个 |

---

## 🔧 注意事项

1. **只读端点**：dashboard、audit、notifications、archives/ledger、counterparties/list 为 GET 只读
2. **权限控制**：admin/审批人角色在各路由中通过 `@require_role` / `@require_any_role` 控制
3. **WebSocket**：`ws_notifications.py` 提供实时通知广播能力
4. **飞书集成**：`app/utils/feishu.py` + `reminders.py` 实现到期提醒推送
