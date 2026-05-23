# 合同评审模块设计文档

> 版本：V1.0 | 日期：2024-01-15 | 范围：V1 MVP
>
> **定位**：以合同评审为纽带，串联 AI 审查、法务审核、财务审核、高管审批，
> 形成多角色协同、意见可追溯、结果可度量的完整评审闭环。

---

## 一、评审流程总览

### 1.1 完整评审闭环

```
合同提交
  ↓
【阶段一：AI 初筛（自动）】
  ├─ 硬规则引擎快速拦截（违约金上限、管辖法院、预付款比例）
  ├─ 知识库语义检索（Chroma 匹配相关法规）
  └─ LLM 逐条款审查 → 生成初筛报告（风险等级 + 条款详情 + 修改建议）
  ↓
【阶段二：法务评审（人工）】
  ├─ 复核 AI 初筛报告 → 确认 / 修正 / 补充
  ├─ 逐条款标注风险点 + 引用法律依据
  ├─ 输出评审意见：通过 / 有条件通过 / 退回修改
  └─ 若退回 → 起草人修订后重新提交评审
  ↓
【阶段三：财务评审（人工，按金额触发）】
  ├─ 审查付款条件、预付款比例、税务条款
  ├─ 核对预算额度（对接财务系统 / 手动确认）
  └─ 输出评审意见：通过 / 有条件通过 / 退回修改
  ↓
【阶段四：高管审批（按金额触发）】
  └─ 综合评审意见 → 最终决策：通过 / 拒绝
  ↓
【阶段五：评审归档】
  ├─ 所有评审意见汇总
  ├─ 评审记录锁定（不可修改）
  └─ 进入用印 / 签署流程
```

### 1.2 评审状态流转

```
                  ┌─────────┐
                  │  已提交  │ ← 起草人提交合同
                  └────┬────┘
                       │
                  ┌────▼────┐
                  │ AI 初筛 │ ← 自动触发
                  └────┬────┘
                       │
              ┌────────┼────────┐
              ▼        ▼        ▼
         ┌──────┐ ┌──────┐ ┌──────┐
         │待法务│ │待财务│ │待高管│ ← 并行 / 串行（按流程配置）
         │评审  │ │评审  │ │审批  │
         └──┬───┘ └──┬───┘ └──┬───┘
            │        │        │
  ┌─────────┼────────┼────────┼─────────────┐
  ▼         ▼        ▼        ▼             ▼
┌────┐  ┌────┐  ┌────┐  ┌────┐        ┌──────┐
│通过│  │返修│  │拒审│  │超时│        │争议   │
│    │  │    │  │    │  │    │        │升级   │
└─┬──┘  └─┬──┘  └──┬─┘  └──┬─┘        └──┬───┘
  │       │       │       │              │
  │       ▼       │       ▼              ▼
  │  ┌──────┐    │  ┌──────┐       ┌──────────┐
  │  │起草人│    │  │上级  │       │法务负责人 │
  │  │修订  │    │  │审批  │       │仲裁      │
  │  └──┬───┘    │  └──────┘       └──────────┘
  │     │        │
  │     └────────┤ (修订后重新提交)
  │              │
  ▼              ▼
┌──────────────────┐
│  综合评审通过     │ → 触发用印 / 签署
└──────────────────┘
```

---

## 二、评审角色与权限

### 2.1 角色定义

| 角色 | 职责 | 评审权限 | 数据范围 |
|------|------|---------|---------|
| **AI 审查引擎** | 初筛 + 生成报告 | 只读（合同内容） | 全部 |
| **法务评审员** | 法律风险审查 | 确认 / 修正 AI 结论 / 退回 | 全公司 |
| **法务负责人** | 争议仲裁 + 终审 | 最终裁决 / 覆盖法务评审员意见 | 全公司 |
| **财务评审员** | 财务条款审查 | 确认 / 退回 / 修改建议 | 全公司 |
| **高管审批人** | 最终决策 | 通过 / 拒绝（不可退回） | 全公司 |
| **起草人** | 接收反馈 + 修订 | 查看评审意见 / 修改合同 | 本人 |

### 2.2 权限矩阵

