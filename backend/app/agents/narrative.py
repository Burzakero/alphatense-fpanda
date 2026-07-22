"""
One-shot AI executive narrative for the PDF report.

Unlike fpa_agent.py's conversational, tool-calling `ask()`, this is a single
plain Claude call: given a client's already-computed report (KPIs +
variances) and whatever else is available (forecast, EBITDA bridge, trend,
working capital), ask Claude for a short executive summary plus bulleted
risks/opportunities. Claude never sees raw data beyond what's passed in --
no tools, nothing to look up -- so a plain `messages.create()` call is the
right shape, not the tool-calling `ask()` machinery. Uses claude-sonnet-5
rather than fpa_agent's claude-opus-4-8 -- this is one-shot summarization
over numbers the engine already computed, not multi-step tool reasoning.

Called from the API route layer only (see app/api/main.py's /report/pdf
route) -- never from reporting/pdf_report.py, which must stay a pure
function. The caller is responsible for catching every failure mode
(AgentNotConfiguredError, network, rate limit, refusal, malformed
response) and falling back to the deterministic summary; this module
never raises on a malformed response -- it degrades to a summary-only
result instead.
"""

from __future__ import annotations

import json
import os

from anthropic import Anthropic
from dotenv import load_dotenv

from app.agents.fpa_agent import AgentNotConfiguredError
from app.engine.workspace import ClientReport
from app.models.domain import AIExecutiveNarrative, ClientTrend, EbitdaBridge, ForecastResult, WorkingCapitalMetrics

load_dotenv()

_MODEL = "claude-sonnet-5"

_SYSTEM_PROMPT = """You are a senior FP&A analyst writing the executive narrative section \
of a one-click PDF report an advisor hands directly to their client. You'll be given a \
client's computed KPIs, variance vs budget/prior, and whatever else is available \
(forecast, EBITDA bridge, 12-month trend, working capital metrics) -- all already \
computed by a deterministic engine. Only reference figures present in what you're given; \
never invent numbers. This is a UK/US advisory product -- always format monetary values \
with the £ symbol (e.g. £113,000), never $ or other currencies, matching the rest of the \
report.

Respond in exactly this format and nothing else:

SUMMARY:
<2-3 sentence executive summary>

RISKS:
- <risk 1>
- <risk 2>

OPPORTUNITIES:
- <opportunity 1>
- <opportunity 2>

Use 0-4 bullets per section. If there is nothing material for a section, keep its \
header and simply omit the bullets under it."""


def _build_prompt(
    report: ClientReport,
    forecast: list[ForecastResult] | None,
    bridge: EbitdaBridge | None,
    trend: ClientTrend | None,
    working_capital: WorkingCapitalMetrics | None,
) -> str:
    payload: dict = dict(report.to_dict())
    if forecast:
        payload["forecast"] = [f.model_dump(mode="json") for f in forecast]
    if bridge is not None:
        payload["ebitda_bridge"] = bridge.model_dump(mode="json")
    if trend is not None:
        payload["trend"] = trend.model_dump(mode="json")
    if working_capital is not None:
        payload["working_capital"] = working_capital.model_dump(mode="json")
    return json.dumps(payload)


def _parse_response(text: str) -> AIExecutiveNarrative:
    """Split on the SUMMARY:/RISKS:/OPPORTUNITIES: markers via plain string ops.

    Degrades gracefully: if the markers aren't found, the whole response
    becomes the summary and risks/opportunities stay empty. Never raises.
    """
    summary_idx = text.find("SUMMARY:")
    risks_idx = text.find("RISKS:")
    opportunities_idx = text.find("OPPORTUNITIES:")

    if summary_idx == -1:
        return AIExecutiveNarrative(summary=text.strip(), risks=[], opportunities=[])

    summary_end = min((i for i in (risks_idx, opportunities_idx) if i != -1), default=len(text))
    summary = text[summary_idx + len("SUMMARY:") : summary_end].strip()

    def _bullets(start: int, end: int) -> list[str]:
        if start == -1:
            return []
        chunk = text[start:end] if end != -1 else text[start:]
        lines = chunk.splitlines()[1:]  # drop the "RISKS:"/"OPPORTUNITIES:" line itself
        return [line.strip().lstrip("-").strip() for line in lines if line.strip().lstrip("-").strip()]

    risks_end = opportunities_idx if opportunities_idx != -1 else -1
    risks = _bullets(risks_idx, risks_end)
    opportunities = _bullets(opportunities_idx, -1)

    return AIExecutiveNarrative(summary=summary, risks=risks, opportunities=opportunities)


def generate_narrative(
    report: ClientReport,
    forecast: list[ForecastResult] | None = None,
    bridge: EbitdaBridge | None = None,
    trend: ClientTrend | None = None,
    working_capital: WorkingCapitalMetrics | None = None,
) -> AIExecutiveNarrative:
    """Generate an AI executive summary + risks + opportunities for one client's report.

    Raises AgentNotConfiguredError if ANTHROPIC_API_KEY isn't set -- the
    caller (the /report/pdf route) is expected to catch this, and any other
    exception, and fall back to the deterministic summary.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise AgentNotConfiguredError("ANTHROPIC_API_KEY is not configured.")

    client = Anthropic()
    response = client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        thinking={"type": "disabled"},
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_prompt(report, forecast, bridge, trend, working_capital)}],
    )
    text = next((b.text for b in response.content if b.type == "text"), "")
    return _parse_response(text)
