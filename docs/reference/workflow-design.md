# 审批流程设计文档

## 🎯 设计目标

实现灵活可配置的审批流程引擎，支持多级审批、条件分支、并行审批、会签等复杂审批场景。

## 🏗️ 流程引擎架构

```
┌─────────────────────────────────────────────────────────────┐
│                      审批流程引擎                            │
│                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │流程定义  │───▶│流程实例  │───▶  │流程执行  │              │
│  │(模板)    │    │(运行时)  │    │(节点)    │              │
│  └──────────┘    └──────────┘    └──────────┘              │
│       │               │               │                    │
│       ▼               ▼               ▼                    │
│  流程设计器       流程监控        节点处理器                │
└─────────────────────────────────────────────────────────────┘
```

## 📋 审批流程类型

### 1. 标准审批流程

```
起草 → 部门主管审批 → 法务审核 → 财务审核 → 高管审批 → 用印 → 归档
```

### 2. 简易审批流程（小额合同）

```
起草 → 部门主管审批 → 法务审核 → 用印 → 归档
```

### 3. 特殊审批流程（重大合同）

```
起草 → 部门主管审批 → 法务审核 → 财务审核 → 高管审批 → 董事会审批 → 用印 → 归档
```

## 🔧 流程节点定义

```python
# backend/app/models/approval_flow.py

from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel

class NodeType(str, Enum):
    """节点类型"""
    START = "start"           # 开始节点
    APPROVAL = "approval"     # 审批节点
    REVIEW = "review"         # 审核节点（法务/财务）
    CONDITION = "condition"   # 条件分支
    PARALLEL = "parallel"     # 并行节点
    SEAL = "seal"            # 用印节点
    END = "end"              # 结束节点

class ApprovalAction(str, Enum):
    """审批动作"""
    APPROVE = "approve"      # 通过
    REJECT = "reject"        # 拒绝
    RETURN = "return"        # 退回
    DELEGATE = "delegate"    # 委托
    COUNTERSIGN = "countersign"  # 会签

class FlowNode(BaseModel):
    """流程节点"""
    id: str
    name: str
    type: NodeType
    approvers: List[str]              # 审批人 ID 列表
    approval_type: str = "sequential"  # sequential | parallel | countersign
    condition: Optional[Dict] = None   # 条件表达式
    next_nodes: List[str] = []        # 下一个节点 ID 列表
    timeout_hours: int = 24           # 超时时间（小时）
    auto_approve: bool = False        # 超时自动通过
    
class ApprovalFlow(BaseModel):
    """审批流程定义"""
    id: str
    name: str
    description: str
    contract_type: str                # 适用合同类型
    amount_threshold: Optional[float] = None  # 金额阈值
    nodes: List[FlowNode]
    created_at: str
    updated_at: str
```

## 🔄 审批流程状态机

