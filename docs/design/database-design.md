# 数据库设计文档

> 版本：V1.1 | 日期：2026-05-18 | 技术栈：**MySQL 8**  
> 状态枚举见 [contract-status-dictionary.md](./contract-status-dictionary.md) | 真相源 [DESIGN_STATUS.md](./DESIGN_STATUS.md)

## 📊 ER 图概要

```
┌──────────┐     ┌──────────────┐     ┌─────────────────┐
│  users   │────<│  contracts   │>────│ counterparties  │
└──────────┘     └──────────────┘     └─────────────────┘
     │                   │
     │                   │
     ▼                   ▼
┌──────────┐     ┌────────────────┐
│  roles   │     │contract_versions│
└──────────┘     └────────────────┘
                      │
                      ▼
                 ┌──────────────┐
                 │approval_flows│
                 └──────────────┘
                      │
                      ▼
                 ┌──────────────┐
                 │approval_steps│
                 └──────────────┘
                      │
                      ▼
                 ┌──────────────┐
                 │  ai_reviews  │
                 └──────────────┘
                      │
                      ▼
                 ┌──────────────┐
                 │ risk_alerts  │
                 └──────────────┘
```

## 📋 核心表设计

### 1. 用户表 (users)

```sql
CREATE TABLE users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    real_name VARCHAR(50) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(20),
    department_id BIGINT,
    role_id BIGINT,
    status TINYINT DEFAULT 1 COMMENT '1:启用 0:禁用',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_department (department_id),
    INDEX idx_role (role_id)
);
```

### 2. 角色表 (roles)

```sql
CREATE TABLE roles (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) UNIQUE NOT NULL COMMENT '角色名称',
    code VARCHAR(50) UNIQUE NOT NULL COMMENT '角色编码',
    description TEXT,
    permissions JSON COMMENT '权限列表',
    status TINYINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 预置角色
INSERT INTO roles (name, code, permissions) VALUES
('系统管理员', 'admin', '["*"]'),
('法务审核员', 'legal', '["contract:review", "ai:review", "risk:view"]'),
('财务审核员', 'finance', '["contract:review", "finance:view"]'),
('部门主管', 'dept_head', '["contract:approve", "contract:view:dept"]'),
('高管', 'executive', '["contract:approve:high", "report:view"]'),
('普通员工', 'employee', '["contract:create", "contract:view:own"]');
```

### 3. 部门表 (departments)

