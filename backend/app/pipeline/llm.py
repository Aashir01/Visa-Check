"""Multi-provider LLM client wrapper with cost accounting and a per-check budget.

Supports Anthropic (Claude) and DeepSeek.  §9 names "LLM cost per check exceeds
price" as a live risk, so this module enforces a budget rather than merely
reporting one: once a check has spent ``llm_budget_usd_per_check``, further
calls are refused and the pipeline degrades to deterministic checks only.
"""

from __future__ import annotations

import base64
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

import httpx

from ..config import settings

log = logging.getLogger(__name__)


@dataclass
class LlmCall:
    kind: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    usd: float = 0.0
    ok: bool = True
    error: str | None = None


@dataclass
class LlmUsage:
    """Accumulates spend across one check."""

    calls: list[LlmCall] = field(default_factory=list)

    @property
    def usd(self) -> float:
        return round(sum(c.usd for c in self.calls), 6)

    @property
    def tokens_in(self) -> int:
        return sum(c.tokens_in for c in self.calls)

    @property
    def tokens_out(self) -> int:
        return sum(c.tokens_out for c in self.calls)

    def remaining(self) -> float:
        return max(0.0, settings.llm_budget_usd_per_check - self.usd)

    def exhausted(self) -> bool:
        return self.usd >= settings.llm_budget_usd_per_check


def price(tokens_in: int, tokens_out: int) -> float:
    return round(
        tokens_in / 1_000_000 * settings.llm_price_in_per_mtok
        + tokens_out / 1_000_000 * settings.llm_price_out_per_mtok,
        6,
    )


def extract_json(text: str) -> dict | list | None:
    """Pull the first JSON object/array out of a model response."""
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fenced:
        text = fenced.group(1)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for opener, closer in (("{", "}"), ("[", "]")):
        start, end = text.find(opener), text.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    return None


# ---------------------------------------------------------------------------
#  Provider backends
# ---------------------------------------------------------------------------

class _AnthropicBackend:
    """Calls the Anthropic Messages API via the official SDK."""

    def __init__(self, api_key: str):
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)

    def complete(
        self,
        model: str,
        system: str,
        messages: list[dict],
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, int, int]:
        resp = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=messages,
        )
        ti = getattr(resp.usage, "input_tokens", 0) or 0
        to = getattr(resp.usage, "output_tokens", 0) or 0
        text = "".join(
            block.text for block in resp.content if getattr(block, "type", "") == "text"
        )
        return text, ti, to

    def transcribe_image(self, model: str, png: bytes) -> str | None:
        text, _ti, _to = self.complete(
            model=model,
            system=(
                "You transcribe scanned travel and financial documents. Return the "
                "text exactly as it appears, preserving line breaks, numbers and "
                "dates verbatim. Transcribe any passport MRZ band character for "
                "character on its own lines. Return only the transcription."
            ),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": base64.standard_b64encode(png).decode("ascii"),
                            },
                        },
                        {"type": "text", "text": "Transcribe this document."},
                    ],
                }
            ],
            max_tokens=3000,
            temperature=0.0,
        )
        return text


class _DeepSeekBackend:
    """Calls the DeepSeek API (OpenAI-compatible) via httpx."""

    def __init__(self, api_key: str, base_url: str):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=120.0)

    def _call(self, endpoint: str, payload: dict) -> dict:
        url = f"{self._base_url}/{endpoint.lstrip('/')}"
        resp = self._client.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        return resp.json()

    def complete(
        self,
        model: str,
        system: str,
        messages: list[dict],
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, int, int]:
        # DeepSeek expects system as a top-level message, not a separate param
        api_messages: list[dict] = []
        if system:
            api_messages.append({"role": "system", "content": system})

        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if isinstance(content, list):
                # Flatten content blocks for DeepSeek (text + images)
                parts: list[dict] = []
                for block in content:
                    if block.get("type") == "text":
                        parts.append({"type": "text", "text": block.get("text", "")})
                    elif block.get("type") == "image":
                        src = block.get("source", {})
                        parts.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{src.get('media_type', 'image/png')};base64,{src.get('data', '')}"
                            },
                        })
                api_messages.append({"role": role, "content": parts})
            else:
                api_messages.append({"role": role, "content": str(content)})

        body = {
            "model": model,
            "messages": api_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        data = self._call("chat/completions", body)
        choice = (data.get("choices") or [{}])[0]
        text = choice.get("message", {}).get("content", "") or ""
        ti = (data.get("usage") or {}).get("prompt_tokens", 0) or 0
        to = (data.get("usage") or {}).get("completion_tokens", 0) or 0
        return text, ti, to

    def transcribe_image(self, model: str, png: bytes) -> str | None:
        text, _ti, _to = self.complete(
            model=model,
            system=(
                "You transcribe scanned travel and financial documents. Return the "
                "text exactly as it appears, preserving line breaks, numbers and "
                "dates verbatim. Transcribe any passport MRZ band character for "
                "character on its own lines. Return only the transcription."
            ),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": base64.standard_b64encode(png).decode("ascii"),
                            },
                        },
                        {"type": "text", "text": "Transcribe this document."},
                    ],
                }
            ],
            max_tokens=3000,
            temperature=0.0,
        )
        return text