```python
# backend/app/services/workflow/flow_engine.py

from enum import Enum
from typing import Dict, List, Optional

class FlowStatus(str, Enum):
    """流程状态"""
    DRAFT = "draft"              # 草稿
    PENDING_APPROVAL = "pending" # 待审批
    APPROVING = "approving"      # 审批中
    APPROVED = "approved"        # 已通过
    REJECTED = "rejected"        # 已拒绝
    RETURNED = "returned"        # 已退回
    SEALED = "sealed"           # 已用印
    ARCHIVED = "archived"       # 已归档
    CANCELLED = "cancelled"     # 已取消

class FlowEngine:
    """流程引擎"""
    
    async def start_flow(self, contract_id: str, flow_template_id: str) -> str:
        """启动审批流程"""
        # 1. 加载流程模板
        template = await self._load_template(flow_template_id)
        
        # 2. 创建流程实例
        flow_instance = {
            "contract_id": contract_id,
            "template_id": flow_template_id,
            "status": FlowStatus.PENDING_APPROVAL,
            "current_node_id": template.nodes[0].id,
            "node_history": [],
            "created_at": datetime.now(),
        }
        
        # 3. 触发第一个节点
        await self._execute_node(flow_instance, template.nodes[0])
        
        return flow_instance["id"]
    
    async def submit_approval(self, flow_id: str, action: ApprovalAction, comment: str, user_id: str):
        """提交审批"""
        flow = await self._get_flow(flow_id)
        current_node = self._get_current_node(flow)
        
        # 记录审批意见
        approval_record = {
            "node_id": current_node.id,
            "approver_id": user_id,
            "action": action,
            "comment": comment,
            "timestamp": datetime.now(),
        }
        flow["node_history"].append(approval_record)
        
        # 根据动作流转
        if action == ApprovalAction.APPROVE:
            await self._move_to_next(flow, current_node)
        elif action == ApprovalAction.REJECT:
            flow["status"] = FlowStatus.REJECTED
            await self._notify_rejection(flow)
        elif action == ApprovalAction.RETURN:
            flow["status"] = FlowStatus.RETURNED
            await self._notify_return(flow)
        elif action == ApprovalAction.COUNTERSIGN:
            await self._handle_countersign(flow, current_node, user_id)
    
    async def _move_to_next(self, flow: Dict, current_node: FlowNode):
        """流转到下一个节点"""
        if not current_node.next_nodes:
            # 流程结束
            flow["status"] = FlowStatus.APPROVED
            await self._notify_completion(flow)
            return
        
        next_node_id = current_node.next_nodes[0]
        next_node = self._get_node(flow["template_id"], next_node_id)
        
        # 检查条件分支
        if next_node.type == NodeType.CONDITION:
            next_node_id = self._evaluate_condition(flow, next_node)
            next_node = self._get_node(flow["template_id"], next_node_id)
        
        flow["current_node_id"] = next_node_id
        flow["status"] = FlowStatus.APPROVING
        
        # 执行下一个节点
        await self._execute_node(flow, next_node)
    
    def _evaluate_condition(self, flow: Dict, condition_node: FlowNode) -> str:
        """评估条件分支"""
        contract = flow["contract"]
        amount = contract["amount"]
        
        # 金额条件（从配置表读取，非硬编码）
        thresholds = await self._get_amount_thresholds(contract["contract_type"])
        for threshold in thresholds:
            if amount <= threshold["max"]:
                return threshold["next_node_id"]
        return thresholds[-1]["next_node_id"]  # 默认走最高级审批
```

## ⚙️ 审批规则配置化（V1 必做）

### 1. 金额阈值配置表
```sql
CREATE TABLE approval_thresholds (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    contract_type VARCHAR(50) NOT NULL COMMENT '合同类型',
    min_amount DECIMAL(15,2) NOT NULL COMMENT '最小金额',
    max_amount DECIMAL(15,2) COMMENT '最大金额（NULL 表示无上限）',
    flow_template_id BIGINT NOT NULL COMMENT '匹配的流程模板 ID',
    status TINYINT DEFAULT 1 COMMENT '1:启用 0:禁用',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_type_range (contract_type, min_amount, max_amount)
);

-- 示例数据
INSERT INTO approval_thresholds (contract_type, min_amount, max_amount, flow_template_id) VALUES
('purchase', 0, 100000, 1),    -- 采购≤10 万 → 简易流程
('purchase', 100000, 1000000, 2), -- 采购 10-100 万 → 标准流程
('purchase', 1000000, NULL, 3);   -- 采购>100 万 → 特殊流程
```

### 2. 审批人配置表
```sql
CREATE TABLE approval_node_approvers (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    flow_template_id BIGINT NOT NULL COMMENT '流程模板 ID',
    node_id VARCHAR(50) NOT NULL COMMENT '节点 ID',
    approver_type VARCHAR(50) NOT NULL COMMENT 'user_id | role_code | dept_head',
    approver_value VARCHAR(100) COMMENT '具体值（如 user_101 / role_legal）',
    is_required TINYINT DEFAULT 1 COMMENT '是否必填',
    sort_order INT DEFAULT 0 COMMENT '排序',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 示例：法务审核节点配置为 role_legal 角色
INSERT INTO approval_node_approvers (flow_template_id, node_id, approver_type, approver_value) VALUES
(2, 'legal_review', 'role_code', 'role_legal');
```