```sql
CREATE TABLE departments (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    parent_id BIGINT DEFAULT 0,
    level INT DEFAULT 1,
    path VARCHAR(500) COMMENT '部门路径',
    status TINYINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4. 相对方表 (counterparties)

```sql
CREATE TABLE counterparties (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(200) NOT NULL COMMENT '单位名称',
    credit_code VARCHAR(50) UNIQUE COMMENT '统一社会信用代码',
    legal_person VARCHAR(50) COMMENT '法定代表人',
    contact_name VARCHAR(50) COMMENT '联系人',
    contact_phone VARCHAR(20) COMMENT '联系电话',
    address VARCHAR(500) COMMENT '地址',
    industry VARCHAR(50) COMMENT '行业分类',
    credit_rating VARCHAR(10) COMMENT '信用评级',
    is_blacklist TINYINT DEFAULT 0 COMMENT '是否黑名单 0否 1是',
    blacklist_reason TEXT COMMENT '列入黑名单原因',
    status TINYINT DEFAULT 1 COMMENT '1:启用 0:禁用',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name),
    INDEX idx_credit_code (credit_code),
    INDEX idx_blacklist (is_blacklist)
);
```

### 5. 合同主表 (contracts)

```sql
CREATE TABLE contracts (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    org_id BIGINT DEFAULT 1 COMMENT '组织 ID（V2 多组织预留）',
    contract_no VARCHAR(50) UNIQUE NOT NULL COMMENT '合同编号',
    title VARCHAR(200) NOT NULL COMMENT '合同名称',
    contract_type VARCHAR(50) NOT NULL COMMENT '合同类型',
    status VARCHAR(20) NOT NULL DEFAULT 'draft' COMMENT 'draft/pending/approved/sealed/signed/archived/executing/terminated/void',
    
    -- 对方信息（counterparty_id 关联档案；name/credit_code 为签署时快照）
    counterparty_id BIGINT COMMENT '相对方 ID',
    counterparty_name VARCHAR(200) NOT NULL COMMENT '对方单位名称（快照）',
    counterparty_type VARCHAR(50) COMMENT '对方类型',
    counterparty_credit_code VARCHAR(50) COMMENT '统一社会信用代码（快照）',
    
    -- 金额信息
    amount DECIMAL(15,2) COMMENT '合同金额',
    currency VARCHAR(10) DEFAULT 'CNY',
    tax_rate DECIMAL(5,2) COMMENT '税率',
    
    -- 期限信息
    start_date DATE COMMENT '开始日期',
    end_date DATE COMMENT '结束日期',
    
    -- 审批信息
    current_flow_id BIGINT COMMENT '当前审批流程 ID',
    approval_status VARCHAR(50) COMMENT '子阶段：ai_screening/dept_approval/legal_review/finance_review/executive_approval/board_approval/seal_pending/done',
    
    -- 签署信息
    sign_date DATE COMMENT '签署日期',
    sign_method VARCHAR(20) COMMENT '签署方式',
    seal_record_id BIGINT COMMENT '用印记录 ID',
    
    -- 归档信息
    archive_date DATE COMMENT '归档日期',
    archive_location VARCHAR(200) COMMENT '归档位置',
    
    -- 元数据
    creator_id BIGINT NOT NULL COMMENT '创建人 ID',
    department_id BIGINT COMMENT '所属部门',
    risk_level VARCHAR(20) DEFAULT 'low' COMMENT '风险等级',
    deleted_at TIMESTAMP NULL COMMENT '软删除标记',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_org (org_id),
    INDEX idx_contract_no (contract_no),
    INDEX idx_type (contract_type),
    INDEX idx_status (status),
    INDEX idx_creator (creator_id),
    INDEX idx_department (department_id),
    INDEX idx_counterparty (counterparty_name),
    INDEX idx_counterparty_id (counterparty_id),
    INDEX idx_risk_level (risk_level),
    INDEX idx_deleted (deleted_at),
    FOREIGN KEY (counterparty_id) REFERENCES counterparties(id)
);
```

### 6. 合同版本表 (contract_versions)

```sql
CREATE TABLE contract_versions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    contract_id BIGINT NOT NULL,
    version INT NOT NULL COMMENT '版本号',
    title VARCHAR(200),
    content LONGTEXT COMMENT '合同内容',
    file_path VARCHAR(500) COMMENT '文件路径',
    file_type VARCHAR(10) COMMENT '文件类型',
    file_size BIGINT COMMENT '文件大小',
    file_hash VARCHAR(64) COMMENT '文件哈希',
    change_description TEXT COMMENT '变更说明',
    creator_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (contract_id) REFERENCES contracts(id) ON DELETE CASCADE,
    UNIQUE KEY uk_contract_version (contract_id, version),
    INDEX idx_hash (file_hash)
);
```

### 7. 审批流程表 (approval_flows)

```sql
CREATE TABLE approval_flows (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    contract_id BIGINT NOT NULL,
    flow_template_id BIGINT COMMENT '流程模板 ID',
    flow_type VARCHAR(50) COMMENT '流程类型',
    status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '流程状态',
    current_node_id VARCHAR(50) COMMENT '当前节点 ID',
    current_step INT DEFAULT 0 COMMENT '当前步骤',
    total_steps INT COMMENT '总步骤数',
    start_time TIMESTAMP NULL COMMENT '开始时间',
    end_time TIMESTAMP NULL COMMENT '结束时间',
    duration_hours DECIMAL(10,2) COMMENT '耗时（小时）',
    comment TEXT COMMENT '流程备注',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (contract_id) REFERENCES contracts(id) ON DELETE CASCADE,
    INDEX idx_contract (contract_id),
    INDEX idx_status (status)
);
```

### 8. 审批节点表 (approval_steps)

```sql
CREATE TABLE approval_steps (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    flow_id BIGINT NOT NULL,
    step_number INT NOT NULL COMMENT '步骤序号',
    node_id VARCHAR(50) NOT NULL COMMENT '节点 ID',
    node_name VARCHAR(100) COMMENT '节点名称',
    approver_id BIGINT NOT NULL COMMENT '审批人 ID',
    approver_name VARCHAR(50) COMMENT '审批人姓名',
    action VARCHAR(20) COMMENT '审批动作',
    comment TEXT COMMENT '审批意见',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '节点状态',
    start_time TIMESTAMP NULL COMMENT '开始时间',
    complete_time TIMESTAMP NULL COMMENT '完成时间',
    duration_hours DECIMAL(10,2) COMMENT '处理耗时',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (flow_id) REFERENCES approval_flows(id) ON DELETE CASCADE,
    INDEX idx_flow (flow_id),
    INDEX idx_approver (approver_id),
    INDEX idx_status (status)
);
```

### 9. AI 审查记录表 (ai_reviews)

```sql
CREATE TABLE ai_reviews (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    contract_id BIGINT NOT NULL,
    version_id BIGINT NOT NULL COMMENT '合同版本 ID',
    review_id VARCHAR(50) UNIQUE NOT NULL COMMENT '审查记录 ID',
    
    -- 审查结果
    overall_risk_level VARCHAR(20) COMMENT '整体风险等级',
    overall_risk_score DECIMAL(5,2) COMMENT '整体风险评分',
    recommendation TEXT COMMENT '审查建议',
    
    -- 审查详情
    clause_reviews JSON COMMENT '条款审查结果',
    rule_violations JSON COMMENT '规则违规项',
    summary JSON COMMENT '审查摘要',
    
    -- 元数据
    model_version VARCHAR(50) COMMENT '模型版本',
    review_duration_seconds INT COMMENT '审查耗时（秒）',
    reviewer_id BIGINT COMMENT '人工复核人 ID',
    review_status VARCHAR(20) DEFAULT 'ai_done' COMMENT 'ai_done | reviewed | confirmed',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (contract_id) REFERENCES contracts(id) ON DELETE CASCADE,
    INDEX idx_contract (contract_id),
    INDEX idx_risk_level (overall_risk_level),
    INDEX idx_risk_score (overall_risk_score)
);
```

### 10. 风险预警表 (risk_alerts)

```sql
CREATE TABLE risk_alerts (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    contract_id BIGINT NOT NULL,
    alert_type VARCHAR(50) NOT NULL COMMENT '预警类型',
    alert_level VARCHAR(20) NOT NULL COMMENT '预警等级',
    title VARCHAR(200) NOT NULL COMMENT '预警标题',
    message TEXT COMMENT '预警内容',
    source VARCHAR(50) COMMENT '来源：ai | rule | manual',
    source_detail JSON COMMENT '来源详情',
    
    -- 处理状态
    status VARCHAR(20) DEFAULT 'pending' COMMENT 'pending | processing | resolved | ignored',
    handler_id BIGINT COMMENT '处理人 ID',
    handle_comment TEXT COMMENT '处理意见',
    handle_time TIMESTAMP NULL COMMENT '处理时间',
    
    -- 关联信息
    related_clause VARCHAR(100) COMMENT '相关条款',
    legal_basis TEXT COMMENT '法律依据',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (contract_id) REFERENCES contracts(id) ON DELETE CASCADE,
    INDEX idx_contract (contract_id),
    INDEX idx_type (alert_type),
    INDEX idx_level (alert_level),
    INDEX idx_status (status)
);
```

### 11. 用印记录表 (seal_records)

```sql
CREATE TABLE seal_records (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    contract_id BIGINT NOT NULL,
    seal_type VARCHAR(50) COMMENT '印章类型',
    seal_id BIGINT COMMENT '印章 ID',
    user_id BIGINT NOT NULL COMMENT '操作人 ID',
    approval_flow_id BIGINT COMMENT '审批流程 ID',
    file_path VARCHAR(500) COMMENT '用印文件路径',
    file_hash VARCHAR(64) COMMENT '文件哈希',
    watermark_hash VARCHAR(64) COMMENT '水印哈希',
    ip_address VARCHAR(50) COMMENT '操作 IP',
    user_agent TEXT COMMENT '浏览器信息',
    status VARCHAR(20) DEFAULT 'completed' COMMENT '状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (contract_id) REFERENCES contracts(id) ON DELETE CASCADE,
    INDEX idx_contract (contract_id),
    INDEX idx_user (user_id),
    INDEX idx_hash (file_hash)
);
```

### 12. 审计日志表 (audit_logs)

```sql
CREATE TABLE audit_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    username VARCHAR(50) COMMENT '用户名',
    action VARCHAR(100) NOT NULL COMMENT '操作动作',
    resource_type VARCHAR(50) COMMENT '资源类型',
    resource_id BIGINT COMMENT '资源 ID',
    resource_name VARCHAR(200) COMMENT '资源名称',
    detail JSON COMMENT '操作详情',
    ip_address VARCHAR(50) COMMENT 'IP 地址',
    user_agent TEXT COMMENT '浏览器信息',
    status VARCHAR(20) DEFAULT 'success' COMMENT '操作状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_user (user_id),
    INDEX idx_action (action),
    INDEX idx_resource (resource_type, resource_id),
    INDEX idx_time (created_at)
);
```

### 13. 合同台账表 (contract_ledger)

```sql
CREATE TABLE contract_ledger (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    contract_id BIGINT NOT NULL,
    contract_no VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    contract_type VARCHAR(50),
    counterparty_name VARCHAR(200),
    amount DECIMAL(15,2),
    status VARCHAR(20),
    start_date DATE,
    end_date DATE,
    approval_status VARCHAR(20),
    risk_level VARCHAR(20),
    creator_name VARCHAR(50),
    department_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (contract_id) REFERENCES contracts(id),
    INDEX idx_contract_no (contract_no),
    INDEX idx_type (contract_type),
    INDEX idx_status (status),
    INDEX idx_counterparty (counterparty_name),
    INDEX idx_risk_level (risk_level)
);
```

## 🔍 索引优化策略

| 查询场景 | 索引方案 |
|---------|---------|
| 合同列表查询 | `(status, contract_type, created_at)` 复合索引 |
| 对方单位检索 | `counterparty_name` 全文索引 |
| 审批待办查询 | `(approver_id, status)` 复合索引 |
| 风险合同统计 | `(risk_level, status)` 复合索引 |
| 到期合同提醒 | `end_date` 索引 + 定时任务 |
| 审计日志查询 | `(user_id, created_at)` 复合索引 |

## 🔐 数据安全

```sql
-- 敏感字段加密存储
ALTER TABLE contracts 
    ADD COLUMN counterparty_credit_code_encrypted VARBINARY(255);

