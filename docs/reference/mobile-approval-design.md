# 移动端审批设计文档

> 版本：V1.0 | 日期：2024-01-15

---

## 一、设计目标

通过飞书/企微审批卡片通知，实现移动端快速审批，不阻塞业务流程。

---

## 二、技术方案

### 2.1 技术选型

| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| **独立 H5 页面** | 功能完整，可自定义 UI | 开发成本高，用户体验一般 | ❌ V1 排除 |
| **飞书/企微审批卡片** | 零开发成本，用户体验好，集成度高 | 功能受限，仅支持快捷操作 | ✅ V1 采用 |
| **小程序** | 体验好，功能完整 | 开发成本高，需审核上线 | ❌ V2 考虑 |

### 2.2 集成方式

```
合同审批 → 飞书/企微机器人推送 → 审批卡片 → 
  ├─ 快捷审批（通过/拒绝）→ 回调 API → 更新审批状态
  └─ 查看详情 → 跳转 H5 详情页 → 完整审批
```

---

## 三、飞书审批卡片设计

### 3.1 卡片结构

```json
{
    "msg_type": "interactive",
    "card": {
        "header": {
            "title": {
                "tag": "plain_text",
                "content": "📄 合同审批待办"
            },
            "template": "blue"
        },
        "elements": [
            {
                "tag": "div",
                "fields": [
                    {
                        "is_short": true,
                        "text": {
                            "tag": "lark_md",
                            "content": "**合同名称**\nXXX 采购合同"
                        }
                    },
                    {
                        "is_short": true,
                        "text": {
                            "tag": "lark_md",
                            "content": "**合同金额**\n¥500,000"
                        }
                    }
                ]
            },
            {
                "tag": "div",
                "fields": [
                    {
                        "is_short": true,
                        "text": {
                            "tag": "lark_md",
                            "content": "**提交人**\n张三"
                        }
                    },
                    {
                        "is_short": true,
                        "text": {
                            "tag": "lark_md",
                            "content": "**提交时间**\n2024-01-15 10:00"
                        }
                    }
                ]
            },
            {
                "tag": "div",
                "fields": [
                    {
                        "is_short": true,
                        "text": {
                            "tag": "lark_md",
                            "content": "**当前节点**\n法务审核"
                        }
                    },
                    {
                        "is_short": true,
                        "text": {
                            "tag": "lark_md",
                            "content": "**紧急程度**\n🔴 紧急"
                        }
                    }
                ]
            },
            {
                "tag": "hr"
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": "✅ 通过"
                        },
                        "type": "primary",
                        "value": {
                            "action": "approve",
                            "flow_id": 5001
                        }
                    },
                    {
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": "❌ 拒绝"
                        },
                        "type": "danger",
                        "value": {
                            "action": "reject",
                            "flow_id": 5001
                        }
                    },
                    {
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": "📄 查看详情"
                        },
                        "type": "default",
                        "url": "https://contract.example.com/contracts/1001"
                    }
                ]
            }
        ]
    }
}
```

---

## 四、企微审批卡片设计

### 4.1 卡片结构

```json
{
    "msgtype": "template_card",
    "template_card": {
        "card_type": "text_notice",
        "source": {
            "icon_url": "https://example.com/icon.png",
            "desc": "合同审批系统",
            "desc_color": 1
        },
        "main_title": {
            "title": "📄 合同审批待办",
            "desc": "XXX 采购合同 ¥500,000"
        },
        "emphasis_content": {
            "title": "待处理",
            "desc": "请尽快审批"
        },
        "sub_title_text": "提交人：张三 | 提交时间：2024-01-15 10:00",
        "horizontal_content_list": [
            {
                "keyname": "当前节点",
                "value": "法务审核"
            },
            {
                "keyname": "紧急程度",
                "value": "🔴 紧急"
            }
        ],
        "jump_list": [
            {
                "type": 1,
                "url": "https://contract.example.com/contracts/1001",
                "title": "查看详情",
                "colored": true
            }
        ],
        "task_id": "5001",
        "button_list": [
            {
                "text": "✅ 通过",
                "style": 1,
                "key": "approve"
            },
            {
                "text": "❌ 拒绝",
                "style": 2,
                "key": "reject"
            }
        ]
    }
}
```

---

## 五、审批回调处理

### 5.1 飞书回调

```python
from fastapi import APIRouter, Request
import hashlib

router = APIRouter()

@router.post("/feishu/callback")
async def feishu_callback(request: Request):
    """飞书审批回调"""
    data = await request.json()
    
    # 验证签名
    if not _verify_signature(request, data):
        return {"error": "invalid signature"}
    
    # 解析回调数据
    action = data.get("action")
    flow_id = data.get("flow_id")
    user_id = data.get("user_id")
    comment = data.get("comment", "")
    
    # 执行审批操作
    if action == "approve":
        await approval_service.approve_flow(
            flow_id=flow_id,
            action="approve",
            comment=comment,
            user_id=user_id,
            source="feishu",
        )
    elif action == "reject":
        await approval_service.approve_flow(
            flow_id=flow_id,
            action="reject",
            comment=comment,
            user_id=user_id,
            source="feishu",
        )
    
    # 更新卡片状态
    await _update_card_status(data["message_id"], "已审批")
    
    return {"success": True}

def _verify_signature(request: Request, data: dict) -> bool:
    """验证飞书签名"""
    timestamp = request.headers.get("X-Lark-Request-Timestamp")
    nonce = request.headers.get("X-Lark-Request-Nonce")
    signature = request.headers.get("X-Lark-Signature")
    
    # 签名算法：sha256(timestamp + nonce + app_secret)
    app_secret = settings.FEISHU_APP_SECRET
    content = f"{timestamp}{nonce}{app_secret}"
    expected_signature = hashlib.sha256(content.encode()).hexdigest()
    
    return signature == expected_signature

async def _update_card_status(message_id: str, status: str):
    """更新卡片状态"""
    import httpx
    
    async with httpx.AsyncClient() as client:
        await client.patch(
            f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}",
            headers={"Authorization": f"Bearer {await _get_tenant_access_token()}"},
            json={
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {"tag": "plain_text", "content": "📄 合同审批待办"},
                        "template": "green",  # 绿色表示已处理
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"**状态**：{status}"
                            }
                        }
                    ]
                }
            }
        )
```

