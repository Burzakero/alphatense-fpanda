"""
Domain models for the Finance Alphatense AI FP&A engine.

Architecture note (multi-tenant by design):
    Advisor -> Client -> FinancialStatement (per period, per scenario)

An Advisor manages many Clients from a single workspace. Every downstream
calculation (KPIs, variance analysis) operates on a single Client's data at
a time, so adding clients never requires touching the engine itself -- the
Workspace orchestrator (see engine/workspace.py) is what fans out across
clients. This mirrors the "multi-tenant native" positioning in the product
plan: the advisor never has to leave a single panel to manage dozens of
clients.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Scenario(str, Enum):
    """Which version of the numbers a line item represents."""

    ACTUAL = "actual"
    BUDGET = "budget"
    PRIOR = "prior"  # same period, prior year -- used for YoY comparisons


class AccountCategory(str, Enum):
    """Coarse P&L categories used for KPI roll-ups and variance drivers."""

    REVENUE = "revenue"
    COGS = "cogs"
    OPEX = "opex"
    OTHER_INCOME = "other_income"
    OTHER_EXPENSE = "other_expense"
    TAX = "tax"


class Advisor(BaseModel):
    """A financial advisory firm using the platform (the paying customer)."""

    advisor_id: str
    name: str


class Client(BaseModel):
    """One of the advisor's end clients -- gets its own isolated workspace."""

    client_id: str
    advisor_id: str
    name: str
    currency: str = "GBP"


