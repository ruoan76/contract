# -*- coding: utf-8 -*-
"""LLM 统一网关 — timeout、重试、日志。"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Optional

import openai
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LLMCallMeta:
    caller: str
    latency_ms: int
    prompt_hash: str
    success: bool
    error_type: Optional[str] = None


class LLMGateway:
    """OpenAI 兼容 LLM 调用封装。"""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.AI_API_KEY,
            base_url=settings.AI_BASE_URL,
            timeout=settings.AI_REQUEST_TIMEOUT,
            max_retries=0,
        )
        self._model = settings.AI_MODEL
        self._temperature = settings.AI_TEMPERATURE
        self._max_tokens = settings.AI_MAX_TOKENS

    async def complete_json(
        self,
        *,
        messages: list[dict[str, str]],
        caller: str,
        system_prompt: str | None = None,
        max_retries: int = 2,
    ) -> tuple[dict[str, Any], LLMCallMeta]:
        """调用 LLM 并解析 JSON 响应。"""
        import time

        prompt_hash = hashlib.sha256(
            json.dumps(messages, ensure_ascii=False)[:8000].encode()
        ).hexdigest()[:12]
        last_error: Optional[str] = None

        for attempt in range(max_retries + 1):
            started = time.monotonic()
            try:
                msgs = list(messages)
                if system_prompt and not any(m.get("role") == "system" for m in msgs):
                    msgs = [{"role": "system", "content": system_prompt}] + msgs

                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=msgs,
                    temperature=self._temperature,
                    max_tokens=self._max_tokens,
                    response_format={"type": "json_object"},
                )
                raw = response.choices[0].message.content or "{}"
                try:
                    parsed = _parse_json_response(raw, strict=True)
                except (json.JSONDecodeError, ValueError):
                    parsed = _parse_json_response(raw, strict=False)
                    if parsed is None:
                        raise ValueError("json_parse")
                latency = int((time.monotonic() - started) * 1000)
                meta = LLMCallMeta(
                    caller=caller,
                    latency_ms=latency,
                    prompt_hash=prompt_hash,
                    success=True,
                )
                logger.info(
                    "ai_review.llm caller=%s latency_ms=%d hash=%s success=true",
                    caller,
                    latency,
                    prompt_hash,
                )
                return parsed, meta

            except openai.APITimeoutError as exc:
                last_error = "timeout"
                logger.warning(
                    "ai_review.llm caller=%s timeout attempt=%d",
                    caller,
                    attempt + 1,
                )
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
            except openai.APIStatusError as exc:
                last_error = f"api_status_{exc.status_code}"
                if exc.status_code >= 500 and attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                logger.error("ai_review.llm caller=%s api_error=%s", caller, exc)
                break
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = "json_parse"
                logger.warning(
                    "ai_review.llm caller=%s json_error=%s attempt=%d",
                    caller,
                    exc,
                    attempt + 1,
                )
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                break
            except Exception as exc:
                last_error = type(exc).__name__
                logger.error("ai_review.llm caller=%s error=%s", caller, exc)
                break

        latency = 0
        meta = LLMCallMeta(
            caller=caller,
            latency_ms=latency,
            prompt_hash=prompt_hash,
            success=False,
            error_type=last_error,
        )
        raise LLMCallError(caller, last_error or "unknown")


def _strip_markdown_fence(text: str) -> str:
    text = text.strip()
    if not text.startswith("```"):
        return text
    lines = text.split("\n")
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines)


def _extract_json_object(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    return ""


def _repair_json_string(text: str) -> str:
    """修正常见 JSON 瑕疵（尾逗号等）。"""
    repaired = re.sub(r",\s*}", "}", text)
    repaired = re.sub(r",\s*]", "]", repaired)
    return repaired


def _parse_json_response(raw_text: str, *, strict: bool = True) -> dict[str, Any] | None:
    """
    解析 LLM JSON。strict=False 时尝试截取与修复，失败返回 None。
    """
    text = _strip_markdown_fence(raw_text)
    candidates: list[str] = []
    if text:
        candidates.append(text)
    extracted = _extract_json_object(text)
    if extracted and extracted not in candidates:
        candidates.append(extracted)

    last_error: Optional[Exception] = None
    for candidate in candidates:
        for variant in (candidate, _repair_json_string(candidate)):
            try:
                data = json.loads(variant)
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError as exc:
                last_error = exc
                continue

    if strict:
        raise ValueError(last_error or "无法解析 JSON")
    return None


class LLMCallError(Exception):
    def __init__(self, caller: str, error_type: str):
        super().__init__(f"LLM call failed: {caller} ({error_type})")
        self.caller = caller
        self.error_type = error_type


_gateway: Optional[LLMGateway] = None


def get_llm_gateway() -> LLMGateway:
    global _gateway
    if _gateway is None:
        _gateway = LLMGateway()
    return _gateway