# ---------------------------------------------------------------------------
#  Unified client
# ---------------------------------------------------------------------------

class LlmClient:
    def __init__(self, usage: LlmUsage | None = None, *, enabled: bool = True):
        self.usage = usage or LlmUsage()
        self.model = settings.llm_model
        self._backend: Any = None
        self._provider_name = ""
        self.enabled = enabled

        provider = settings.llm_provider.lower()

        if provider == "deepseek" and settings.deepseek_api_key:
            try:
                self._backend = _DeepSeekBackend(
                    settings.deepseek_api_key, settings.deepseek_base_url
                )
                self._provider_name = "deepseek"
                # Sensible model default if still on a Claude model name
                if self.model.startswith("claude-"):
                    self.model = "deepseek-chat"
            except Exception as exc:
                log.warning("DeepSeek client unavailable: %s", exc)

        elif provider == "anthropic" and settings.anthropic_api_key:
            try:
                self._backend = _AnthropicBackend(settings.anthropic_api_key)
                self._provider_name = "anthropic"
            except Exception as exc:
                log.warning("Anthropic client unavailable: %s", exc)

        # Fallback: if the preferred provider has no key, try the other one
        if self._backend is None:
            if settings.deepseek_api_key:
                try:
                    self._backend = _DeepSeekBackend(
                        settings.deepseek_api_key, settings.deepseek_base_url
                    )
                    self._provider_name = "deepseek"
                    if self.model.startswith("claude-"):
                        self.model = "deepseek-chat"
                except Exception as exc:
                    log.warning("DeepSeek fallback unavailable: %s", exc)
            elif settings.anthropic_api_key:
                try:
                    self._backend = _AnthropicBackend(settings.anthropic_api_key)
                    self._provider_name = "anthropic"
                except Exception as exc:
                    log.warning("Anthropic fallback unavailable: %s", exc)

    @property
    def configured(self) -> bool:
        """Whether the deployment could call ANY model."""
        return bool(
            settings.llm_enabled
            and (settings.anthropic_api_key or settings.deepseek_api_key)
        )

    @property
    def available(self) -> bool:
        return (
            self.enabled
            and self._backend is not None
            and not self.usage.exhausted()
        )

    @property
    def provider(self) -> str:
        return self._provider_name

    # -- core call ---------------------------------------------------------

    def complete(
        self,
        *,
        kind: str,
        system: str,
        content: list | str,
        max_tokens: int | None = None,
        temperature: float = 0.0,
    ) -> str | None:
        if self._backend is None:
            return None
        if self.usage.exhausted():
            log.info("LLM budget exhausted for this check; skipping %s call", kind)
            self.usage.calls.append(
                LlmCall(kind=kind, model=self.model, ok=False, error="budget_exhausted")
            )
            return None

        messages = [
            {
                "role": "user",
                "content": content if isinstance(content, list) else [
                    {"type": "text", "text": content}
                ],
            }
        ]
        try:
            text, ti, to = self._backend.complete(
                model=self.model,
                system=system,
                messages=messages,
                max_tokens=max_tokens or settings.llm_max_tokens,
                temperature=temperature,
            )
        except Exception as exc:
            log.warning("LLM call %s failed: %s", kind, exc)
            self.usage.calls.append(
                LlmCall(kind=kind, model=self.model, ok=False, error=str(exc)[:300])
            )
            return None

        self.usage.calls.append(
            LlmCall(
                kind=kind,
                model=self.model,
                tokens_in=ti,
                tokens_out=to,
                usd=price(ti, to),
            )
        )
        return text

    def complete_json(self, **kwargs) -> dict | list | None:
        return extract_json(self.complete(**kwargs) or "")

    # -- vision transcription (opt-in OCR provider) ------------------------

    def transcribe_image(self, png: bytes) -> str | None:
        if self._backend is None:
            return None
        if self.usage.exhausted():
            log.info("LLM budget exhausted; skipping vision transcription")
            return None
        try:
            text = self._backend.transcribe_image(self.model, png)
            # Approximate token count for the image transcription
            ti = 2000  # rough estimate for a page image
            to = len(text.split()) if text else 0
            self.usage.calls.append(
                LlmCall(
                    kind="vision",
                    model=self.model,
                    tokens_in=ti,
                    tokens_out=to,
                    usd=price(ti, to),
                )
            )
            return text
        except Exception as exc:
            log.warning("Vision transcription failed: %s", exc)
            return None