| 操作 | AI | 法务 | 法务负责人 | 财务 | 高管 | 起草人 |
|------|-----|------|----------|------|------|--------|
| 查看合同内容 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 查看 AI 初筛报告 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 标记风险条款 | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| 确认 / 修正 AI 结论 | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| 退回修改 | ✅(建议) | ✅ | ✅ | ✅ | ❌ | ❌ |
| 最终裁决 | ❌ | ❌ | ✅(争议) | ❌ | ✅ | ❌ |
| 修改合同文本 | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 查看评审历史 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 三、评审任务管理

### 3.1 任务自动分配策略

```python
class ReviewTaskDistributor:
    """评审任务分配器"""

    async def distribute(
        self, contract: Contract, flow_type: str
    ) -> Dict[str, List[int]]:
        """
        返回 {node_id: [assignee_ids], ...}
        """
        assignments = {}

        for node in self._get_flow_nodes(flow_type):
            assignee_type = node["assignee_type"]

            if assignee_type == "role":
                # 按角色分配
                role_code = node["assignee_value"]
                candidates = await self._get_users_by_role(role_code)
                assignments[node["id"]] = self._select_by_workload(candidates)

            elif assignee_type == "dept_head":
                # 合同创建人的部门主管
                dept_head = await self._get_dept_head(contract.creator_id)
                assignments[node["id"]] = [dept_head]

            elif assignee_type == "specific":
                # 指定具体用户
                assignments[node["id"]] = [node["assignee_value"]]

            elif assignee_type == "auto":
                # 自动匹配：法务按专长领域，财务按部门
                if node["role"] == "legal":
                    assignments[node["id"]] = await self._match_legal_expert(
                        contract.contract_type
                    )
                elif node["role"] == "finance":
                    assignments[node["id"]] = await self._match_finance_by_dept(
                        contract.department_id
                    )

        return assignments

    def _select_by_workload(self, candidates: List[int]) -> List[int]:
        """按工作量均衡分配"""
        # 查询候选人当前评审任务数，选择最少的一个
        workloads = {c: self._get_pending_count(c) for c in candidates}
        return sorted(workloads, key=workloads.get)[:1]
```

### 3.2 任务分配规则配置

| 合同类型 | 法务分配策略 | 财务分配策略 |
|---------|------------|------------|
| **采购合同** | 按专长 → 采购法务组 | 按部门 → 对应财务组 |
| **销售合同** | 按专长 → 销售法务组 | 按部门 → 对应财务组 |
| **劳务合同** | 按专长 → 劳动法务组 | 按部门 → 对应财务组 |
| **保密协议** | 轮询分配（工作量均衡） | 无需财务评审 |
| **其他** | 轮询分配 | 按部门 |

### 3.3 任务时效管理（SLA）

| 评审节点 | 标准时效 | 预警时效 | 升级时效 | 超时动作 |
|---------|---------|---------|---------|---------|
| **AI 初筛** | ≤30 秒 | - | - | 标记"AI 不可用"，转人工 |
| **法务评审** | 24 小时 | 18 小时 | 36 小时 | 升级至法务负责人 |
| **财务评审** | 24 小时 | 18 小时 | 36 小时 | 升级至财务主管 |
| **高管审批** | 48 小时 | 36 小时 | 72 小时 | 升级至 CEO |
| **起草人修订** | 72 小时 | 48 小时 | 120 小时 | 自动撤回合同 |

---

## 四、评审意见管理

### 4.1 意见结构模型