### 3. 动态审批人解析逻辑
```python
class ApproverResolver:
    """审批人动态解析器"""
    
    async def resolve(self, node_config: Dict) -> List[int]:
        """根据配置解析实际审批人 ID"""
        approver_type = node_config["approver_type"]
        approver_value = node_config["approver_value"]
        
        if approver_type == "user_id":
            return [int(approver_value)]
        elif approver_type == "role_code":
            # 查询拥有该角色的所有用户
            users = await self.db.users.find({"role_code": approver_value, "status": 1})
            return [u["id"] for u in users]
        elif approver_type == "dept_head":
            # 查询合同创建人的部门主管
            contract = await self._get_current_contract()
            dept_id = contract["department_id"]
            dept = await self.db.departments.find(dept_id)
            return [dept["head_id"]] if dept["head_id"] else []
        return []
```

## 📊 审批规则配置

```python
# backend/app/services/workflow/rule_config.py

APPROVAL_RULES = {
    # 按合同类型
    "sales_contract": {
        "amount_thresholds": [
            {"max": 100000, "flow": "simple"},      # 10 万以下：简易流程
            {"max": 1000000, "flow": "standard"},   # 10-100 万：标准流程
            {"max": None, "flow": "special"},       # 100 万以上：特殊流程
        ],
        "required_reviews": ["legal", "finance"],   # 必须经过的审核
    },
    
    "purchase_contract": {
        "amount_thresholds": [
            {"max": 50000, "flow": "simple"},
            {"max": 500000, "flow": "standard"},
            {"max": None, "flow": "special"},
        ],
        "required_reviews": ["legal", "finance", "tech"],
    },
    
    "labor_contract": {
        "amount_thresholds": [
            {"max": None, "flow": "standard"},
        ],
        "required_reviews": ["legal", "hr"],
    },
}

# 审批人角色配置
APPROVER_ROLES = {
    "department_head": {
        "title": "部门主管",
        "authority": "审批本部门合同",
        "timeout": 24,
    },
    "legal": {
        "title": "法务审核",
        "authority": "法律风险审查",
        "timeout": 48,
    },
    "finance": {
        "title": "财务审核",
        "authority": "财务条款审查",
        "timeout": 24,
    },
    "executive": {
        "title": "高管审批",
        "authority": "重大合同审批",
        "timeout": 72,
    },
    "board": {
        "title": "董事会审批",
        "authority": "特别重大合同",
        "timeout": 168,
    },
}
```

## 🔔 审批通知机制

```python
# backend/app/services/workflow/notification.py

from enum import Enum
from typing import List

class NotificationChannel(str, Enum):
    """通知渠道"""
    EMAIL = "email"
    WECHAT = "wechat"
    SMS = "sms"
    SYSTEM = "system"

class NotificationService:
    """审批通知服务"""
    
    async def notify_pending_approval(self, flow_id: str, approver_id: str):
        """通知待审批"""
        flow = await self._get_flow(flow_id)
        contract = flow["contract"]
        
        message = {
            "title": "待审批合同通知",
            "content": f"您有一条合同待审批：{contract['title']}",
            "contract_id": contract["id"],
            "flow_id": flow_id,
            "deadline": self._calculate_deadline(flow),
        }
        
        # 多渠道通知
        await self._send(approver_id, NotificationChannel.SYSTEM, message)
        await self._send(approver_id, NotificationChannel.EMAIL, message)
        await self._send(approver_id, NotificationChannel.WECHAT, message)
    
    async def notify_timeout_reminder(self, flow_id: str):
        """超时提醒"""
        flow = await self._get_flow(flow_id)
        current_approver = flow["current_approver"]
        
        message = {
            "title": "审批超时提醒",
            "content": f"您的合同审批已超时：{flow['contract']['title']}",
            "contract_id": flow["contract"]["id"],
            "flow_id": flow_id,
        }
        
        await self._send(current_approver, NotificationChannel.SYSTEM, message)
        await self._send(current_approver, NotificationChannel.SMS, message)
    
    async def notify_flow_completed(self, flow_id: str):
        """流程完成通知"""
        flow = await self._get_flow(flow_id)
        initiator = flow["initiator_id"]
        
        message = {
            "title": "审批流程完成",
            "content": f"您的合同审批已完成：{flow['contract']['title']}",
            "contract_id": flow["contract"]["id"],
            "flow_id": flow_id,
            "result": flow["status"],
        }
        
        await self._send(initiator, NotificationChannel.SYSTEM, message)
        await self._send(initiator, NotificationChannel.EMAIL, message)
```