### 5.2 企微回调

```python
@router.post("/wechat/callback")
async def wechat_callback(request: Request):
    """企微审批回调"""
    data = await request.json()
    
    # 验证签名
    if not _verify_wechat_signature(request, data):
        return {"error": "invalid signature"}
    
    # 解析回调数据
    action = data.get("button_key")
    flow_id = data.get("task_id")
    user_id = data.get("userid")
    comment = data.get("input_text", "")
    
    # 执行审批操作
    if action == "approve":
        await approval_service.approve_flow(
            flow_id=flow_id,
            action="approve",
            comment=comment,
            user_id=user_id,
            source="wechat",
        )
    elif action == "reject":
        await approval_service.approve_flow(
            flow_id=flow_id,
            action="reject",
            comment=comment,
            user_id=user_id,
            source="wechat",
        )
    
    # 更新卡片状态
    await _update_wechat_card_status(data["card_id"], "已审批")
    
    return {"errorcode": 0, "errmsg": "ok"}
```

---

## 六、通知推送服务

### 6.1 推送逻辑

```python
class NotificationService:
    """审批通知服务"""
    
    async def notify_pending_approval(self, flow_id: int, approver_id: int):
        """推送待审批通知"""
        flow = await self._get_flow(flow_id)
        contract = flow["contract"]
        approver = await self._get_user(approver_id)
        
        # 判断使用飞书还是企微
        if approver.get("feishu_open_id"):
            await self._send_feishu_notification(
                approver["feishu_open_id"],
                flow,
                contract,
            )
        elif approver.get("wechat_userid"):
            await self._send_wechat_notification(
                approver["wechat_userid"],
                flow,
                contract,
            )
    
    async def _send_feishu_notification(self, open_id: str, flow: dict, contract: dict):
        """发送飞书通知"""
        import httpx
        
        card_data = {
            "msg_type": "interactive",
            "receive_id": open_id,
            "card": self._build_feishu_card(flow, contract),
        }
        
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://open.feishu.cn/open-apis/im/v1/messages",
                headers={"Authorization": f"Bearer {await self._get_tenant_access_token()}"},
                json=card_data,
            )
    
    async def _send_wechat_notification(self, userid: str, flow: dict, contract: dict):
        """发送企微通知"""
        import httpx
        
        card_data = {
            "touser": userid,
            "msgtype": "template_card",
            "template_card": self._build_wechat_card(flow, contract),
        }
        
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://qyapi.weixin.qq.com/cgi-bin/message/send",
                params={"access_token": await self._get_wechat_access_token()},
                json=card_data,
            )
```

---

## 七、H5 详情页（V2）

### 7.1 页面设计

```
┌─────────────────────────────────────────────────────────────┐
│  合同审批详情                                               │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 合同名称：XXX 采购合同                              │    │
│  │ 合同金额：¥500,000                                  │    │
│  │ 相对方：XXX 公司                                    │    │
│  │ 提交人：张三                                        │    │
│  │ 提交时间：2024-01-15 10:00                          │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 审批流程                                            │    │
│  │                                                     │    │
│  │ ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐                    │    │
│  │ │起│→│主│→│法│→│财│→│高│                    │    │
│  │ │草│  │管│  │务│  │务│  │管│                    │    │
│  │ └──┘  └──┘  └──┘  └──┘  └──┘                    │    │
│  │  ✓     ✓     ●     ○     ○                      │    │
│  │                                                     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 审批意见                                            │    │
│  │ ┌───────────────────────────────────────────────┐  │    │
│  │ │                                               │  │    │
│  │ │                                               │  │    │
│  │ └───────────────────────────────────────────────┘  │    │
│  │                                                     │    │
│  │ [通过] [拒绝] [退回] [委托]                        │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 八、配置管理

### 8.1 飞书应用配置

| 配置项 | 说明 |
|--------|------|
| **App ID** | 飞书应用 App ID |
| **App Secret** | 飞书应用 App Secret |
| **Redirect URI** | 回调地址 |
| **Event URL** | 事件订阅地址 |
| **权限** | im:message:send_v2（发送消息）、im:message:receive_v2（接收消息） |

### 8.2 企微应用配置

| 配置项 | 说明 |
|--------|------|
| **Corp ID** | 企业 ID |
| **Agent ID** | 应用 Agent ID |
| **Secret** | 应用 Secret |
| **回调 URL** | 事件回调地址 |
| **权限** | 消息发送、卡片更新 |

---

## 九、验收标准

| 指标 | 要求 | 测试方法 |
|------|------|---------|
| **通知到达率** | >95% | 发送 100 条通知，统计到达数 |
| **通知延迟** | <5 秒 | 记录发送时间 vs 接收时间 |
| **快捷审批成功率** | >99% | 测试 100 次快捷审批，统计成功数 |
| **卡片状态更新** | 实时 | 审批后卡片状态立即更新 |

---

**文档维护者**：产品团队  
**最后更新**：2024-01-15