```python
class ReviewOpinion(BaseModel):
    """评审意见"""
    id: str                          # 意见 ID
    review_id: str                   # 评审记录 ID
    contract_id: int                 # 合同 ID
    version_id: int                  # 合同版本 ID
    stage: str                       # 评审阶段：ai / legal / finance / executive
    reviewer_id: int                 # 评审人 ID
    reviewer_role: str               # 评审人角色

    # 意见内容
    action: str                      # approve / conditional_approve / return / reject
    overall_comment: str             # 总体意见
    risk_level: str                  # 低 / 中 / 高
    risk_score: int                  # 0-100

    # 逐条款意见
    clause_opinions: List[ClauseOpinion]

    # 关键条款修改建议
    modification_suggestions: List[ModificationSuggestion]

    # 附件
    attachments: List[str]           # 附件 URL

    # 元数据
    created_at: datetime
    updated_at: datetime
    is_final: bool                   # 是否最终意见
    parent_opinion_id: Optional[str] # 引用上级意见（法务引用 AI）


class ClauseOpinion(BaseModel):
    """逐条款意见"""
    clause_id: str                   # 条款 ID
    clause_title: str                # 条款标题
    clause_content: str              # 条款原文
    ai_assessment: str               # AI 评估
    reviewer_assessment: str         # 评审人评估
    is_issue: bool                   # 是否有问题
    issue_type: str                  # 问题类型
    severity: str                    # 严重程度
    suggestion: str                  # 修改建议
    legal_basis: Optional[str]       # 法律依据
    confidence: Optional[int]        # 置信度
    is_disputed: bool                # 是否争议项
    dispute_reason: Optional[str]    # 争议原因


class ModificationSuggestion(BaseModel):
    """条款修改建议"""
    clause_id: str                   # 条款 ID
    original_text: str               # 原文
    suggested_text: str              # 建议修改后文本
    diff: str                        # Diff 对比
    reason: str                      # 修改原因
    priority: str                    # 必须修改 / 建议修改 / 可选
```

### 4.2 评审意见模板

#### 法务评审意见模板

```
════════════════════════════════════════════════
                法务评审意见
════════════════════════════════════════════════

合同编号：CTR-XXXX-XXXX
合同名称：XXX 采购合同
评审人：法务部 - XXX
评审时间：2024-01-15 14:30

【评审结论】：有条件通过

【总体意见】：
该合同整体条款较为完整，但存在以下需关注的风险点：
1. 违约责任条款未设置赔偿上限（高风险）
2. 管辖约定在乙方所在地（中风险）
3. 预付款比例 40%，略高于公司标准（低风险）

【风险评分】：65/100（中风险）

【逐条款意见】：详见附件《条款评审表》

【修改建议】：
1. 第四条违约责任：建议增加赔偿上限，不超过合同总额的 30%
2. 第六条管辖约定：建议修改为甲方所在地法院
3. 第三条付款条件：建议预付款比例降至 30%

【最终结论】：☐ 通过  ☑ 有条件通过  ☐ 退回修改  ☐ 拒绝

────────────────────────────────────────────────
法务评审员签字：________  日期：________
```

#### 财务评审意见模板

```
════════════════════════════════════════════════
                财务评审意见
════════════════════════════════════════════════

合同编号：CTR-XXXX-XXXX
合同名称：XXX 采购合同
评审人：财务部 - XXX
评审时间：2024-01-15 16:00

【评审结论】：有条件通过

【预算核对】：
- 申请金额：¥ 500,000
- 预算额度：¥ 600,000（采购部 Q1 预算）
- 已用额度：¥ 120,000
- 剩余额度：¥ 480,000
- 本次占比：83%（接近预算上限，建议关注）

【财务条款审查】：
1. 付款条件：预付款 40% → 建议降至 30%
2. 税务条款：含税价，税率 13%，无异常
3. 发票类型：增值税专用发票，符合要求

【最终结论】：☐ 通过  ☑ 有条件通过  ☐ 退回修改

────────────────────────────────────────────────
财务评审员签字：________  日期：________
```

### 4.3 多评审员意见冲突解决

```python
class ConflictResolver:
    """评审意见冲突解决"""

    async def resolve(self, opinions: List[ReviewOpinion]) -> ConflictResolution:
        conflicts = self._detect_conflicts(opinions)

        if not conflicts:
            return ConflictResolution(status="一致", summary="所有评审意见一致")

        # 冲突分类
        critical = [c for c in conflicts if c.severity == "critical"]
        major = [c for c in conflicts if c.severity == "major"]
        minor = [c for c in conflicts if c.severity == "minor"]

        if critical:
            # 存在严重冲突 → 升级至法务负责人仲裁
            return ConflictResolution(
                status="需仲裁",
                summary=f"存在 {len(critical)} 项严重冲突，已升级至法务负责人",
                conflicts=conflicts,
                escalate_to="legal_head",
            )

        if major:
            # 存在较大冲突 → 评审员协商
            return ConflictResolution(
                status="需协商",
                summary=f"存在 {len(major)} 项较大冲突，需评审员协商",
                conflicts=conflicts,
                escalate_to="reviewers",
            )

        # 轻微冲突 → 采用多数意见
        return ConflictResolution(
            status="多数决",
            summary=f"{len(minor)} 项轻微冲突，采用多数意见",
            resolved_by="majority_vote",
        )

    def _detect_conflicts(self, opinions: List[ReviewOpinion]) -> List[Conflict]:
        """检测冲突"""
        conflicts = []

        # 逐条款对比
        clause_map = {}
        for opinion in opinions:
            for clause_op in opinion.clause_opinions:
                clause_id = clause_op.clause_id
                if clause_id not in clause_map:
                    clause_map[clause_id] = []
                clause_map[clause_id].append(clause_op)

        # 检测同一条款的不同评估
        for clause_id, assessments in clause_map.items():
            if len(set(a.risk_level for a in assessments)) > 1:
                severity = self._assess_conflict_severity(assessments)
                conflicts.append(Conflict(
                    clause_id=clause_id,
                    assessments=assessments,
                    severity=severity,
                    description=f"条款 {clause_id} 存在分歧",
                ))

        return conflicts
```

