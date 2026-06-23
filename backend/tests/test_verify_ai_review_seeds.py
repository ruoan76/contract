# -*- coding: utf-8 -*-
"""种子 manifest 门禁（CI 可跑）。"""
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
SCRIPT = BACKEND / "scripts" / "verify_ai_review_seeds.py"


def test_verify_ai_review_seeds_script():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(BACKEND),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
