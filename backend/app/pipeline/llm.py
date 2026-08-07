"""Anthropic client wrapper with cost accounting and a per-check budget.

§9 names "LLM cost per check exceeds price" as a live risk, so this module
enforces a budget rather than merely reporting one: once a check has spent
``llm_budget_usd_per_check``, further calls are refused and the pipeline
degrades to deterministic checks only. A report built without the LLM is
still useful — missing documents, name mismatches, balances and dates are all
computed in code.
"""

from __future__ import annotations

import base64
import json
import logging
import re
from dataclasses import dataclass, field

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


class LlmClient:
    def __init__(self, usage: LlmUsage | None = None, *, enabled: bool = True):
        self.usage = usage or LlmUsage()
        self.model = settings.llm_model
        self._client = None
        # `enabled` is the per-check tier decision; `settings.llm_enabled` and
        # the API key are deployment-level. Both must hold for a call to run.
        self.enabled = enabled
        if enabled and settings.llm_enabled and settings.anthropic_api_key:
            try:
                from anthropic import Anthropic

                self._client = Anthropic(api_key=settings.anthropic_api_key)
            except Exception as exc:  # noqa: BLE001
                log.warning("Anthropic client unavailable: %s", exc)

    @property
    def configured(self) -> bool:
        """Whether the deployment could call the model at all."""
        return bool(settings.llm_enabled and settings.anthropic_api_key)

    @property
    def available(self) -> bool:
        return (
            self.enabled
            and self._client is not None
            and not self.usage.exhausted()
        )

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
        if self._client is None:
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
            resp = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens or settings.llm_max_tokens,
                temperature=temperature,
                system=system,
                messages=messages,
            )
        except Exception as exc:  # noqa: BLE001 - never fail a check on LLM error
            log.warning("LLM call %s failed: %s", kind, exc)
            self.usage.calls.append(
                LlmCall(kind=kind, model=self.model, ok=False, error=str(exc)[:300])
            )
            return None

        ti = getattr(resp.usage, "input_tokens", 0) or 0
        to = getattr(resp.usage, "output_tokens", 0) or 0
        self.usage.calls.append(
            LlmCall(
                kind=kind,
                model=self.model,
                tokens_in=ti,
                tokens_out=to,
                usd=price(ti, to),
            )
        )
        return "".join(
            block.text for block in resp.content if getattr(block, "type", "") == "text"
        )

    def complete_json(self, **kwargs) -> dict | list | None:
        return extract_json(self.complete(**kwargs) or "")

    # -- vision transcription (opt-in OCR provider) ------------------------

    def transcribe_image(self, png: bytes) -> str | None:
        return self.complete(
            kind="vision",
            system=(
                "You transcribe scanned travel and financial documents. Return the "
                "text exactly as it appears, preserving line breaks, numbers and "
                "dates verbatim. Transcribe any passport MRZ band character for "
                "character on its own lines. Return only the transcription."
            ),
            content=[
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
            max_tokens=3000,
        )