---

## 五、评审记录与追溯

### 5.1 评审历史记录

```python
class ReviewHistory(BaseModel):
    """评审历史（不可变记录）"""
    id: str                          # 记录 ID
    contract_id: int                 # 合同 ID
    review_id: str                   # 评审单 ID
    sequence: int                    # 评审序号（第几次评审）
    version: int                     # 合同版本号

    # 流程信息
    flow_type: str                   # 简易 / 标准 / 特殊
    current_stage: str               # 当前阶段
    stage_history: List[StageRecord] # 各阶段记录

    # 评审结果
    final_action: str                # 通过 / 拒绝
    final_comment: str               # 最终评审意见
    final_risk_level: str            # 最终风险等级

    # 时间线
    submitted_at: datetime           # 提交时间
    started_at: datetime             # 开始评审时间
    completed_at: datetime           # 评审完成时间
    duration_hours: float            # 总耗时

    # 不可变保证
    locked: bool                     # 评审完成后锁定
    lock_reason: str                 # 锁定原因
    audit_hash: str                  # 记录哈希


class StageRecord(BaseModel):
    """阶段记录"""
    stage: str                       # ai / legal / finance / executive
    assignee_id: int                 # 评审人 ID
    assigned_at: datetime            # 分配时间
    started_at: Optional[datetime]   # 开始时间
    completed_at: Optional[datetime] # 完成时间
    action: Optional[str]            # 通过 / 退回 / 超时
    comment: Optional[str]           # 评审意见
    duration_hours: Optional[float]  # 耗时
    is_overtime: bool                # 是否超时
    escalation_count: int            # 升级次数
```

### 5.2 合同版本与评审痕迹关联

```
合同版本演进：

v1 (原始版本) → 提交评审
  ├─ AI 初筛：发现 3 项高风险条款
  ├─ 法务评审：确认 2 项，补充 1 项，退回修改
  ↓
v2 (修订版本) → 重新提交评审
  ├─ AI 初筛：风险降低为 1 项中风险
  ├─ 法务评审：确认无新增风险，通过
  ├─ 财务评审：通过
  ├─ 高管审批：通过
  ↓
v2 进入用印 / 签署

版本对比视图：
┌──────────┬──────────┬──────────┐
│   v1     │   变更    │   v2     │
├──────────┼──────────┼──────────┤
│ 违约金   │ 新增上限  │ 违约金   │
│ 无上限   │  ≤30%   │ ≤30%    │
│ (高风险) │          │ (低风险) │
├──────────┼──────────┼──────────┤
│ 管辖法院 │ 修改为   │ 管辖法院 │
│ 乙方所在 │ 甲方所在 │ 甲方所在 │
│ (中风险) │          │ (低风险) │
├──────────┼──────────┼──────────┤
│ 预付款   │ 降至     │ 预付款   │
│ 40%      │ 30%      │ 30%      │
│ (低风险) │          │ (低风险) │
└──────────┴──────────┴──────────┘
```

### 5.3 评审操作审计日志

```python
class ReviewAuditLog(BaseModel):
    """评审操作审计"""
    id: str
    review_id: str
    operator_id: int                 # 操作人
    action: str                      # assign / start / comment / approve / return / override
    detail: Dict                     # 操作详情
    ip_address: str
    user_agent: str
    timestamp: datetime
```

