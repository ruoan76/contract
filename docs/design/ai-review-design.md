# AI 合同审查设计文档

> ⚠️ **范围说明（V1）**：本文档为 **开发期技术蓝图**（Skill 编排、RAG、Chroma 等），**不等于**当前高保真原型 `prototype/index.html` 的实现范围。  
> V1 原型/产品承诺：五维度审查报告、置信度展示、规则命中文案、法务误报/漏报标记。完整能力按 Sprint 自 [DESIGN_STATUS.md](./DESIGN_STATUS.md) 分期落地。  
> **外部方法论**：种子数据与编排参考 [contract-review-pro V3.0](https://github.com/CSlawyer1985/contract-review-pro)（MIT），详见 §2.3 与 [contract-review-pro-seeds.md](../reference/contract-review-pro-seeds.md)。

## 🎯 设计目标

利用大模型技术（Qwen3.6）实现合同内容智能审查，识别法律风险、财务风险、履约风险，辅助法务人员快速判断合同质量。

## 🏗️ 整体架构

### 1.1 架构定位
AI 合同审查模块不仅是“大模型调用”，而是一个**可配置、可扩展、多技能协作的智能体系统**。通过 **Skill 编排架构** 与 **策略驱动配置**，实现审查能力的灵活组合与热更新。

### 1.2 核心设计原则
| 原则 | 说明 |
|------|------|
| **Skill 化** | 将审查能力拆解为原子化技能（解析、合规、风险、财务等），由编排器统一调度 |
| **策略驱动** | 审查规则、阈值、Prompt 模板通过 YAML/JSON 配置，业务人员可配，无需改代码 |
| **RAG 增强** | 结合向量检索与规则引擎，解决大模型幻觉，确保审查依据准确 |
| **推理链 (CoT)** | 强制模型展示思考过程，提升审查可解释性与准确率 |
| **自我反思** | 模型生成结果后进行二次校验，降低误报率 |

### 1.3 逻辑架构图
```
┌─────────────────────────────────────────────────────────────┐
│                    AI 合同审查流程                            │
│                                                             │
│  合同文档 → 文本提取 → 分段解析 → 策略匹配 → 技能编排 → 报告  │
│    ↑           ↑           ↑          ↑         ↑          │
│  上传/导入   PDF/Word     条款拆分    合同类型   Skill 调度   │
│                                         ↓                 │
│                                  ┌──────────────┐         │
│                                  │ 审查策略配置  │         │
│                                  │ (YAML/JSON)  │         │
│                                  └──────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   Skill 编排层 (Orchestrator)                 │
│                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │解析 Skill│ │合规 Skill│ │风险 Skill│ │财务 Skill│       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                    │
│  │履约 Skill│ │异常 Skill│ │报告 Skill│                    │
│  └──────────┘ └──────────┘ └──────────┘                    │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   底层能力层                                  │
│  Qwen3.6 (LLM) │ Chroma (RAG) │ RuleEngine (规则引擎)       │
│  CoT (推理链)  │ Self-Correction (反思) │ Structured Output  │
└─────────────────────────────────────────────────────────────┘
```

## 📋 审查维度与 Skill 分类

### 2.1 Skill 技能分类 (Skill Taxonomy)

| 技能类别 | Skill ID | 职责 | 技术实现 |
|---------|----------|------|---------|
| **基础解析** | `parser.contract_parser` | 提取条款、识别主体、金额、日期 | NLP 实体识别 (NER) |
| **合规审查** | `review.compliance_check` | 检查强制性规定、格式条款 | RAG (法规库) + LLM 语义比对 |
| **风险审查** | `review.risk_assessment` | 违约责任、管辖、解除权 | 规则引擎 + LLM 风险评分 |
| **财务审查** | `review.finance_check` | 付款条件、税务、保证金 | 正则提取 + 阈值校验 |
| **履约审查** | `review.performance_check` | 交付周期、验收标准、质保 | LLM 语义完整性检查 |
| **异常检测** | `review.anomaly_detection` | 矛盾条款、隐藏风险、偏离模板 | 向量相似度 + 逻辑冲突检测 |
| **综合报告** | `report.generator` | 汇总结果、生成报告、修订建议 | LLM 摘要 + 模板渲染 |

### 2.2 审查维度与 Skill 映射

| 审查维度 | 对应 Skill | 检查内容 | 判断标准 |
|---------|-----------|---------|---------|
| **合规性审查** | `review.compliance_check` | 主体资格、经营范围、强制性规定 | 违反强制性规定 → 直接高风险 |
| **风险条款识别** | `review.risk_assessment` | 违约责任、管辖约定、解除条件 | 赔偿无上限 → 高风险 |
| **财务审查** | `review.finance_check` | 付款条件、价格条款、税务条款 | 预付款>50% → 高风险 |
| **履约能力评估** | `review.performance_check` | 交付周期、质量标准、验收条件 | 验收条件模糊 → 中风险 |
| **异常检测** | `review.anomaly_detection` | 矛盾条款、隐藏风险、缺失条款 | 条款矛盾 → 高风险 |

### 2.3 参考 contract-review-pro V3.0 编排与结合

上游项目为**律师侧审核 Skill**（Python + CSV 知识库 + 7 步 Session），本平台为**企业合同生命周期 + Qwen 编排**。结合方式：**采纳其方法论与种子数据，不移植 Claude 运行时**。

#### 2.3.1 架构对照

| 上游（contract-review-pro） | 本平台 | 结合策略 |
|----------------------------|--------|----------|
| `ContractReviewSession` 7 步 | `AiReviewSession`（FastAPI 状态机） | 映射为审查子流程，**不占用**审批流节点 |
| 5 类门禁 `gate_*` | 编排 **Phase 0**（效力/主体优先） | 在五维度 Skill 之前执行 |
| 15 `risk_labels` | 报告二级分类 + 筛选 | 与 CUAD 标签 **双轨**（见下） |
| 六维度风险评价 | `ai_review_issues` 扩展字段 | V1 存 3 维，V2 满六维 |
| `revision_routing.csv` | `revision_method` | 对接 `revision-workspace` / 法务批注 |
| 终稿三件套 `.docx` | 导出服务 | V2：`export/opinion`、`export/annotated` |
| `ClientConfig` | `counterparty` + 集团策略表 | V2：相对方级 YAML 策略 |

#### 2.3.2 审查 Session 状态机（结合 7 步）

在现有「上传 → 解析 → 编排 → 报告」之上，增加**有状态 Session**（与 [workflow-vs-review.md](./workflow-vs-review.md) 评审轨并行）：

```text
S0  client_context      # 相对方/集团策略（可选，未命中不套用）
S1  review_state        # 元数据：合同号、类型、立场、flow_type
S2  read_through        # 通读摘要：主体/标的/价款/交付/违约/争议（禁止跳过）
S3  validity_gates      # gate_validity + gate_subject（53 项清单中门禁项）
S4  issue_backlog       # 待研究法律问题 + risk_label
S5  knowledge_research  # RAG：法规库 + 种子 template 法律依据
S6  clause_review       # 逐条：正反两面 + 五维度 Skills + 15 标签
S7  clause_extract      # 可选：值得入库条款候选（写模板库队列）
     → aggregate_report → 法务复核（原型：误报/漏报）
```

**硬约束（写入 Orchestrator Guardrail）**：

1. 禁止跳过 S2 通读直接出意见  
2. 禁止跳过 S3 效力/主体门禁  
3. 禁止无 `legal_basis`（法规库或种子 template）的高风险定论  
4. 禁止编造法条  

#### 2.3.3 五类门禁与五维度 Skill 的执行顺序

```text
Phase 0  门禁层（CSV: review_checklists + contract_types.review_points）
         ├─ gate_validity   → parser + 规则 + LLM
         ├─ gate_subject
         ├─ gate_clause     → 五维度 Skills 主战场
         ├─ gate_consistency → anomaly_detection 加权
         └─ gate_output     → report.generator

Phase 1  五维度 Skills（现有 2.2 映射不变）
Phase 2  聚合：按 risk_label 分组 + 按 risk_level 排序
Phase 3  revision_router：为每条 issue 填 revision_method
```

门禁失败项：**默认高风险且不可被五维度「降权」**，须法务确认后方能标记误报。

#### 2.3.4 三套标签体系如何共存

| 体系 | 用途 | 来源 |
|------|------|------|
| **五维度** | 编排调度、雷达图大类 | 本文档 §2.2 |
| **15 risk_labels** | 报告分组、统计、门禁 | 种子 `risk_labels.csv` |
| **CUAD** | 国际化对照、原型筛选 | 原型 / archive 整合 |

单条 `ai_review_issue` 建议结构：

```json
{
  "dimension": "finance_check",
  "label_id": "L06",
  "cuad_code": "CUAD-07",
  "gate_id": "gate_clause",
  "risk_level": "medium",
  "confidence": 0.65,
  "revision_method": "comment",
  "legal_basis": "民法典第585条",
  "exposure_summary": "预付款40%超内部制度30%"
}
```

#### 2.3.5 种子数据（CSV → 本平台）

完整落库规划见 **[contract-review-pro-seeds.md](../reference/contract-review-pro-seeds.md)**。

| 阶段 | 导入内容 | 消费方 |
|------|----------|--------|
| **Sprint AI-1** | `risk_labels` + `revision_routing` + `auto_detectable` 清单 | 规则引擎、报告 UI |
| **Sprint AI-2** | `risk_templates` 采购/服务子集 | RAG few-shot、硬规则 |
| **Sprint AI-3** | `clause_standards` + 30 类 `contract_types` 映射 | clause-compare、策略 YAML |

已落地目录：`backend/seeds/ai_review/`（`import_contract_review_pro.py` → `generated/*.json`，见 `manifest.json`）。

#### 2.3.6 与产品页面的绑定

| 页面 | 结合点 |
|------|--------|
| `ai-review` | 顶部 **效力门禁摘要**；筛选：15 标签 + CUAD；置信度旁展示 `label_id` |
| `review-workspace` | 正反三面折叠；采纳建议时读 `revision_method` |
| `revision-workspace` | track_changes 类建议 →「接受修改」；comment 类 → 批注框 |
| `clause-compare` | `clause_standards` 偏离度 |
| `config` | 阈值 + 按 `ai_profile_key` 启用 checklist 子集 |

#### 2.3.7 Policy YAML 扩展示例

```yaml
# policies/purchase.yaml — 在现有 policy 上增加
ai_profile_key: 买卖合同
review_session:
  skip_steps: []          # 禁止跳过 S2/S3
  depth: standard         # quick | standard | deep
gates:
  required: [gate_validity, gate_subject, gate_clause]
seed_packs:
  - risk_labels
  - review_checklists
  - risk_templates.purchase
revision_router: default   # 加载 revision_routing 表
```

#### 2.3.8 分期与原型差距

| 能力 | 原型现状 | 开发期目标 |
|------|----------|------------|
| 五维度报告 | ✅ | 保持 |
| 15 标签 / 门禁摘要 | ❌ | Sprint AI-1 |
| Session 七步（可观测） | ❌ | 审查任务时间线 API |
| 六维度评价 | 部分（置信度） | Sprint AI-2 |
| docx 三件套 | Toast 示意 | V2 导出服务 |

---

## 🔧 技术实现

### 1. 文本提取与预处理

```python
# backend/app/services/ai_review/text_extractor.py

class TextExtractor:
    """合同文本提取器"""
    
    def extract(self, file_path: str) -> str:
        """支持 PDF/Word/图片 文本提取"""
        ext = file_path.split('.')[-1].lower()
        if ext == 'pdf':
            return self._extract_pdf(file_path)
        elif ext in ['doc', 'docx']:
            return self._extract_docx(file_path)
        elif ext in ['jpg', 'png']:
            return self._extract_ocr(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {ext}")
    
    def _extract_pdf(self, path: str) -> str:
        """PDF 文本提取（支持扫描版 OCR）"""
        import fitz  # PyMuPDF
        doc = fitz.open(path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    
    def _extract_docx(self, path: str) -> str:
        """Word 文档文本提取"""
        import docx
        doc = docx.Document(path)
        return "\n".join([p.text for p in doc.paragraphs])
    
    def _extract_ocr(self, path: str) -> str:
        """图片 OCR 识别"""
        import easyocr
        reader = easyocr.Reader(['ch_sim', 'en'])
        result = reader.readtext(path)
        return " ".join([r[1] for r in result])
```

### 2. 条款分段与解析

```python
# backend/app/services/ai_review/clause_parser.py

import re
from typing import List, Dict

class ClauseParser:
    """合同条款解析器"""
    
    def parse(self, text: str) -> List[Dict]:
        """将合同文本解析为结构化条款"""
        clauses = []
        
        # 按章节标题分段
        sections = self._split_sections(text)
        
        for section in sections:
            clause = {
                "title": section["title"],
                "content": section["content"],
                "type": self._classify_clause(section["title"]),
                "risk_level": "pending",
            }
            clauses.append(clause)
        
        return clauses
    
    def _split_sections(self, text: str) -> List[Dict]:
        """按章节标题分割文本"""
        # 匹配 "第X章"、"第X条"、"一、"、"1." 等标题格式
        pattern = r'(第[一二三四五六七八九十百千]+[章节条]|[一二三四五六七八九十]+[、.]|\d+[.、])'
        sections = re.split(pattern, text)
        
        result = []
        for i in range(0, len(sections)-1, 2):
            result.append({
                "title": sections[i].strip(),
                "content": sections[i+1].strip()
            })
        return result
    
    def _classify_clause(self, title: str) -> str:
        """条款分类"""
        keywords = {
            "违约责任": ["违约", "责任", "赔偿"],
            "付款条件": ["付款", "支付", "结算"],
            "保密条款": ["保密", "机密", "秘密"],
            "知识产权": ["知识产权", "专利", "版权"],
            "管辖约定": ["管辖", "仲裁", "诉讼"],
            "解除条款": ["解除", "终止", "撤销"],
        }
        
        for category, words in keywords.items():
            if any(word in title for word in words):
                return category
        return "其他"
```

### 3. AI 审查引擎（核心）

```python
# backend/app/services/ai_review/ai_engine.py

from openai import OpenAI
import json

class AIReviewEngine:
    """AI 合同审查引擎"""
    
    def __init__(self):
        # 连接本地 Qwen3.6 模型
        self.client = OpenAI(
            base_url="http://localhost:8000/v1",  # MLX 本地服务
            api_key="local"
        )
        self.model = "mlx-community/Qwen3.6-35B-A3B-4bit"
    
    async def review_contract(self, clauses: List[Dict]) -> Dict:
        """合同审查主流程"""
        review_results = []
        total_risk_score = 0
        
        for clause in clauses:
            # 逐条款审查
            result = await self._review_clause(clause)
            review_results.append(result)
            total_risk_score += result["risk_score"]
        
        # 综合评估
        overall_assessment = await self._overall_assessment(clauses, review_results)
        
        return {
            "clauses": review_results,
            "overall": overall_assessment,
            "risk_level": self._calculate_risk_level(total_risk_score),
            "risk_score": total_risk_score,
            "suggestions": self._generate_suggestions(review_results),
        }
    
    async def _review_clause(self, clause: Dict) -> Dict:
        """单条款审查"""
        prompt = self._build_review_prompt(clause)
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # 低温度保证稳定性
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return {
            "clause": clause,
            "risk_level": result.get("risk_level", "low"),
            "risk_score": result.get("risk_score", 0),
            "issues": result.get("issues", []),
            "suggestions": result.get("suggestions", []),
            "legal_basis": result.get("legal_basis", ""),
        }
    
    def _build_review_prompt(self, clause: Dict) -> str:
        """构建审查提示词"""
        return f"""
请审查以下合同条款，从以下维度评估风险：

【条款标题】{clause['title']}
【条款内容】{clause['content']}
【条款类型】{clause['type']}

请按以下 JSON 格式返回审查结果：
{{
    "risk_level": "high|medium|low",
    "risk_score": 0-100,
    "issues": [
        {{
            "type": "风险类型",
            "description": "风险描述",
            "severity": "high|medium|low",
            "legal_basis": "法律依据"
        }}
    ],
    "suggestions": ["修改建议1", "修改建议2"],
    "legal_basis": "主要法律依据"
}}

审查要点：
1. 是否违反法律强制性规定
2. 是否存在不公平条款
3. 是否存在模糊表述
4. 是否存在权利失衡
5. 是否存在履约风险
"""
    
    def _get_system_prompt(self) -> str:
        """系统提示词"""
        return """
你是一个专业的合同审查 AI 助手，具有丰富的中国法律知识和合同审查经验。
你的任务是：
1. 识别合同中的法律风险点
2. 评估风险等级（高/中/低）
3. 提供具体的修改建议
4. 引用相关法律法规作为依据

审查原则：
- 客观公正，不偏袒任何一方
- 重点关注高风险条款
- 建议具体可操作
- 引用法律条文准确
"""
    
    def _calculate_risk_level(self, total_score: float) -> str:
        """计算整体风险等级"""
        if total_score >= 80:
            return "high"
        elif total_score >= 50:
            return "medium"
        else:
            return "low"
    
    def _generate_suggestions(self, results: List[Dict]) -> List[str]:
        """生成综合修改建议"""
        suggestions = []
        for result in results:
            suggestions.extend(result.get("suggestions", []))
        return list(set(suggestions))  # 去重
```

### 4. 规则引擎（辅助 AI）

```python
# backend/app/services/ai_review/rule_engine.py

import re
from typing import List, Dict

class RuleEngine:
    """规则引擎 - 补充 AI 审查"""
    
    def __init__(self):
        self.rules = self._load_rules()
    
    def _load_rules(self) -> List[Dict]:
        """加载审查规则"""
        return [
            {
                "id": "R001",
                "name": "违约金上限检查",
                "pattern": r"违约金.*?([0-9]+)%",
                "check": lambda m: int(m.group(1)) > 30,
                "risk_level": "high",
                "message": "违约金超过 30%，可能过高",
            },
            {
                "id": "R002",
                "name": "管辖法院检查",
                "pattern": r"管辖.*?法院",
                "check": lambda m: "甲方" not in m.group(0),
                "risk_level": "medium",
                "message": "建议约定甲方所在地法院管辖",
            },
            {
                "id": "R003",
                "name": "保密期限检查",
                "pattern": r"保密.*?([0-9]+).*?年",
                "check": lambda m: int(m.group(1)) > 3,
                "risk_level": "medium",
                "message": "保密期限超过 3 年，建议评估合理性",
            },
            {
                "id": "R004",
                "name": "预付款比例检查",
                "pattern": r"预付款.*?([0-9]+)%",
                "check": lambda m: int(m.group(1)) > 50,
                "risk_level": "high",
                "message": "预付款比例超过 50%，存在资金风险",
            },
        ]
    
    def apply_rules(self, text: str) -> List[Dict]:
        """应用规则检查"""
        violations = []
        
        for rule in self.rules:
            match = re.search(rule["pattern"], text)
            if match and rule["check"](match):
                violations.append({
                    "rule_id": rule["id"],
                    "rule_name": rule["name"],
                    "risk_level": rule["risk_level"],
                    "message": rule["message"],
                    "matched_text": match.group(0),
                })
        
        return violations
```

### 5. 风险评级模型

```python
# backend/app/services/ai_review/risk_scorer.py

class RiskScorer:
    """风险评分器"""
    
    def __init__(self):
        self.weights = {
            "compliance": 0.30,    # 合规性
            "financial": 0.25,     # 财务
            "performance": 0.20,   # 履约
            "legal": 0.15,         # 法律
            "operational": 0.10,   # 经营
        }
    
    def calculate_overall_risk(self, scores: Dict) -> Dict:
        """计算综合风险评分"""
        weighted_score = sum(
            scores.get(key, 0) * weight 
            for key, weight in self.weights.items()
        )
        
        return {
            "total_score": round(weighted_score, 2),
            "risk_level": self._get_risk_level(weighted_score),
            "breakdown": scores,
            "recommendation": self._get_recommendation(weighted_score),
        }
    
    def _get_risk_level(self, score: float) -> str:
        if score >= 80:
            return "高风险 - 建议重新谈判或拒绝签署"
        elif score >= 60:
            return "中风险 - 建议修改关键条款后签署"
        elif score >= 40:
            return "低风险 - 可签署，注意一般风险点"
        else:
            return "极低风险 - 建议签署"
    
    def _get_recommendation(self, score: float) -> str:
        recommendations = {
            80: "1. 立即暂停签署流程\n2. 法务部门介入审查\n3. 与对方重新谈判关键条款\n4. 评估替代方案",
            60: "1. 修改高风险条款\n2. 补充保障措施\n3. 法务复核后签署\n4. 加强履约监控",
            40: "1. 注意一般风险点\n2. 按标准流程签署\n3. 定期履约检查",
            0: "1. 按标准流程签署\n2. 正常履约管理",
        }
        
        for threshold in [80, 60, 40, 0]:
            if score >= threshold:
                return recommendations[threshold]
```

## 📊 审查报告输出

```json
{
    "contract_id": "CTR-2024-001",
    "review_id": "REV-2024-001",
    "review_time": "2024-01-15 10:30:00",
    "overall_risk": {
        "level": "medium",
        "score": 65.5,
        "recommendation": "中风险 - 建议修改关键条款后签署"
    },
    "clause_reviews": [
        {
            "clause_title": "违约责任",
            "risk_level": "high",
            "risk_score": 85,
            "issues": [
                {
                    "type": "赔偿上限",
                    "description": "未设置赔偿上限，存在无限责任风险",
                    "severity": "high",
                    "legal_basis": "《民法典》第 584 条"
                }
            ],
            "suggestions": [
                "建议增加赔偿上限条款，不超过合同总额的 30%",
                "建议明确间接损失不承担赔偿责任"
            ]
        }
    ],
    "rule_violations": [
        {
            "rule_id": "R001",
            "message": "违约金超过 30%，可能过高",
            "risk_level": "high"
        }
    ],
    "summary": {
        "total_clauses": 15,
        "high_risk_clauses": 3,
        "medium_risk_clauses": 5,
        "low_risk_clauses": 7,
        "total_issues": 12,
        "critical_issues": 3
    }
}
```

## 🔄 审查流程

```
1. 上传合同文档
   ↓
2. 文本提取（PDF/Word/图片 OCR）
   ↓
3. 条款分段与分类
   ↓
4. 规则引擎辅助检查（硬规则优先）
   ↓
5. 法规知识库检索（语义匹配相关法规）
   ↓
6. AI 逐条款审查（Qwen3.6 + 知识库上下文）
   ↓
7. 风险评分与评级
   ↓
8. 生成审查报告
   ↓
9. 法务人工复核
   ↓
10. 反馈修改建议
   ↓
11. 合同修订后重新审查
```

## 📚 法规知识库基座（V1 必做）

### 1. 设计目标
内置 50 条核心法规条款，作为 AI 审查的“事实依据”，解决大模型幻觉问题，提升审查准确率至 80%+。

### 2. 知识库结构
```python
class LawArticle(BaseModel):
    id: str                          # 法规 ID
    law_name: str                    # 法规名称（如《民法典》）
    chapter: str                     # 章节
    article_number: str              # 条款号（如第 584 条）
    content: str                     # 条款原文
    summary: str                     # 条款摘要（用于语义检索）
    tags: List[str]                  # 标签（违约/赔偿/管辖/保密等）
    risk_scenarios: List[str]        # 适用风险场景
    effective_date: date             # 生效日期
    status: str                      # 状态（effective/abolished）
```

### 3. V1 核心法规清单（50 条示例）

| 法规名称 | 条款号 | 标签 | 风险场景 |
|---------|--------|------|---------|
| 《民法典》 | 第 496 条 | 格式条款 | 免除己方责任、加重对方责任 |
| 《民法典》 | 第 584 条 | 违约赔偿 | 赔偿上限、间接损失 |
| 《民法典》 | 第 585 条 | 违约金 | 违约金过高/过低调整 |
| 《民法典》 | 第 686 条 | 保证担保 | 一般保证 vs 连带责任 |
| 《民法典》 | 第 705 条 | 租赁期限 | 租赁超 20 年无效 |
| 《公司法》 | 第 16 条 | 对外担保 | 公司对外担保需董事会/股东会决议 |
| 《电子签名法》 | 第 13 条 | 电子签章 | 可靠电子签名条件 |
| 《劳动合同法》 | 第 19 条 | 试用期 | 试用期超期 |
| 《招标投标法》 | 第 46 条 | 招投标 | 阴阳合同/背离实质性内容 |
| 《数据安全法》 | 第 21 条 | 数据合规 | 跨境数据传输、敏感数据 |
| ... | ... | ... | ... |

### 4. 知识库检索与注入
```python
class KnowledgeBaseRetriever:
    """法规知识库检索器"""
    
    def __init__(self):
        self.vector_db = Chroma(persist_directory="./law_kb")
        self.embedding_model = SentenceTransformer("shibing624/text2vec-base-chinese")
    
    def retrieve(self, clause_text: str, top_k: int = 5) -> List[LawArticle]:
        """语义检索相关法规"""
        query_emb = self.embedding_model.encode(clause_text)
        results = self.vector_db.similarity_search(query_emb, k=top_k)
        return [LawArticle(**r.metadata) for r in results]
    
    def build_prompt_context(self, articles: List[LawArticle]) -> str:
        """构建 Prompt 上下文"""
        context = "【参考法规】\n"
        for art in articles:
            context += f"- {art.law_name} 第{art.article_number}条：{art.summary}\n"
        return context
```

### 5. AI 审查 Prompt 模板（V1 增强版）
```
你是一个专业的合同审查 AI 助手。请基于以下【参考法规】审查合同条款。

【参考法规】
{knowledge_base_context}

【条款内容】
{clause_content}

请按以下 JSON 格式返回审查结果：
{{
    "risk_level": "high|medium|low",
    "risk_score": 0-100,
    "issues": [
        {{
            "type": "风险类型",
            "description": "风险描述",
            "severity": "high|medium|low",
            "legal_basis": "必须引用【参考法规】中的具体条款"
        }}
    ],
    "suggestions": ["修改建议1", "修改建议2"],
}}

审查原则：
1. 优先引用【参考法规】中的条款作为依据
2. 若条款无明确法规依据，标记为“建议优化”，不标记为高风险
3. 严禁编造法规条款号
```

## 🔧 灵活配置设计 (Policy-Driven Configuration)

### 1. 策略配置示例 (policy.yaml)

通过 **YAML/JSON 策略文件** 实现审查规则的灵活配置，支持按合同类型、行业、风险偏好定制。

```yaml
# 采购合同审查策略
contract_type: purchase
risk_appetite: moderate  # conservative | moderate | aggressive

# 启用的技能
active_skills:
  - parser.contract_parser
  - review.compliance_check
  - review.risk_assessment
  - review.finance_check
  - review.performance_check
  - review.anomaly_detection

# 规则配置
rules:
  # 硬规则 (规则引擎)
  hard_rules:
    - id: R001
      name: 违约金上限
      condition: "penalty_rate > 0.30"
      risk_level: high
      message: "违约金比例超过 30%，可能过高"
      
    - id: R002
      name: 预付款比例
      condition: "advance_payment > 0.50"
      risk_level: medium
      message: "预付款比例超过 50%，存在资金风险"
      
    - id: R003
      name: 管辖法院
      condition: "jurisdiction != '甲方所在地'"
      risk_level: high
      message: "建议约定甲方所在地法院管辖"

  # 软规则 (LLM 语义审查)
  soft_rules:
    - id: S001
      name: 违约责任公平性
      prompt_template: "review/prompts/penalty_fairness.j2"
      risk_level: "llm_assess"
      
    - id: S002
      name: 验收标准明确性
      prompt_template: "review/prompts/acceptance_clarity.j2"
      risk_level: "llm_assess"

# 知识库配置
knowledge_base:
  - source: "law_articles"
    tags: ["civil_code", "contract_law"]
    top_k: 5
    
# 模板配置
template_check:
  enabled: true
  template_id: "PUR-001"
  deviation_threshold: 0.15  # 偏离度阈值
```

### 2. 配置管理后台
提供可视化界面，允许法务/业务人员：
- **调整风险偏好**：保守/适中/激进（影响阈值和审查严格度）
- **启用/禁用技能**：按需加载审查维度
- **修改硬规则阈值**：如违约金上限从 30% 改为 25%
- **管理软规则 Prompt**：编辑 LLM 审查提示词

## 🤖 大模型技术应用 (LLM Technology Stack)

### 1. RAG (检索增强生成) - 解决幻觉
结合向量检索与规则引擎，确保审查依据准确。

```python
class LegalRAGRetriever:
    """法律 RAG 检索器"""
    
    def __init__(self):
        self.vector_db = Chroma(persist_directory="./law_kb")
        self.embedding_model = SentenceTransformer("shibing624/text2vec-base-chinese")
    
    def retrieve(self, clause_text: str, policy: dict) -> List[LawArticle]:
        """语义检索相关法规"""
        query_emb = self.embedding_model.encode(clause_text)
        
        # 根据策略过滤标签
        filter_tags = policy.get("knowledge_base", {}).get("tags", [])
        
        results = self.vector_db.similarity_search(
            query_emb, 
            k=policy.get("knowledge_base", {}).get("top_k", 5),
            filter={"tags": {"$in": filter_tags}}
        )
        
        return [LawArticle(**r.metadata) for r in results]
```

### 2. CoT (Chain of Thought) - 提升推理能力
要求模型展示思考过程，而非直接给结论。

**Prompt 模板：**
```text
请审查以下合同条款，按以下步骤思考：

1. **条款解析**：提取条款中的关键要素（主体、义务、违约责任、期限等）
2. **合规检查**：对照【参考法规】，检查是否违反强制性规定
3. **风险评估**：评估条款是否公平，是否存在单方加重责任
4. **结论生成**：给出风险等级和修改建议

【条款内容】
{clause_text}

请以 JSON 格式返回审查结果。
```

### 3. Few-Shot Learning - 提升一致性
提供正反例，让模型学习审查标准。

**Prompt 模板：**
```text
请审查以下合同条款。参考以下示例的审查标准：

【示例 1 - 高风险】
条款："乙方违约需赔偿甲方一切损失，包括但不限于直接损失、间接损失、利润损失等。"
审查结果：
- 风险等级：高
- 风险描述：未设置赔偿上限，且包含间接损失，责任过重
- 修改建议：建议增加赔偿上限，不超过合同总额的 30%，并排除间接损失

【示例 2 - 低风险】
条款："任何一方违约，应赔偿守约方因此遭受的直接损失，赔偿总额不超过合同总额的 20%。"
审查结果：
- 风险等级：低
- 风险描述：条款公平，设置了赔偿上限，符合行业标准
- 修改建议：无

【待审查条款】
{clause_text}

请给出审查结果。
```

### 4. Structured Output - 结构化输出
强制模型输出 JSON Schema，便于下游解析和展示。

**JSON Schema：**
```json
{
  "type": "object",
  "properties": {
    "risk_level": {"type": "string", "enum": ["high", "medium", "low"]},
    "risk_score": {"type": "integer", "minimum": 0, "maximum": 100},
    "issues": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {"type": "string"},
          "description": {"type": "string"},
          "severity": {"type": "string", "enum": ["high", "medium", "low"]},
          "legal_basis": {"type": "string"},
          "suggestion": {"type": "string"}
        },
        "required": ["type", "description", "severity"]
      }
    }
  },
  "required": ["risk_level", "risk_score", "issues"]
}
```

### 5. Self-Correction (自我反思) - 提升准确率
模型生成结果后，再进行一次自我检查。

```python
async def self_correct(self, initial_result: dict, clause_text: str) -> dict:
    """自我反思"""
    prompt = f"""
    你刚刚审查了以下合同条款：
    {clause_text}
    
    你的初步审查结果：
    {json.dumps(initial_result, ensure_ascii=False)}
    
    请检查你的审查结果：
    1. 风险等级是否合理？
    2. 法律依据是否准确？
    3. 修改建议是否可操作？
    
    如果需要修正，请输出修正后的结果。
    """
    
    response = await self.llm.call(prompt)
    return json.loads(response)
```

## 🔄 审查流程设计 (Review Pipeline)

```
1. 上传合同
   ↓
2. 文本提取（PDF/Word/OCR）
   ↓
3. 条款分段与分类（ClauseParser）
   ↓
4. 策略匹配（PolicyMatcher）
   - 根据合同类型加载审查策略
   - 确定启用的 Skills 和规则
   ↓
5. 技能编排执行（Orchestrator）
   ├─ 硬规则检查（RuleEngine）→ 快速拦截
   ├─ 软规则检查（LLM + RAG）→ 语义审查
   ├─ 模板偏离检测（DeviationDetector）→ 对比分析
   └─ 异常检测（AnomalyDetector）→ 矛盾/隐藏风险
   ↓
6. 结果聚合（Aggregator）
   - 合并各 Skill 结果
   - 计算综合风险评分
   - 生成审查报告
   ↓
7. 法务人工复核
   - 确认/修正 AI 结论
   - 反馈闭环（用于模型优化）
```

## 📚 法规知识库基座（V1 必做）

### 1. 设计目标
内置 50 条核心法规条款，作为 AI 审查的“事实依据”，解决大模型幻觉问题，提升审查准确率至 80%+。

### 2. 知识库结构
```python
class LawArticle(BaseModel):
    id: str                          # 法规 ID
    law_name: str                    # 法规名称（如《民法典》）
    chapter: str                     # 章节
    article_number: str              # 条款号（如第 584 条）
    content: str                     # 条款原文
    summary: str                     # 条款摘要（用于语义检索）
    tags: List[str]                  # 标签（违约/赔偿/管辖/保密等）
    risk_scenarios: List[str]        # 适用风险场景
    effective_date: date             # 生效日期
    status: str                      # 状态（effective/abolished）
```

### 3. V1 核心法规清单（50 条示例）

| 法规名称 | 条款号 | 标签 | 风险场景 |
|---------|--------|------|---------|
| 《民法典》 | 第 496 条 | 格式条款 | 免除己方责任、加重对方责任 |
| 《民法典》 | 第 584 条 | 违约赔偿 | 赔偿上限、间接损失 |
| 《民法典》 | 第 585 条 | 违约金 | 违约金过高/过低调整 |
| 《民法典》 | 第 686 条 | 保证担保 | 一般保证 vs 连带责任 |
| 《民法典》 | 第 705 条 | 租赁期限 | 租赁超 20 年无效 |
| 《公司法》 | 第 16 条 | 对外担保 | 公司对外担保需董事会/股东会决议 |
| 《电子签名法》 | 第 13 条 | 电子签章 | 可靠电子签名条件 |
| 《劳动合同法》 | 第 19 条 | 试用期 | 试用期超期 |
| 《招标投标法》 | 第 46 条 | 招投标 | 阴阳合同/背离实质性内容 |
| 《数据安全法》 | 第 21 条 | 数据合规 | 跨境数据传输、敏感数据 |
| ... | ... | ... | ... |

### 4. 知识库检索与注入
```python
class KnowledgeBaseRetriever:
    """法规知识库检索器"""
    
    def __init__(self):
        self.vector_db = Chroma(persist_directory="./law_kb")
        self.embedding_model = SentenceTransformer("shibing624/text2vec-base-chinese")
    
    def retrieve(self, clause_text: str, top_k: int = 5) -> List[LawArticle]:
        """语义检索相关法规"""
        query_emb = self.embedding_model.encode(clause_text)
        results = self.vector_db.similarity_search(query_emb, k=top_k)
        return [LawArticle(**r.metadata) for r in results]
    
    def build_prompt_context(self, articles: List[LawArticle]) -> str:
        """构建 Prompt 上下文"""
        context = "【参考法规】\n"
        for art in articles:
            context += f"- {art.law_name} 第{art.article_number}条：{art.summary}\n"
        return context
```

### 5. AI 审查 Prompt 模板（V1 增强版）
```
你是一个专业的合同审查 AI 助手。请基于以下【参考法规】审查合同条款。

【参考法规】
{knowledge_base_context}

【条款内容】
{clause_content}

请按以下 JSON 格式返回审查结果：
{{
    "risk_level": "high|medium|low",
    "risk_score": 0-100,
    "issues": [
        {{
            "type": "风险类型",
            "description": "风险描述",
            "severity": "high|medium|low",
            "legal_basis": "必须引用【参考法规】中的具体条款"
        }}
    ],
    "suggestions": ["修改建议1", "修改建议2"],
}}

审查原则：
1. 优先引用【参考法规】中的条款作为依据
2. 若条款无明确法规依据，标记为“建议优化”，不标记为高风险
3. 严禁编造法规条款号
```

## 🔧 核心 Skill 实现示例

### 1. 合规审查 Skill (`review.compliance_check`)

```python
class ComplianceCheckSkill:
    """合规审查技能"""
    
    def __init__(self, rag_retriever, llm_client):
        self.rag = rag_retriever
        self.llm = llm_client
    
    async def execute(self, clause: dict, policy: dict) -> dict:
        # 1. 检索相关法规
        laws = self.rag.retrieve(clause["content"], policy)
        
        # 2. 构建 Prompt
        prompt = self._build_prompt(clause, laws)
        
        # 3. 调用 LLM
        response = await self.llm.call(prompt, schema=ComplianceSchema)
        
        # 4. 自我反思
        if policy.get("self_correction", False):
            response = await self._self_correct(response, clause["content"])
        
        return {
            "skill_id": "review.compliance_check",
            "clause": clause,
            "result": response,
            "laws_cited": [law.id for law in laws]
        }
    
    def _build_prompt(self, clause: dict, laws: list) -> str:
        laws_text = "\n".join([f"- {law.law_name} 第{law.article_number}条：{law.summary}" for law in laws])
        return f"""
        请审查以下合同条款的合规性。
        
        【参考法规】
        {laws_text}
        
        【条款内容】
        {clause['content']}
        
        请判断是否违反强制性规定，并引用法规。
        """
```

### 2. 风险审查 Skill (`review.risk_assessment`)

```python
class RiskAssessmentSkill:
    """风险评估技能"""
    
    def __init__(self, rule_engine, llm_client):
        self.rule_engine = rule_engine
        self.llm = llm_client
    
    async def execute(self, clause: dict, policy: dict) -> dict:
        # 1. 硬规则检查
        hard_results = self.rule_engine.check(clause["content"], policy.rules.hard_rules)
        
        # 2. 软规则检查 (LLM)
        soft_results = []
        for soft_rule in policy.rules.soft_rules:
            prompt = self._build_soft_prompt(clause, soft_rule)
            result = await self.llm.call(prompt, schema=RiskSchema)
            soft_results.append(result)
        
        # 3. 聚合结果
        all_issues = hard_results + soft_results
        
        return {
            "skill_id": "review.risk_assessment",
            "clause": clause,
            "issues": all_issues,
            "risk_level": self._calculate_risk_level(all_issues),
            "risk_score": self._calculate_risk_score(all_issues)
        }
```
