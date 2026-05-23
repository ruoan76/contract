# contract-review-pro 种子数据规划

> 版本：1.0.0 | 日期：2026-05-18  
> 来源：[CSlawyer1985/contract-review-pro](https://github.com/CSlawyer1985/contract-review-pro) V3.0（**MIT License**）  
> 编排结合：见 [../design/ai-review-design.md](../design/ai-review-design.md) §2.3

---

## 1. 用途与边界

| 项 | 说明 |
|----|------|
| **用途** | 为规则引擎、RAG、Prompt 策略、审查报告 UI 提供**可版本化的结构化种子** |
| **不用途** | 不引入 Claude Skill 运行时；不替代本平台审批/用印/归档流程 |
| **V1 目标** | 导入 **risk_labels + review_checklists（auto_detectable）+ revision_routing**；合同类型做 **映射表** 而非一次上 30 类 UI |
| **V2 目标** | 全量 risk_templates、clause_standards；按 `contract_type` 加载策略包 |

---

## 2. 源 CSV 清单与落库规划

| 源文件（上游 `data/`） | 行数级 | 建议目标表 / 文件 | V1 | 说明 |
|------------------------|--------|-------------------|-----|------|
| `contract_types.csv` | 30 | `ai_contract_type_profiles` + 映射 JSON | 映射 | 扩展审查要点，UI 仍用 [data-dictionary](../design/data-dictionary.md) 7 类 |
| `risk_labels.csv` | 15 | `ai_risk_labels` | ✅ | 报告分组、筛选、门禁关联 |
| `risk_templates.csv` | 124 | `ai_risk_templates` | 部分 | 先导入「采购/服务/借款」子集 ~30 条 |
| `review_checklists.csv` | 53 | `ai_review_checklist_items` | ✅ | `auto_detectable=true` 优先进规则引擎 |
| `clause_standards.csv` | 18 | `ai_clause_standards` | 二期 | 模板偏离检测、clause-compare |
| `revision_routing.csv` | 21 | `ai_revision_routing_rules` | ✅ | 修订建议 `revision_method` |

---

## 3. 仓库目录（已落地）

```text
backend/seeds/ai_review/
├── SOURCE.md
├── README.md
├── import_contract_review_pro.py
├── raw/                              # 上游 CSV 快照
└── generated/                        # 已生成，可提交
    ├── manifest.json                 # 计数：labels 15 / routing 21 / checklists 53
    ├── risk_labels.json
    ├── revision_routing.json
    ├── review_checklists.json
    ├── contract_type_map.json
    ├── contract_type_profiles.json   # 30 类
    ├── risk_templates.purchase.json  # 买卖+通用 14 条（V1 子集）
    └── cuad_label_bridge.json        # 15 标签 ↔ CUAD 对照（手工）
```

重新生成：

```bash
python3 backend/seeds/ai_review/import_contract_review_pro.py
```

**同步策略**：上游发版 → 更新 `raw/*.csv` → bump `SOURCE.md` → 跑脚本 → DB 迁移。

---

## 4. 合同类型映射（平台 7 类 ↔ 上游 30 类）

平台主数据仍以 `contracts.contract_type`（[data-dictionary](../design/data-dictionary.md) §1）为准；AI 层增加 **`ai_profile_key`** 指向细分类审查配置。

| 平台 `contract_type` | 默认 `ai_profile_key`（上游中文名） | 可扩展别名 |
|----------------------|-------------------------------------|------------|
| `purchase` | 买卖合同 | 商品房买卖合同、仓储合同 |
| `sales` | 买卖合同 | 产品代理（条款侧重销售方） |
| `labor` | 劳动合同 | 劳务派遣、竞业限制协议 |
| `nda` | 技术转让/服务合同 | 保密条款组合 |
| `cooperation` | 合伙合同 / 服务合同 | 特许经营、中介合同 |
| `legal-standard` | 服务合同 | 法务制式 |
| `other` | 服务合同（通用） | 用户选手工覆盖 |

**流程匹配**（`flow_type`）仍由金额/规则配置决定，**不**由 30 类直接驱动。

---

## 5. 表结构草案（与 database-design 对齐）

### 5.1 `ai_risk_labels`

| 列 | 类型 | 来源列 |
|----|------|--------|
| `id` | varchar | `label_id` L01–L15 |
| `name` | varchar | `label_name` |
| `category` | varchar | `category` |
| `gate_id` | varchar | `typical_gate` → gate_validity 等 |
| `color` | varchar | `color_code` |
| `cuad_tags` | json | 可选：手工映射 CUAD-07 等 |

### 5.2 `ai_review_checklist_items`

| 列 | 类型 | 来源列 |
|----|------|--------|
| `id` | serial | 自增 |
| `category` | varchar | `checklist_category` |
| `item` | varchar | `checklist_item` |
| `description` | text | `description` |
| `gate_id` | varchar | `gate_category` |
| `gate_priority` | int | `gate_priority` |
| `risk_level` | varchar | `risk_level` → 映射 high/medium/low |
| `auto_detectable` | bool | `auto_detectable` |
| `applicable_profiles` | json | 解析 `applicable_contracts` |

### 5.3 `ai_risk_templates`

| 列 | 类型 | 来源列 |
|----|------|--------|
| `risk_id` | varchar | `risk_id` R001… |
| `profile_key` | varchar | 解析 `contract_type` |
| `clause_name` | varchar | `clause_name` |
| `description` | text | `risk_description` |
| `legal_basis` | text | `legal_basis` |
| `suggestion` | text | `modification_suggestion` |
| `label_id` | varchar | `risk_label` |
| `revision_method` | varchar | `default_revision_method` |
| `gate_id` | varchar | `gate_id` |

### 5.4 `ai_revision_routing_rules`

| 列 | 类型 | 来源列 |
|----|------|--------|
| `issue_type` | varchar | `issue_type` |
| `default_method` | enum | track_changes / comment |
| `auto_applicable` | bool | `auto_applicable` |
| `self_check_questions` | varchar | `self_check_questions` |

---

## 6. 自动检测项（V1 规则引擎优先）

自 `review_checklists.csv` 中 `auto_detectable=True` 的项（上游标注 4 项，可扩展实现）：

| 检查项 | 实现思路 |
|--------|----------|
| 数字是否准确 | 金额大小写、阿拉伯数字与中文大写一致性 |
| 日期是否准确 | 日期格式、起算点 |
| 格式是否规范 | 编号连续性、基础排版（弱规则） |

其余 49 项走 LLM + RAG，结果仍挂 `gate_id` 与 `label_id`。

---

## 7. 导入验收标准

| 检查 | 标准 |
|------|------|
| 行数 | risk_labels=15；revision_routing≥21；checklists=53 |
| 映射 | 每条 template 的 `risk_label` 均能 join `ai_risk_labels` |
| API | `GET /api/v1/ai-review/{id}/result` 返回含 `label_id`、`gate_id`、`revision_method` |
| 原型 | `ai-review` 筛选器增加「风险标签」下拉（15 项） |

---

## 8. 许可与署名

- 协议：**MIT**；允许改编与商用，需保留版权声明。  
- 建议在 `backend/seeds/ai_review/SOURCE.md` 中写明：  
  `Data derived from contract-review-pro © 陈石 / CSlawyer1985, MIT License.`  
- 本项目 **CUAD** 标签体系保留，与 15 标签 **双轨展示**（见 ai-review-design §2.3）。

---

## 9. 相关文档

- [ai-review-design.md §2.3](../design/ai-review-design.md) — 编排与 Session 结合  
- [data-dictionary.md](../design/data-dictionary.md) — 平台枚举  
- [field-dictionary.md](../design/field-dictionary.md) — 审查结果 API 字段（待扩展）