**日志记录点：**

| 操作 | 记录内容 |
|------|---------|
| 任务分配 | 分配人、分配给谁、分配时间 |
| 开始评审 | 评审人、合同 ID、开始时间 |
| 提交意见 | 意见 ID、动作、风险等级 |
| 退回修改 | 退回原因、退回人、退回时间 |
| 覆盖意见 | 操作人、被覆盖意见 ID、原因 |
| 最终批准 | 审批人、审批时间、结论 |
| 意见修改 | 修改人、修改内容、修改时间（仅法务负责人可） |

---

## 六、评审协作机制

### 6.1 并行评审流程

```
合同提交 → AI 初筛
              ↓
    ┌─────────┼─────────┐
    ▼         ▼         ▼
  法务      财务      高管
  (串行)    (串行)    (等待法务+财务完成)
    │         │         │
    ├─────────┤         │
    │  意见汇总  │         │
    │         │         │
    │    ┌────┘         │
    │    │              │
    └────┼──────────────┘
         ▼
      终审意见
```

### 6.2 通知与催办

| 事件 | 通知对象 | 通知渠道 | 通知内容 |
|------|---------|---------|---------|
| **任务分配** | 评审人 | 系统 + 飞书 + 邮件 | 待评审合同名称、编号、提交人 |
| **临近到期** | 评审人 | 系统 + 飞书 | 距离到期剩余 XX 小时 |
| **已超期** | 评审人 + 上级 | 系统 + 飞书 + 邮件 + 短信 | 已超期，请尽快处理 |
| **冲突升级** | 法务负责人 | 系统 + 飞书 | 评审意见冲突，需仲裁 |
| **评审完成** | 起草人 + 下一节点评审人 | 系统 + 飞书 | 评审通过 / 退回修改 |
| **退回修改** | 起草人 | 系统 + 飞书 + 邮件 | 退回原因 + 修改建议 |

### 6.3 评论与批注

```python
class ReviewComment(BaseModel):
    """评审评论/批注"""
    id: str
    review_id: str                   # 所属评审
    parent_comment_id: Optional[str] # 父评论（支持嵌套）
    clause_id: Optional[str]         # 关联条款
    author_id: int                   # 作者
    content: str                     # 内容
    type: str                        # comment / question / note / decision
    is_resolved: bool                # 是否已解决
    created_at: datetime
```

---

## 七、评审统计与质量度量

### 7.1 评审效率指标

| 指标 | 计算方式 | 用途 |
|------|---------|------|
| **平均评审时长** | AVG(completed_at - submitted_at) | 评估流程效率 |
| **各阶段平均时长** | AVG(各阶段 completed - started) | 定位瓶颈节点 |
| **退回修改率** | COUNT(return_actions) / COUNT(total) | 评估合同质量 |
| **一次通过率** | COUNT(一次通过) / COUNT(total) | 评估审查有效性 |
| **超时率** | COUNT(超时) / COUNT(total) | 评估 SLO 达成 |
| **争议升级率** | COUNT(冲突升级) / COUNT(total) | 评估评审一致性 |

### 7.2 评审质量指标

| 指标 | 计算方式 | 用途 |
|------|---------|------|
| **AI 准确率** | COUNT(AI 与法务一致) / COUNT(total) | 评估 AI 审查质量 |
| **AI 漏报率** | COUNT(AI 漏报) / COUNT(总风险) | 评估 AI 安全性 |
| **AI 误报率** | COUNT(AI 误报) / COUNT(AI 标记) | 评估 AI 可用性 |
| **评审意见采纳率** | COUNT(意见被采纳) / COUNT(总意见) | 评估意见有效性 |
| **法务工作量** | 人均评审合同数 / 月 | 评估资源配置 |

### 7.3 评审看板

