#!/usr/bin/env node
/**
 * 原型回归入口：结构审计 + 完整 E2E
 * 运行：cd prototype && python3 build.py && node _run-tests.mjs
 */
import { runAudit } from './_page-audit.mjs';
import { runE2E } from './_e2e-test.mjs';

console.log('========================================');
console.log('  合同审批原型 — 完整测试');
console.log('========================================\n');

const auditCode = await runAudit({ quietSummary: false });
console.log('\n----------------------------------------\n');
const e2eCode = await runE2E();

const code = auditCode || e2eCode;
process.exit(code);