## 📈 审批效率监控

```python
# backend/app/services/workflow/flow_monitor.py

class FlowMonitor:
    """审批流程监控"""
    
    async def get_flow_metrics(self, contract_id: str) -> Dict:
        """获取流程指标"""
        flow = await self._get_flow_by_contract(contract_id)
        
        metrics = {
            "total_nodes": len(flow["node_history"]),
            "completed_nodes": len([n for n in flow["node_history"] if n["action"]]),
            "current_node": flow["current_node_id"],
            "elapsed_hours": self._calculate_elapsed(flow),
            "average_node_time": self._calculate_average_time(flow),
            "bottleneck_nodes": self._find_bottlenecks(flow),
            "timeout_risk": self._assess_timeout_risk(flow),
        }
        
        return metrics
    
    def _find_bottlenecks(self, flow: Dict) -> List[Dict]:
        """识别审批瓶颈"""
        node_times = {}
        for record in flow["node_history"]:
            node_id = record["node_id"]
            if node_id not in node_times:
                node_times[node_id] = []
            node_times[node_id].append(record["duration"])
        
        bottlenecks = []
        for node_id, times in node_times.items():
            avg_time = sum(times) / len(times)
            if avg_time > 24:  # 平均超过 24 小时
                bottlenecks.append({
                    "node_id": node_id,
                    "average_hours": round(avg_time, 2),
                    "max_hours": max(times),
                    "count": len(times),
                })
        
        return sorted(bottlenecks, key=lambda x: x["average_hours"], reverse=True)
```

## 🎨 前端审批界面设计

```
┌─────────────────────────────────────────────────────────────┐
│  审批中心                                                   │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────────────────────────────┐  │
│  │ 待办审批    │  │ 合同详情                              │  │
│  │ (12)        │  │                                     │  │
│  │             │  │ 合同名称：XXX 采购合同               │  │
│  │ ● 采购合同  │  │ 合同金额：¥500,000                 │  │
│  │   待审批    │  │ 对方单位：XXX 公司                  │  │
│  │             │  │ 当前节点：法务审核                  │  │
│  │ ● 销售合同  │  │                                     │  │
│  │   待审批    │  │ 审批流程：                          │  │
│  │             │  │ ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐    │  │
│  │ ● 劳务合同  │  │ │起│→│主│→│法│→│财│→│高│    │  │
│  │   待审批    │  │ │草│  │管│  │务│  │务│  │管│    │  │
│  │             │  │ └──┘  └──┘  └──┘  └──┘  └──┘    │  │
│  │ ...         │  │  ✓     ✓     ●     ○     ○      │  │
│  └─────────────┘  │                                     │  │
│                   │  审批意见：                          │  │
│                   │ ┌───────────────────────────────┐  │  │
│                   │ │                               │  │  │
│                   │ │                               │  │  │
│                   │ └───────────────────────────────┘  │  │
│                   │                                     │  │
│                   │  [通过] [拒绝] [退回] [委托]        │  │
│                   └─────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 📋 审批记录审计

```python
# backend/app/services/audit/approval_audit.py

class ApprovalAudit:
    """审批审计日志"""
    
    async def log_approval_action(self, record: Dict):
        """记录审批操作"""
        audit_log = {
            "flow_id": record["flow_id"],
            "contract_id": record["contract_id"],
            "user_id": record["approver_id"],
            "action": record["action"],
            "comment": record["comment"],
            "node_id": record["node_id"],
            "timestamp": datetime.now(),
            "ip_address": record.get("ip"),
            "user_agent": record.get("user_agent"),
        }
        
        await self.db.audit_logs.insert(audit_log)
    
    async def get_approval_history(self, contract_id: str) -> List[Dict]:
        """获取审批历史"""
        return await self.db.audit_logs.find(
            {"contract_id": contract_id},
            sort=[("timestamp", -1)]
        )
```