```
┌─────────────────────────────────────────────────────────────┐
│  评审看板                                                   │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ 待评审   │ │ 评审中   │ │ 争议中   │ │ 已完成   │       │
│  │   12     │ │   5      │ │   2      │ │   45     │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 本周评审趋势                                        │    │
│  │                                                      │    │
│  │  ▁ ▂ ▃ ▅ ▇ █ ▇ (柱状图：每日评审完成数)             │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 节点耗时分布                                        │    │
│  │                                                      │    │
│  │  法务评审 ████████████████████ 8.5h (平均)          │    │
│  │  财务评审 ██████████ 4.2h                            │    │
│  │  高管审批 ██████ 2.1h                                │    │
│  │  AI 初筛  ▍ 18s                                     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ AI 审查质量                                         │    │
│  │                                                      │    │
│  │  准确率 ████████████████████ 87.5%                  │    │
│  │  漏报率 ████ 8.2%                                   │    │
│  │  误报率 ██ 4.3%                                     │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 八、数据库设计补充

### 8.1 评审记录表

```sql
CREATE TABLE review_records (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    contract_id BIGINT NOT NULL,
    version_id BIGINT NOT NULL,
    review_id VARCHAR(50) UNIQUE NOT NULL COMMENT 'REV-YYYYMMDD-SEQ',
    sequence INT NOT NULL DEFAULT 1 COMMENT '第几次评审',
    flow_type VARCHAR(50) NOT NULL COMMENT 'simple/standard/special',

    -- 进度
    current_stage VARCHAR(50) NOT NULL DEFAULT 'ai' COMMENT 'ai/legal/finance/executive',
    total_stages INT NOT NULL COMMENT '总阶段数',
    completed_stages INT DEFAULT 0 COMMENT '已完成阶段数',

    -- 结果
    final_action VARCHAR(50) COMMENT 'approve/conditional_approve/reject',
    final_risk_level VARCHAR(20),
    final_risk_score INT,
    final_comment TEXT,

    -- 时间
    submitted_at TIMESTAMP NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_hours DECIMAL(10,2),

    -- 锁定
    locked BOOLEAN DEFAULT FALSE,
    locked_at TIMESTAMP,
    audit_hash VARCHAR(64),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (contract_id) REFERENCES contracts(id),
    INDEX idx_contract (contract_id),
    INDEX idx_review_id (review_id),
    INDEX idx_current_stage (current_stage),
    INDEX idx_submitted (submitted_at)
);
```

### 8.2 评审阶段记录表

```sql
CREATE TABLE review_stage_records (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    review_id BIGINT NOT NULL,
    stage VARCHAR(50) NOT NULL COMMENT 'ai/legal/finance/executive',
    assignee_type VARCHAR(50) COMMENT 'role/dept_head/specific/auto',
    assignee_id BIGINT,
    assigned_at TIMESTAMP NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    action VARCHAR(50) COMMENT 'approve/return/reject/overtime',
    risk_level VARCHAR(20),
    risk_score INT,
    comment TEXT,
    duration_hours DECIMAL(10,2),
    is_overtime BOOLEAN DEFAULT FALSE,
    escalation_count INT DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (review_id) REFERENCES review_records(id),
    INDEX idx_review (review_id),
    INDEX idx_assignee (assignee_id),
    INDEX idx_stage (stage)
);
```

### 8.3 评审意见表

```sql
CREATE TABLE review_opinions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    review_id BIGINT NOT NULL,
    contract_id BIGINT NOT NULL,
    version_id BIGINT NOT NULL,
    stage VARCHAR(50) NOT NULL,
    reviewer_id BIGINT NOT NULL,
    reviewer_role VARCHAR(50) NOT NULL,

    action VARCHAR(50) NOT NULL COMMENT 'approve/conditional_approve/return/reject',
    overall_comment TEXT,
    risk_level VARCHAR(20),
    risk_score INT,

    clause_opinions JSON COMMENT '逐条款意见',
    modification_suggestions JSON COMMENT '修改建议',
    attachments JSON COMMENT '附件 URL 列表',

    is_final BOOLEAN DEFAULT FALSE,
    parent_opinion_id BIGINT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (review_id) REFERENCES review_records(id),
    INDEX idx_review (review_id),
    INDEX idx_contract (contract_id),
    INDEX idx_reviewer (reviewer_id)
);
```

### 8.4 评审评论表

```sql
CREATE TABLE review_comments (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    review_id BIGINT NOT NULL,
    parent_comment_id BIGINT,
    clause_id VARCHAR(100),
    author_id BIGINT NOT NULL,
    content TEXT NOT NULL,
    type VARCHAR(50) DEFAULT 'comment' COMMENT 'comment/question/note/decision',
    is_resolved BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (review_id) REFERENCES review_records(id),
    INDEX idx_review (review_id),
    INDEX idx_clause (clause_id)
);
```

### 8.5 评审冲突记录表

```sql
CREATE TABLE review_conflicts (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    review_id BIGINT NOT NULL,
    clause_id VARCHAR(100) NOT NULL,
    severity VARCHAR(50) NOT NULL COMMENT 'critical/major/minor',
    description TEXT NOT NULL,
    involved_reviewers JSON COMMENT '涉及评审人 ID 列表',
    resolution_method VARCHAR(50) COMMENT 'escalate/discuss/majority_vote',
    resolved_by BIGINT COMMENT '解决人 ID',
    resolved_at TIMESTAMP,
    resolution_note TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (review_id) REFERENCES review_records(id),
    INDEX idx_review (review_id)
);
```

---

## 九、API 接口设计

### 9.1 评审管理 API

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/v1/reviews` | GET | 评审列表（支持阶段/状态筛选） |
| `/api/v1/reviews/{id}` | GET | 评审详情 |
| `/api/v1/reviews/{id}/stages` | GET | 各阶段评审记录 |
| `/api/v1/reviews/{id}/opinions` | GET | 评审意见列表 |
| `/api/v1/reviews/{id}/opinions` | POST | 提交评审意见 |
| `/api/v1/reviews/{id}/opinions/{op_id}` | PUT | 修改评审意见（限法务负责人） |
| `/api/v1/reviews/{id}/conflicts` | GET | 评审冲突列表 |
| `/api/v1/reviews/{id}/conflicts/{cid}` | POST | 解决冲突 |
| `/api/v1/reviews/{id}/comments` | GET | 评论列表 |
| `/api/v1/reviews/{id}/comments` | POST | 发布评论 |
| `/api/v1/reviews/{id}/change-logs` | GET | 操作审计日志 |
| `/api/v1/reviews/{id}/version-compare` | GET | 版本对比 |

