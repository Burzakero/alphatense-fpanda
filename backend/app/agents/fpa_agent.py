"""
Conversational FP&A agent.

Wraps a workspace's already-computed KPIs, variance analysis, forecast, and
aging as tools for Claude to call. The agent never computes a number itself
-- it decides which of the engine's existing outputs answers the advisor's
question, calls the matching tool, and narrates over the result. This is
what closes the gap between the deterministic engine (reports an advisor
looks at) and an actual conversational copilot.

Deliberately stateless like the rest of the API: the caller passes in the
prior turns (`history`) and gets the updated list back, rather than this
module keeping its own session store.
"""

from __future__ import annotations

import json
import os
from datetime import date

from anthropic import Anthropic, beta_tool
from dotenv import load_dotenv

from app.engine.forecast import ForecastError
from app.engine.workspace import Workspace
from app.models.domain import InvoiceType

load_dotenv()

_MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = """You are a senior FP&A analyst embedded in a financial advisory's platform. \
You have tools that expose the already-computed KPIs, variance analysis, \
forecasts, AR/AP aging, and AR/AP-based cash flow projections for the \
clients in this workspace. Cash flow projections need a starting_balance \
from the advisor (there's no bank feed) and only reflect invoices with a \
due date on file -- not unbilled recurring costs like payroll or rent.

Ground every number you state in a tool result -- never estimate or restate \
a figure from earlier in the conversation without a fresh tool call if \
precision matters. If a question needs data you don't have a tool for \
(e.g. cash flow projections, data outside this workspace), say so plainly \
instead of guessing. Keep answers concise and quote the specific numbers \
the advisor asked about, not the whole report."""


class AgentNotConfiguredError(RuntimeError):
    """Raised when ANTHROPIC_API_KEY isn't set. The chat endpoint turns this into a 503."""


def _portfolio_summary(workspace: Workspace) -> str:
    reports = workspace.build_portfolio_report()
    return json.dumps([r.to_dict() for r in reports])


def _client_report(workspace: Workspace, client_id: str, period: str) -> str:
    report = workspace.build_client_report(client_id, period)
    if report is None:
        return f"No actual data on file for client '{client_id}' in period '{period}'."
    return json.dumps(report.to_dict())


def _client_forecast(workspace: Workspace, client_id: str, periods_ahead: int = 3) -> str:
    try:
        results = workspace.build_forecast(client_id, periods_ahead=periods_ahead)
    except ForecastError as exc:
        return str(exc)
    return json.dumps([r.model_dump() for r in results])


def _client_aging(workspace: Workspace, client_id: str, invoice_type: str, as_of: str) -> str:
    try:
        parsed_type = InvoiceType(invoice_type.strip().lower())
    except ValueError:
        return f"Invalid invoice_type '{invoice_type}' -- expected 'ar' or 'ap'."
    try:
        as_of_date = date.fromisoformat(as_of)
    except ValueError:
        return f"Invalid as_of date '{as_of}' -- expected YYYY-MM-DD."

    report = workspace.build_aging_report(client_id, parsed_type, as_of_date)
    if report is None:
        return f"No {parsed_type.value.upper()} invoices on file for client '{client_id}'."
    return json.dumps(report.model_dump(mode="json"))


def _client_cash_flow(workspace: Workspace, client_id: str, starting_balance: float, as_of: str, weeks_ahead: int = 13) -> str:
    try:
        as_of_date = date.fromisoformat(as_of)
    except ValueError:
        return f"Invalid as_of date '{as_of}' -- expected YYYY-MM-DD."

    forecast = workspace.build_cash_flow_forecast(client_id, starting_balance, as_of_date, weeks_ahead=weeks_ahead)
    return json.dumps(forecast.model_dump(mode="json"))


def _build_tools(workspace: Workspace) -> list:
    """Wrap the plain functions above as @beta_tool closures bound to this workspace.

    Kept as thin delegations (not the implementation itself) so the actual
    logic is testable as plain Python functions, independent of how the SDK
    decorator handles direct invocation.
    """

    @beta_tool
    def get_portfolio_summary() -> str:
        """Get KPIs and variance analysis for every client/period on file in this workspace.

        Use this for questions about "the portfolio" or "all clients", or to
        discover which client_ids and periods are available before calling
        one of the other tools.
        """
        return _portfolio_summary(workspace)

    @beta_tool
    def get_client_report(client_id: str, period: str) -> str:
        """Get KPIs and variance vs budget/prior for one client's one period.

        Args:
            client_id: the client identifier, e.g. "beacon-partners".
            period: the period label, e.g. "2026-06".
        """
        return _client_report(workspace, client_id, period)

    @beta_tool
    def get_client_forecast(client_id: str, periods_ahead: int = 3) -> str:
        """Get the best/base/worst forecast for one client's next N periods.

        Args:
            client_id: the client identifier, e.g. "beacon-partners".
            periods_ahead: how many periods ahead to project.
        """
        return _client_forecast(workspace, client_id, periods_ahead)

    @beta_tool
    def get_client_aging(client_id: str, invoice_type: str, as_of: str) -> str:
        """Get AR or AP aging (buckets by days overdue) for one client.

        Args:
            client_id: the client identifier, e.g. "beacon-partners".
            invoice_type: "ar" for accounts receivable or "ap" for accounts payable.
            as_of: the date to age invoices against, in YYYY-MM-DD format.
        """
        return _client_aging(workspace, client_id, invoice_type, as_of)

    @beta_tool
    def get_client_cash_flow(client_id: str, starting_balance: float, as_of: str, weeks_ahead: int = 13) -> str:
        """Project a client's cash balance week by week from their AR/AP invoices on file.

        Only accounts for invoices with a due date already loaded -- doesn't
        include recurring costs that aren't billed as an AP invoice (payroll,
        rent, etc.). Say so if the advisor asks about cash flow more broadly.

        Args:
            client_id: the client identifier, e.g. "beacon-partners".
            starting_balance: the client's current cash balance (advisor-supplied,
                there's no bank feed in this system).
            as_of: the date the projection starts from, in YYYY-MM-DD format.
            weeks_ahead: how many weeks ahead to project (13 is the standard horizon).
        """
        return _client_cash_flow(workspace, client_id, starting_balance, as_of, weeks_ahead)

    return [
        get_portfolio_summary,
        get_client_report,
        get_client_forecast,
        get_client_aging,
        get_client_cash_flow,
    ]


def ask(workspace: Workspace, message: str, history: list[dict] | None = None) -> tuple[str, list[dict]]:
    """Answer one advisor question, grounded in the workspace's computed data.

    Returns (reply_text, updated_history) -- the caller stores and resends
    `updated_history` on the next turn.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise AgentNotConfiguredError("ANTHROPIC_API_KEY is not configured.")

    client = Anthropic()
    messages = list(history or [])
    messages.append({"role": "user", "content": message})

    runner = client.beta.messages.tool_runner(
        model=_MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        thinking={"type": "adaptive"},
        tools=_build_tools(workspace),
        messages=messages,
    )
    final_message = runner.until_done()

    reply = next((b.text for b in final_message.content if b.type == "text"), "")
    messages.append({"role": "assistant", "content": reply})
    return reply, messages
