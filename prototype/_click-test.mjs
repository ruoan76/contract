/**
 * 原型 E2E 回归（兼容入口，等价于 _e2e-test.mjs）
 * 运行：cd prototype && node _click-test.mjs
 */
import { runE2E } from './_e2e-test.mjs';

const code = await runE2E();
process.exit(code);
