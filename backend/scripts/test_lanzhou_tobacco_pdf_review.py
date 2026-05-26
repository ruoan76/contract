#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兰州烟草扫描 PDF 端到端验收：parse → 建单 → upload → AI 审查。

用法（需 API + MLX + EasyOCR）:
  cd backend && source .venv/bin/activate
  python scripts/test_lanzhou_tobacco_pdf_review.py
  python scripts/test_lanzhou_tobacco_pdf_review.py --pdf /path/to/contract.pdf --skip-review
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx

DEFAULT_PDF = (
    "/Users/tianfch/Downloads/"
    "甘肃省烟草公司兰州市公司2018年卷烟营销网建信息化项目建设合同-195.8万.pdf"
)
BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
USERNAME = os.environ.get("API_USER", "drafter1")
PASSWORD = os.environ.get("API_PASSWORD", "123456")
PARSE_TIMEOUT = float(os.environ.get("OCR_PARSE_TIMEOUT", "900"))
REVIEW_TIMEOUT = float(os.environ.get("AI_REVIEW_TIMEOUT", "1800"))


def _login(client: httpx.Client) -> str:
    r = client.post(
        f"{BASE_URL}/api/v1/system/login",
        params={"username": USERNAME, "password": PASSWORD},
    )
    r.raise_for_status()
    data = r.json()
    if data.get("code") != 200:
        raise RuntimeError(f"登录失败: {data}")
    token = data["data"]["token"]
    return token


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def main() -> int:
    parser = argparse.ArgumentParser(description="扫描 PDF 合同审查验收")
    parser.add_argument("--pdf", default=DEFAULT_PDF, help="合同 PDF 路径")
    parser.add_argument("--skip-review", action="store_true", help="仅测解析与建单")
    parser.add_argument(
        "--contract-id",
        type=int,
        default=None,
        help="已有合同 ID：跳过 parse/建单/上传，仅校验或重跑审查",
    )
    parser.add_argument("--amount", type=float, default=1_958_000.0)
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not args.contract_id and not pdf_path.is_file():
        print(f"错误: 找不到 PDF: {pdf_path}", file=sys.stderr)
        return 1

    t0 = time.perf_counter()
    timings: dict[str, float] = {}

    with httpx.Client(timeout=httpx.Timeout(PARSE_TIMEOUT)) as client:
        print("1) 登录 …")
        token = _login(client)
        h = _headers(token)

        char_count = 0
        ocr_used = False

        if args.contract_id:
            contract_id = args.contract_id
            print(f"2–4) 跳过，使用已有合同 contract_id={contract_id}")
        else:
            print(f"2) 解析 PDF（OCR 可能较慢）: {pdf_path.name}")
            t_parse = time.perf_counter()
            with pdf_path.open("rb") as f:
                r = client.post(
                    f"{BASE_URL}/api/v1/contracts/parse",
                    headers=h,
                    files={"file": (pdf_path.name, f, "application/pdf")},
                )
            r.raise_for_status()
            parse_body = r.json()
            if parse_body.get("code") != 200:
                print("解析失败:", parse_body, file=sys.stderr)
                return 1
            pdata = parse_body["data"]
            fields = pdata.get("fields") or {}
            char_count = pdata.get("char_count") or fields.get("char_count") or 0
            ocr_used = pdata.get("ocr_used") or fields.get("ocr_used")
            full_text = fields.get("full_text") or fields.get("text_preview") or ""
            timings["parse_sec"] = time.perf_counter() - t_parse

            print(
                f"   字数={char_count}, ocr_used={ocr_used}, "
                f"耗时={timings['parse_sec']:.1f}s"
            )
            if char_count < 1000:
                print(
                    f"警告: 正文字数 {char_count} < 1000，OCR 可能失败或未启用",
                    file=sys.stderr,
                )
            if not ocr_used and char_count < 200:
                print("错误: 扫描件未触发 OCR 且几乎无正文", file=sys.stderr)
                return 1

            title = fields.get("title") or pdf_path.stem[:120]
            amount = fields.get("amount") or args.amount
            contract_type = fields.get("contract_type") or "service"
            counterparty = (
                fields.get("party_b") or fields.get("party_a") or "待确认相对方"
            )

            print("3) 创建合同草稿 …")
            t_create = time.perf_counter()
            r = client.post(
                f"{BASE_URL}/api/v1/contracts/",
                headers={**h, "Content-Type": "application/json"},
                json={
                    "title": title,
                    "contract_type": contract_type,
                    "counterparty_name": str(counterparty)[:80],
                    "amount": amount,
                    "content": full_text,
                },
                timeout=60.0,
            )
            r.raise_for_status()
            cbody = r.json()
            contract_id = cbody["data"]["id"]
            timings["create_sec"] = time.perf_counter() - t_create
            print(f"   contract_id={contract_id}, amount={amount}")

            print("4) 上传 PDF 附件 …")
            t_up = time.perf_counter()
            with pdf_path.open("rb") as f:
                r = client.post(
                    f"{BASE_URL}/api/v1/contracts/{contract_id}/upload",
                    headers=h,
                    files={"file": (pdf_path.name, f, "application/pdf")},
                    timeout=PARSE_TIMEOUT,
                )
            r.raise_for_status()
            udata = r.json().get("data") or {}
            char_count = udata.get("char_count") or char_count
            ocr_used = udata.get("ocr_used") or ocr_used
            timings["upload_sec"] = time.perf_counter() - t_up
            print(
                f"   char_count={char_count}, ocr_used={ocr_used}, "
                f"耗时={timings['upload_sec']:.1f}s"
            )

        if args.skip_review:
            timings["total_sec"] = time.perf_counter() - t0
            print("\n=== 验收摘要（跳过审查）===")
            print(json.dumps({"contract_id": contract_id, **timings}, ensure_ascii=False, indent=2))
            return 0

        review_resp: dict = {}
        review_id = None
        review_status_immediate = None
        r = client.get(
            f"{BASE_URL}/api/v1/ai-review/contracts/{contract_id}/latest-review",
            headers=h,
            timeout=60.0,
        )
        existing = (r.json().get("data") or {}) if r.status_code == 200 else {}
        if existing.get("review_status") in (
            "ai_done",
            "reviewed",
            "confirmed",
            "done",
        ):
            print("5) 已有完成审查，跳过重新触发 …")
            review_id = existing.get("review_id")
            review_status_immediate = existing.get("review_status")
            timings["review_sec"] = 0.0
        else:
            print("5) 发起 AI 审查（同步 MLX，可能数分钟）…")
            t_review = time.perf_counter()
            r = client.post(
                f"{BASE_URL}/api/v1/ai-review/review",
                headers={**h, "Content-Type": "application/json"},
                json={"contract_id": contract_id},
                timeout=REVIEW_TIMEOUT,
            )
            if r.status_code >= 400:
                print("审查失败:", r.status_code, r.text[:2000], file=sys.stderr)
                return 1
            review_resp = r.json().get("data") or {}
            review_id = review_resp.get("review_id")
            review_status_immediate = review_resp.get("status")
            timings["review_sec"] = time.perf_counter() - t_review
        print(f"   review_id={review_id}, status={review_status_immediate}")

        print("6) 拉取最新审查结果 …")
        latest: dict = {}
        status = review_status_immediate
        for _ in range(5):
            r = client.get(
                f"{BASE_URL}/api/v1/ai-review/contracts/{contract_id}/latest-review",
                headers=h,
                timeout=60.0,
            )
            r.raise_for_status()
            latest = r.json().get("data") or {}
            status = latest.get("review_status") or status
            if status in ("ai_done", "reviewed", "confirmed", "done"):
                break
            time.sleep(1.0)
        completeness = latest.get("review_completeness")
        if not completeness and isinstance(latest.get("summary"), dict):
            completeness = latest["summary"].get("review_completeness")
        gates = latest.get("gates")

        rule_count = 0
        llm_count = 0
        if review_id:
            r2 = client.get(
                f"{BASE_URL}/api/v1/ai-review/{review_id}/issues",
                headers=h,
                params={"page_size": 200},
                timeout=60.0,
            )
            if r2.status_code == 200:
                issues = (r2.json().get("data") or {}).get("items") or []
                for it in issues:
                    src = (it.get("source") or "").lower()
                    if src == "rule":
                        rule_count += 1
                    elif src in ("llm", "ai", "mlx"):
                        llm_count += 1

        timings["total_sec"] = time.perf_counter() - t0
        ok = status in ("ai_done", "reviewed", "confirmed", "done")
        summary = {
            "contract_id": contract_id,
            "review_id": review_id,
            "review_status": status,
            "review_completeness": completeness,
            "rule_issues": rule_count,
            "llm_issues": llm_count,
            "gates_keys": list(gates.keys()) if isinstance(gates, dict) else None,
            "ocr_used": ocr_used,
            "char_count": char_count,
            **{k: round(v, 1) for k, v in timings.items()},
        }
        print("\n=== 验收摘要 ===")
        print(json.dumps(summary, ensure_ascii=False, indent=2))

        if not ok:
            print(f"失败: 审查状态为 {status}", file=sys.stderr)
            return 1
        if rule_count < 1:
            print("警告: 未发现 rule 来源 issue（金额规则可能未命中）", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
