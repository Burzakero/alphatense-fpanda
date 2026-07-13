"""
Workspace orchestrator: the piece that makes the engine "multi-client native".

An advisor's Workspace loads a single uploaded file that may contain rows
for many clients, many periods, and multiple scenarios (actual/budget/
prior) at once. It fans out KPI calculation and variance analysis per
client/period pair, and returns a portfolio-level view -- so an advisor
managing dozens of clients gets one call that covers all of them, instead
of re-running the pipeline per client.

Adding a new client to the platform means adding rows to the source file
(or connecting a new Xero org in later phases) -- nothing here needs to
change, which is the point of the multi-tenant design called out in the
product plan.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from app.engine.aging import calculate_aging
from app.engine.cash_flow import project_cash_flow
from app.engine.forecast import ForecastError, generate_forecast
from app.engine.kpis import calculate_kpis
from app.engine.variance import analyze_variance
from app.ingestion.parser import load_financial_statements
from app.models.domain import (
    AgingReport,
    CashFlowForecast,
    FinancialStatement,
    ForecastResult,
    Invoice,
    InvoiceType,
    KPISet,
    Scenario,
    VarianceResult,
)


class ClientReport:
    """All computed output for one client's one period: KPIs + variances vs budget/prior."""

    def __init__(
        self,
        client_id: str,
        period: str,
        actual_kpis: KPISet,
        variances_vs_budget: list[VarianceResult],
        variances_vs_prior: list[VarianceResult],
    ) -> None:
        self.client_id = client_id
        self.period = period
        self.actual_kpis = actual_kpis
        self.variances_vs_budget = variances_vs_budget
        self.variances_vs_prior = variances_vs_prior

    def to_dict(self) -> dict:
        return {
            "client_id": self.client_id,
            "period": self.period,
            "actual_kpis": self.actual_kpis.model_dump(),
            "variances_vs_budget": [v.model_dump() for v in self.variances_vs_budget],
            "variances_vs_prior": [v.model_dump() for v in self.variances_vs_prior],
        }


class Workspace:
    """Loads one source file and computes reports for every client/period found in it."""

    def __init__(self, statements: list[FinancialStatement], invoices: list[Invoice] | None = None):
        self._statements = statements
        # Index by (client_id, period, scenario) for O(1) lookups when pairing
        # actual statements with their budget/prior counterparts.
        self._by_key: dict[tuple[str, str, Scenario], FinancialStatement] = {
            (s.client_id, s.period, s.scenario): s for s in statements
        }
        self._invoices: list[Invoice] = list(invoices) if invoices else []

    @classmethod
    def from_file(cls, path: str | Path) -> "Workspace":
        return cls(load_financial_statements(path))

    @property
    def client_ids(self) -> list[str]:
        return sorted({s.client_id for s in self._statements})

    def _statement(self, client_id: str, period: str, scenario: Scenario) -> FinancialStatement | None:
        return self._by_key.get((client_id, period, scenario))

    def build_client_report(self, client_id: str, period: str) -> ClientReport | None:
        """Build the full report for one client/period, if actual data exists for it."""
        actual_stmt = self._statement(client_id, period, Scenario.ACTUAL)
        if actual_stmt is None:
            return None

        actual_kpis = calculate_kpis(actual_stmt)

        variances_vs_budget: list[VarianceResult] = []
        budget_stmt = self._statement(client_id, period, Scenario.BUDGET)
        if budget_stmt is not None:
            budget_kpis = calculate_kpis(budget_stmt)
            variances_vs_budget = analyze_variance(actual_kpis, budget_kpis, actual_stmt, budget_stmt)

        variances_vs_prior: list[VarianceResult] = []
        prior_stmt = self._statement(client_id, period, Scenario.PRIOR)
        if prior_stmt is not None:
            prior_kpis = calculate_kpis(prior_stmt)
            variances_vs_prior = analyze_variance(actual_kpis, prior_kpis, actual_stmt, prior_stmt)

        return ClientReport(
            client_id=client_id,
            period=period,
            actual_kpis=actual_kpis,
            variances_vs_budget=variances_vs_budget,
            variances_vs_prior=variances_vs_prior,
        )

    def build_portfolio_report(self) -> list[ClientReport]:
        """Build reports for every (client, period) pair that has actual data.

        This is the single call an advisor's dashboard would make to refresh
        every client in their portfolio at once.
        """
        actual_keys = sorted(
            {(s.client_id, s.period) for s in self._statements if s.scenario == Scenario.ACTUAL}
        )
        reports = []
        for client_id, period in actual_keys:
            report = self.build_client_report(client_id, period)
            if report is not None:
                reports.append(report)
        return reports

    def client_history(self, client_id: str) -> list[FinancialStatement]:
        """All ACTUAL statements for one client, across every period on file."""
        return [
            s for s in self._statements
            if s.client_id == client_id and s.scenario == Scenario.ACTUAL
        ]

    def build_forecast(self, client_id: str, periods_ahead: int = 3) -> list[ForecastResult]:
        """Best/base/worst forecast for one client, using all of its actual history.

        Raises ForecastError (via the forecast engine) if the client has
        fewer than 2 periods of actual data on file -- there's no trend to
        project from a single snapshot.
        """
        history = self.client_history(client_id)
        if not history:
            raise ForecastError(f"No actual history on file for client '{client_id}'")
        return generate_forecast(client_id, history, periods_ahead=periods_ahead)

    def build_portfolio_forecast(self, periods_ahead: int = 3) -> dict[str, list[ForecastResult]]:
        """Forecast every client in the portfolio that has enough history to project.

        Clients with fewer than 2 actual periods on file are skipped rather
        than raising, so one thin client doesn't break the whole portfolio
        refresh.
        """
        forecasts: dict[str, list[ForecastResult]] = {}
        for client_id in self.client_ids:
            try:
                forecasts[client_id] = self.build_forecast(client_id, periods_ahead=periods_ahead)
            except ForecastError:
                continue
        return forecasts

    def add_invoices(self, invoices: list[Invoice]) -> None:
        """Attach AR/AP invoices to this workspace, on top of the P&L data already loaded."""
        self._invoices.extend(invoices)

    def build_aging_report(self, client_id: str, invoice_type: InvoiceType, as_of: date) -> AgingReport | None:
        """AR or AP aging for one client, or None if no invoices of that type are on file for them."""
        matching = [inv for inv in self._invoices if inv.client_id == client_id and inv.type == invoice_type]
        if not matching:
            return None
        return calculate_aging(client_id, matching, invoice_type, as_of)

    def build_cash_flow_forecast(
        self, client_id: str, starting_balance: float, as_of: date, weeks_ahead: int = 13
    ) -> CashFlowForecast:
        """Project cash flow for one client from their AR/AP invoices on file.

        Unlike aging, this always returns a result -- a client with no
        invoices on file just gets a flat balance for the whole window,
        which is itself a meaningful answer (no known cash movements).
        """
        matching = [inv for inv in self._invoices if inv.client_id == client_id]
        return project_cash_flow(client_id, matching, starting_balance, as_of, weeks_ahead=weeks_ahead)