class LineItem(BaseModel):
    """A single account balance for a client, period, and scenario."""

    client_id: str
    period: str  # e.g. "2026-06" (monthly) or "2026-Q2"
    scenario: Scenario
    account: str  # e.g. "Marketing", "SaaS Subscriptions"
    category: AccountCategory
    amount: float

    @field_validator("period")
    @classmethod
    def _non_empty_period(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("period must not be empty")
        return v.strip()


class FinancialStatement(BaseModel):
    """All line items for one client, one period, one scenario."""

    client_id: str
    period: str
    scenario: Scenario
    line_items: list[LineItem] = Field(default_factory=list)

    def total(self, category: AccountCategory) -> float:
        return sum(li.amount for li in self.line_items if li.category == category)

    def top_accounts(self, category: AccountCategory, n: int = 3) -> list[LineItem]:
        items = [li for li in self.line_items if li.category == category]
        return sorted(items, key=lambda li: abs(li.amount), reverse=True)[:n]


class KPISet(BaseModel):
    """Calculated KPIs for one client, one period, one scenario."""

    client_id: str
    period: str
    scenario: Scenario

    revenue: float
    cogs: float
    gross_profit: float
    gross_margin_pct: Optional[float]  # None if revenue is 0

    opex: float
    ebitda: float
    ebitda_margin_pct: Optional[float]

    other_income: float
    other_expense: float
    tax: float
    net_income: float
    net_margin_pct: Optional[float]


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class VarianceResult(BaseModel):
    """One KPI's deviation between an actual figure and a comparison basis."""

    client_id: str
    period: str
    kpi_name: str
    comparison_scenario: Scenario  # BUDGET or PRIOR

    actual_value: float
    comparison_value: float
    delta: float
    delta_pct: Optional[float]  # None if comparison_value is 0
    severity: Severity
    narrative: str


class ForecastScenario(str, Enum):
    """Which of the three projections a ForecastResult represents."""

    BEST = "best"
    BASE = "base"
    WORST = "worst"


class ForecastResult(BaseModel):
    """A projected KPI set for one future period, under one scenario.

    Mirrors KPISet's shape so the same reporting/formatting code can render
    forecasts and actuals side by side, plus an `assumptions` narrative
    explaining the growth rates driving the projection -- an advisor
    presenting this to a client needs to be able to say *why* the number is
    what it is, not just see the number.
    """

    client_id: str
    period: str
    scenario: ForecastScenario

    revenue: float
    cogs: float
    gross_profit: float
    gross_margin_pct: Optional[float]

    opex: float
    ebitda: float
    ebitda_margin_pct: Optional[float]

    other_income: float
    other_expense: float
    tax: float
    net_income: float
    net_margin_pct: Optional[float]

    assumptions: str


class InvoiceType(str, Enum):
    """Which side of the ledger an invoice sits on."""

    AR = "ar"  # accounts receivable -- money owed to the client by their customers
    AP = "ap"  # accounts payable -- money the client owes to their vendors


class Invoice(BaseModel):
    """A single AR or AP invoice, open or (partially) paid.

    Distinct from LineItem/FinancialStatement on purpose: aging needs a
    real due_date per invoice to bucket by days overdue, which an
    aggregated per-period P&L line item doesn't carry.
    """

    client_id: str
    invoice_id: str
    type: InvoiceType
    counterparty: str  # customer name (AR) or vendor name (AP)
    issue_date: date
    due_date: date
    amount: float
    amount_paid: float = 0.0

    @property
    def balance(self) -> float:
        return round(self.amount - self.amount_paid, 2)


class AgingBucket(str, Enum):
    """Standard AR/AP aging buckets, by days past due."""

    CURRENT = "current"
    DAYS_1_30 = "1-30"
    DAYS_31_60 = "31-60"
    DAYS_61_90 = "61-90"
    DAYS_90_PLUS = "90+"


class AgingBucketAmount(BaseModel):
    """Total open balance (and invoice count) falling into one aging bucket."""

    bucket: AgingBucket
    amount: float
    invoice_count: int


class AgingReport(BaseModel):
    """AR or AP aging for one client as of a given date."""

    client_id: str
    type: InvoiceType
    as_of: date
    total_outstanding: float
    buckets: list[AgingBucketAmount]
    narrative: str


class CashFlowWeek(BaseModel):
    """One week's projected cash movement, from AR/AP invoices due in that week."""

    week_start: date
    week_end: date
    ar_inflows: float
    ap_outflows: float
    net_change: float
    ending_balance: float


class CashFlowForecast(BaseModel):
    """A 13-week-style cash flow projection for one client, built from AR/AP invoices.

    Deliberately scoped to invoices with a due_date already on file --
    recurring costs that aren't billed as an AP invoice (payroll, rent) are
    not included, to avoid double-counting against opex actuals. See
    `narrative` for the caveat spelled out for whoever's reading it.
    """

    client_id: str
    as_of: date
    starting_balance: float
    weeks: list[CashFlowWeek]
    narrative: str


class EbitdaBridgeStep(BaseModel):
    """One bar in the EBITDA bridge waterfall: a budget/actual anchor total, or a category delta."""

    label: str
    value: float
    is_total: bool


class EbitdaBridge(BaseModel):
    """Budget -> Actual EBITDA walk for one client/period, decomposed by Revenue/COGS/Opex deltas.

    Only meaningful when both an ACTUAL and a BUDGET FinancialStatement
    exist for the period -- see Workspace.build_ebitda_bridge, which
    returns None otherwise (same convention as build_aging_report).
    """

    client_id: str
    period: str
    budget_ebitda: float
    actual_ebitda: float
    steps: list[EbitdaBridgeStep]
    narrative: str


class ClientTrendPoint(BaseModel):
    """One period's headline KPIs, for trend charting."""

    period: str
    revenue: float
    ebitda: float
    net_margin_pct: Optional[float]


class ClientTrend(BaseModel):
    """Revenue/EBITDA/net-margin trend across a client's actual periods on file (most recent N)."""

    client_id: str
    periods: list[str]
    points: list[ClientTrendPoint]
    narrative: str


class WorkingCapitalMetrics(BaseModel):
    """DSO / DPO / Cash Conversion Cycle for one client/period, as of a given date.

    Deliberately excludes a DIO (inventory) term -- this is a services-
    business product and the domain model has no inventory data at all,
    the same class of scope limitation as CashFlowForecast's excluded opex
    run-rate. `days_in_period` is a fixed assumption (default 30), not
    derived from the calendar length of `period`. `ar_outstanding` /
    `ap_outstanding` are read as the current balance on file, not a
    reconstructed historical snapshot as of `as_of` -- Invoice has no
    paid-date field, so this is only precise when `as_of` is at/after the
    data's last update. Both limitations are spelled out in `narrative`.
    """

    client_id: str
    period: str
    as_of: date
    ar_outstanding: float
    ap_outstanding: float
    days_in_period: int
    dso: Optional[float]
    dpo: Optional[float]
    ccc: Optional[float]
    narrative: str


class AIExecutiveNarrative(BaseModel):
    """AI-generated (Claude) executive summary + risks + opportunities for the PDF report.

    Produced by app/agents/narrative.py's one-shot generate_narrative() call
    in the API route layer -- never computed inside reporting/pdf_report.py,
    which must stay a pure function. On any failure the route falls back to
    the deterministic _executive_summary() with empty risks/opportunities.
    """

    summary: str
    risks: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