-- 数据脱敏视图
CREATE VIEW v_contract_public AS
SELECT 
    id,
    contract_no,
    title,
    contract_type,
    status,
    LEFT(counterparty_name, 3) + '***' AS counterparty_name,
    amount,
    start_date,
    end_date
FROM contracts
WHERE status IN ('approved', 'sealed', 'archived');

-- 操作审计触发器
DELIMITER //
CREATE TRIGGER trg_contract_update
AFTER UPDATE ON contracts
FOR EACH ROW
BEGIN
    INSERT INTO audit_logs (user_id, action, resource_type, resource_id, detail)
    VALUES (
        @current_user_id,
        'contract_update',
        'contract',
        NEW.id,
        JSON_OBJECT(
            'old_status', OLD.status,
            'new_status', NEW.status,
            'old_amount', OLD.amount,
            'new_amount', NEW.amount
        )
    );
END//
DELIMITER ;
```

## 📊 统计视图

```sql
-- 合同统计视图
CREATE VIEW v_contract_statistics AS
SELECT 
    DATE_FORMAT(created_at, '%Y-%m') AS month,
    contract_type,
    COUNT(*) AS total_count,
    SUM(amount) AS total_amount,
    AVG(amount) AS avg_amount,
    SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) AS approved_count,
    SUM(CASE WHEN risk_level = 'high' THEN 1 ELSE 0 END) AS high_risk_count,
    AVG(CASE WHEN approval_status = 'approved' 
        THEN TIMESTAMPDIFF(HOUR, created_at, updated_at) 
    END) AS avg_approval_hours
FROM contracts
GROUP BY DATE_FORMAT(created_at, '%Y-%m'), contract_type;

-- 审批效率视图
CREATE VIEW v_approval_efficiency AS
SELECT 
    af.flow_type,
    COUNT(*) AS total_flows,
    AVG(af.duration_hours) AS avg_duration_hours,
    MAX(af.duration_hours) AS max_duration_hours,
    MIN(af.duration_hours) AS min_duration_hours,
    SUM(CASE WHEN af.duration_hours > 48 THEN 1 ELSE 0 END) AS overtime_count
FROM approval_flows af
WHERE af.status = 'approved'
GROUP BY af.flow_type;
```
