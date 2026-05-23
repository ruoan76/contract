-- 合同审批管理平台 - 数据库初始化脚本
-- 版本: 1.0.0
-- 数据库: MySQL 8.0

CREATE DATABASE IF NOT EXISTS `contract_db` 
  DEFAULT CHARACTER SET utf8mb4 
  COLLATE utf8mb4_unicode_ci;

USE `contract_db`;

-- ==============================================================================
-- 1. 组织与权限体系
-- ==============================================================================

-- 部门表
CREATE TABLE IF NOT EXISTS `departments` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(100) NOT NULL COMMENT '部门名称',
  `parent_id` INT DEFAULT 0 COMMENT '父部门 ID',
  `level` INT DEFAULT 1 COMMENT '层级',
  `path` VARCHAR(500) COMMENT '部门路径',
  `status` TINYINT DEFAULT 1 COMMENT '1:启用 0:禁用',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_department_parent` (`parent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='部门表';

-- 角色表
CREATE TABLE IF NOT EXISTS `roles` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(50) UNIQUE NOT NULL COMMENT '角色名称',
  `code` VARCHAR(50) UNIQUE NOT NULL COMMENT '角色编码',
  `description` TEXT COMMENT '角色描述',
  `permissions` JSON COMMENT '权限列表',
  `status` TINYINT DEFAULT 1 COMMENT '1:启用 0:禁用',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_role_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色表';

-- 用户表
CREATE TABLE IF NOT EXISTS `users` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `username` VARCHAR(50) UNIQUE NOT NULL COMMENT '用户名',
  `password_hash` VARCHAR(255) NOT NULL COMMENT '密码哈希',
  `real_name` VARCHAR(50) NOT NULL COMMENT '真实姓名',
  `email` VARCHAR(100) COMMENT '邮箱',
  `phone` VARCHAR(20) COMMENT '手机号',
  `department_id` INT COMMENT '部门 ID',
  `role_id` INT COMMENT '角色 ID',
  `status` TINYINT DEFAULT 1 COMMENT '1:启用 0:禁用',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_user_username` (`username`),
  INDEX `idx_user_department` (`department_id`),
  INDEX `idx_user_role` (`role_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ==============================================================================
-- 2. 相对方管理
-- ==============================================================================

CREATE TABLE IF NOT EXISTS `counterparties` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(200) NOT NULL COMMENT '相对方名称',
  `credit_code` VARCHAR(50) UNIQUE COMMENT '统一社会信用代码',
  `type` VARCHAR(50) COMMENT '类型：供应商/客户/合作伙伴',
  `rating` VARCHAR(20) DEFAULT 'A' COMMENT '信用评级',
  `is_blacklisted` TINYINT DEFAULT 0 COMMENT '是否在黑名单',
  `contact_person` VARCHAR(50) COMMENT '联系人',
  `contact_phone` VARCHAR(20) COMMENT '联系电话',
  `address` VARCHAR(500) COMMENT '地址',
  `status` TINYINT DEFAULT 1 COMMENT '1:启用 0:禁用',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_counterparty_name` (`name`),
  INDEX `idx_counterparty_credit` (`credit_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='相对方表';

-- ==============================================================================
-- 3. 合同管理
-- ==============================================================================