### 9.2 评审统计 API

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/v1/reviews/statistics/efficiency` | GET | 评审效率统计 |
| `/api/v1/reviews/statistics/quality` | GET | 评审质量统计 |
| `/api/v1/reviews/statistics/ai-accuracy` | GET | AI 审查准确率 |
| `/api/v1/reviews/statistics/bottleneck` | GET | 瓶颈节点分析 |

---

## 十、V1 vs V2 功能对照

| 功能 | V1 MVP | V2 增强 |
|------|--------|---------|
| **AI 初筛** | ✅ 合规 + 风险 + 硬规则 | ✅ + 财务 / 履约 / 异常检测 |
| **法务评审** | ✅ 复核 AI + 逐条款意见 | ✅ + 评论批注协同 |
| **财务评审** | ✅ 金额触发 + 预算核对 | ✅ + 自动对接财务系统 |
| **高管审批** | ✅ 综合决策 | ✅ + 委托审批 |
| **任务分配** | ✅ 按角色分配 | ✅ + 按专长自动匹配 |
| **冲突解决** | ✅ 手动升级仲裁 | ✅ + 自动检测冲突 |
| **版本对比** | ✅ 基础 Diff | ✅ + 条款级可视化对比 |
| **评审统计** | ✅ 效率指标 | ✅ + 质量指标 + 趋势分析 |
| **评论批注** | ❌ V2 | ✅ |
| **SLA 管理** | ✅ 固定时效 | ✅ + 可配置时效规则 |
| **评审模板** | ✅ 预设模板 | ✅ + 自定义模板 |

---

## 十一、验收标准

| 指标 | V1 目标值 | 测量方式 |
|------|---------|---------|
| **评审流程完整性** | 100% 节点覆盖 | 手动验证 5 种合同类型 |
| **任务分配准确率** | >95% | 统计 100 次分配结果 |
| **AI 准确率** | ≥87% | 抽样 50 份法务复核结果 |
| **AI 漏报率** | <10% | 法务补充风险数 / 总风险数 |
| **法务评审时效** | ≤24 小时 | 系统日志统计 |
| **评审退回率** | <20% | 退回次数 / 总评审数 |
| **系统可用率** | >99.5% | 监控平台统计 |

---

**文档维护者**：产品与技术团队  
**最后更新**：2024-01-15
