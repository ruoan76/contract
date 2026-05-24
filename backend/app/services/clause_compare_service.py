"""条款比对服务（V1.1 MVP：文本 LIMIT 文本 diff）"""
import difflib
from typing import Optional


def compare_texts(
    left_text: str,
    right_text: str,
    left_label: str = "基准版",
    right_label: str = "对比版",
) -> dict:
    left_lines = (left_text or "").splitlines()
    right_lines = (right_text or "").splitlines()
    diff = list(
        difflib.unified_diff(
            left_lines,
            right_lines,
            fromfile=left_label,
            tofile=right_label,
            lineterm="",
        )
    )
    matcher = difflib.SequenceMatcher(None, left_text or "", right_text or "")
    ratio = round(matcher.ratio() * 100, 2)
    changes = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        changes.append(
            {
                "type": tag,
                "left_start": i1,
                "left_end": i2,
                "right_start": j1,
                "right_end": j2,
                "left_snippet": (left_text or "")[i1:i2][:200],
                "right_snippet": (right_text or "")[j1:j2][:200],
            }
        )
    return {
        "similarity_percent": ratio,
        "diff_lines": diff[:200],
        "changes": changes[:50],
        "change_count": len(changes),
    }