CREATE TABLE IF NOT EXISTS `contracts` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `contract_no` VARCHAR(50) UNIQUE NOT NULL COMMENT '合同编号',
  `title` VARCHAR(200) NOT NULL COMMENT '合同名称',
  `contract_type` VARCHAR(50) NOT NULL COMMENT '合同类型',
  `status` VARCHAR(20) NOT NULL DEFAULT 'draft' COMMENT '状态: draft/ai_reviewing/ai_reviewed/approving/approved/signed/archived/rejected/returned',
  `counterparty_id` INT COMMENT '相对方 ID',
  `counterparty_name` VARCHAR(200) NOT NULL COMMENT '对方单位名称',
  `counterparty_credit_code` VARCHAR(50) COMMENT '统一社会信用代码',
  `amount` DECIMAL(15, 2) COMMENT '合同金额',
  `currency` VARCHAR(10) DEFAULT 'CNY',
  `tax_rate` DECIMAL(5, 2) COMMENT '税率',
  `start_date` DATE COMMENT '开始日期',
  `end_date` DATE COMMENT '结束日期',
  `current_flow_id` INT COMMENT '当前审批流程 ID',
  `approval_status` VARCHAR(20) DEFAULT 'pending' COMMENT '审批状态',
  `sign_date` DATE COMMENT '签署日期',
  `sign_method` VARCHAR(20) COMMENT '签署方式',
  `seal_record_id` INT COMMENT '用印记录 ID',
  `archive_date` DATE COMMENT '归档日期',
  `archive_location` VARCHAR(200) COMMENT '归档位置',
  `creator_id` INT NOT NULL COMMENT '创建人 ID',
  `department_id` INT COMMENT '所属部门',
  `risk_level` VARCHAR(20) DEFAULT 'low' COMMENT '风险等级: low/medium/high/critical',
  `current_version_id` INT COMMENT '当前版本 ID',
  `flow_type` VARCHAR(50) COMMENT '审批流程类型: standard/simple/special',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_contract_no` (`contract_no`),
  INDEX `idx_type` (`contract_type`),
  INDEX `idx_status` (`status`),
  INDEX `idx_creator` (`creator_id`),
  INDEX `idx_department` (`department_id`),
  INDEX `idx_counterparty_name` (`counterparty_name`),
  INDEX `idx_risk_level` (`risk_level`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='合同主表';

-- 合同版本表
CREATE TABLE IF NOT EXISTS `contract_versions` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `contract_id` INT NOT NULL COMMENT '合同 ID',
  `version` INT NOT NULL COMMENT '版本号',
  `title` VARCHAR(200),
  `file_path` VARCHAR(500) COMMENT '文件路径 (MinIO key)',
  `file_type` VARCHAR(10) COMMENT '文件类型',
  `file_size` BIGINT COMMENT '文件大小 (bytes)',
  `file_hash` VARCHAR(64) COMMENT '文件哈希 (SHA-256)',
  `change_description` TEXT COMMENT '变更说明',
  `creator_id` INT NOT NULL COMMENT '创建人 ID',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`contract_id`) REFERENCES `contracts`(`id`) ON DELETE CASCADE,
  INDEX `idx_version_contract` (`contract_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='合同版本表';

-- ==============================================================================
-- 4. 审批流程
-- ==============================================================================

