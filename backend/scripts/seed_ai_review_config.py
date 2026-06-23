#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 JSON 种子幂等导入 AI 审查配置到数据库。"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.ai_review.config_seed import import_from_json_seeds


async def main() -> None:
    version = datetime.now(timezone.utc).strftime("seed-%Y%m%d%H%M")
    await import_from_json_seeds(version)
    print(f"AI review config imported, version={version}")


if __name__ == "__main__":
    asyncio.run(main())
