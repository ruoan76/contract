#!/usr/bin/env python3
"""导出 OpenAPI JSON 供前端联调与 Postman 导入。"""
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import app  # noqa: E402


def main() -> None:
    out_path = BACKEND_DIR / "openapi.json"
    schema = app.openapi()
    out_path.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"OpenAPI exported: {out_path} ({len(schema.get('paths', {}))} paths)")


if __name__ == "__main__":
    main()