CREATE TABLE IF NOT EXISTS `approval_flows` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `contract_id` INT NOT NULL COMMENT '合同 ID',
  `flow_template_id` INT COMMENT '流程模板 ID',
  `flow_type` VARCHAR(50) COMMENT '流程类型: standard/simple/special',
  `status` VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '状态: pending/approving/approved/rejected/returned/cancelled',
  `current_node_id` VARCHAR(50) COMMENT '当前节点 ID',
  `current_step` INT DEFAULT 0 COMMENT '当前步骤',
  `total_steps` INT COMMENT '总步骤数',
  `start_time` DATETIME COMMENT '开始时间',
  `end_time` DATETIME COMMENT '结束时间',
  `duration_hours` DECIMAL(8, 2) COMMENT '耗时（小时）',
  `comment` TEXT COMMENT '流程备注',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (`contract_id`) REFERENCES `contracts`(`id`) ON DELETE CASCADE,
  INDEX `idx_approval_contract` (`contract_id`),
  INDEX `idx_approval_status` (`status`),
  INDEX `idx_approval_current_node` (`current_node_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审批流程表';

-- 审批节点记录表
CREATE TABLE IF NOT EXISTS `approval_steps` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `flow_id` INT NOT NULL COMMENT '流程 ID',
  `step_number` INT NOT NULL COMMENT '步骤序号',
  `node_id` VARCHAR(50) NOT NULL COMMENT '节点 ID',
  `node_name` VARCHAR(100) NOT NULL COMMENT '节点名称',
  `approver_id` INT NOT NULL COMMENT '审批人 ID',
  `approver_name` VARCHAR(50) NOT NULL COMMENT '审批人姓名',
  `action` VARCHAR(20) COMMENT '审批动作: approve/reject/return/transfer',
  `comment` TEXT COMMENT '审批意见',
  `status` VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/completed/skipped',
  `start_time` DATETIME COMMENT '开始时间',
  `complete_time` DATETIME COMMENT '完成时间',
  `duration_hours` DECIMAL(8, 2) COMMENT '处理耗时',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`flow_id`) REFERENCES `approval_flows`(`id`) ON DELETE CASCADE,
  INDEX `idx_step_flow` (`flow_id`),
  INDEX `idx_step_number` (`flow_id`, `step_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审批步骤记录表';

-- ==============================================================================
-- 5. AI 审查
-- ==============================================================================

CREATE TABLE IF NOT EXISTS `ai_reviews` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `contract_id` INT NOT NULL COMMENT '合同 ID',
  `version_id` INT NOT NULL COMMENT '合同版本 ID',
  `review_id` VARCHAR(50) UNIQUE NOT NULL COMMENT '审查记录 ID (REV-XXXXXXXX)',
  `overall_risk_level` VARCHAR(20) COMMENT '整体风险等级',
  `overall_risk_score` DECIMAL(5, 2) COMMENT '整体风险评分 (0-100)',
  `recommendation` TEXT COMMENT '审查建议',
  `clause_reviews` JSON COMMENT '条款审查结果',
  `rule_violations` JSON COMMENT '规则违规项',
  `summary` JSON COMMENT '审查摘要',
  `model_version` VARCHAR(50) COMMENT '模型版本',
  `review_duration_seconds` INT COMMENT '审查耗时（秒）',
  `reviewer_id` INT COMMENT '人工复核人 ID',
  `review_status` VARCHAR(20) DEFAULT 'reviewing' COMMENT '状态: reviewing/ai_done/reviewed/confirmed',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (`contract_id`) REFERENCES `contracts`(`id`) ON DELETE CASCADE,
  INDEX `idx_review_contract` (`contract_id`),
  INDEX `idx_review_id` (`review_id`),
  INDEX `idx_review_status` (`review_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI 审查记录表';

-- ==============================================================================
-- 6. 风险预警
-- ==============================================================================

CREATE TABLE IF NOT EXISTS `risk_alerts` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `contract_id` INT NOT NULL COMMENT '合同 ID',
  `alert_type` VARCHAR(50) NOT NULL COMMENT '预警类型',
  `alert_level` VARCHAR(20) NOT NULL COMMENT '预警等级: low/medium/high/critical',
  `title` VARCHAR(200) NOT NULL COMMENT '预警标题',
  `message` TEXT COMMENT '预警内容',
  `source` VARCHAR(50) COMMENT '来源: ai/rule/manual',
  `source_detail` JSON COMMENT '来源详情',
  `status` VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/processing/resolved/ignored',
  `handler_id` INT COMMENT '处理人 ID',
  `handle_comment` TEXT COMMENT '处理意见',
  `handle_time` DATETIME COMMENT '处理时间',
  `related_clause` VARCHAR(100) COMMENT '相关条款',
  `legal_basis` TEXT COMMENT '法律依据',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (`contract_id`) REFERENCES `contracts`(`id`) ON DELETE CASCADE,
  INDEX `idx_risk_contract` (`contract_id`),
  INDEX `idx_risk_level` (`alert_level`),
  INDEX `idx_risk_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='风险预警表';

-- ==============================================================================
-- 7. 用印管理
-- ==============================================================================

CREATE TABLE IF NOT EXISTS `seal_records` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `contract_id` INT NOT NULL COMMENT '合同 ID',
  `contract_no` VARCHAR(50) NOT NULL COMMENT '合同编号',
  `seal_type` VARCHAR(50) NOT NULL COMMENT '用印类型: official/seal_contract/finance',
  `seal_method` VARCHAR(50) COMMENT '用印方式: electronic/physical',
  `status` VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/approved/completed/rejected',
  `approver_id` INT COMMENT '审批人 ID',
  `approver_name` VARCHAR(50) COMMENT '审批人姓名',
  `approval_time` DATETIME COMMENT '审批时间',
  `approval_comment` TEXT COMMENT '审批意见',
  `seal_time` DATETIME COMMENT '用印时间',
  `seal_operator` VARCHAR(50) COMMENT '用印操作人',
  `seal_image_path` VARCHAR(500) COMMENT '用印照片路径',
  `comment` TEXT COMMENT '备注',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (`contract_id`) REFERENCES `contracts`(`id`) ON DELETE CASCADE,
  INDEX `idx_seal_contract` (`contract_id`),
  INDEX `idx_seal_status` (`status`),
  INDEX `idx_seal_type` (`seal_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用印记录表';

-- ==============================================================================
-- 8. 审计日志 (全链路)
-- ==============================================================================

CREATE TABLE IF NOT EXISTS `audit_logs` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL COMMENT '用户 ID',
  `username` VARCHAR(50) NOT NULL COMMENT '用户名',
  `action` VARCHAR(100) NOT NULL COMMENT '操作动作',
  `resource_type` VARCHAR(50) COMMENT '资源类型: contract/approval/seal/risk',
  `resource_id` INT COMMENT '资源 ID',
  `resource_name` VARCHAR(200) COMMENT '资源名称',
  `detail` JSON COMMENT '操作详情 (before/after state)',
  `ip_address` VARCHAR(50) COMMENT 'IP 地址',
  `user_agent` TEXT COMMENT '浏览器信息',
  `status` VARCHAR(20) DEFAULT 'success' COMMENT '操作状态: success/failed',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_audit_user` (`user_id`),
  INDEX `idx_audit_action` (`action`),
  INDEX `idx_audit_resource` (`resource_type`, `resource_id`),
  INDEX `idx_audit_time` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审计日志表';

-- ==============================================================================
-- 9. 合同台账 (只读汇总表)
-- ==============================================================================

CREATE TABLE IF NOT EXISTS `contract_ledger` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `contract_id` INT NOT NULL COMMENT '合同 ID',
  `contract_no` VARCHAR(50) NOT NULL COMMENT '合同编号',
  `title` VARCHAR(200) NOT NULL COMMENT '合同名称',
  `contract_type` VARCHAR(50) COMMENT '合同类型',
  `counterparty_name` VARCHAR(200) COMMENT '相对方名称',
  `amount` DECIMAL(15, 2) COMMENT '合同金额',
  `status` VARCHAR(20) COMMENT '状态',
  `start_date` DATE COMMENT '开始日期',
  `end_date` DATE COMMENT '结束日期',
  `approval_status` VARCHAR(20) COMMENT '审批状态',
  `risk_level` VARCHAR(20) COMMENT '风险等级',
  `creator_name` VARCHAR(50) COMMENT '创建人姓名',
  `department_name` VARCHAR(100) COMMENT '部门名称',
  `created_at` DATETIME COMMENT '创建时间',
  `signed_at` DATETIME COMMENT '签署时间',
  `archived_at` DATETIME COMMENT '归档时间',
  UNIQUE INDEX `idx_ledger_contract` (`contract_id`),
  INDEX `idx_ledger_no` (`contract_no`),
  INDEX `idx_ledger_status` (`status`),
  INDEX `idx_ledger_counterparty` (`counterparty_name`),
  INDEX `idx_ledger_time` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='合同台账汇总表';

-- ==============================================================================
-- 初始数据 (可选)
-- ==============================================================================

INSERT IGNORE INTO `roles` (`id`, `name`, `code`, `description`) VALUES
(1, '超级管理员', 'super_admin', '系统最高权限'),
(2, '部门主管', 'dept_manager', '部门合同审批'),
(3, '法务', 'legal', '合同法务审查'),
(4, '财务', 'finance', '合同财务审批'),
(5, '高管', 'executive', '高管最终审批'),
(6, '起草人', 'draftsman', '合同起草与查询');

-- ==============================================================================
-- 初始化完成
-- ==============================================================================
-- 总表数: 13
-- 核心表: contracts, approval_flows, approval_steps, ai_reviews, audit_logs
-- 版本: 1.0.0
-- ==============================================================================
