#!/usr/bin/env python3
"""
Quick end-to-end demo of the FP&A engine.

Loads the multi-client sample CSV, computes KPIs and variance analysis for
every client/period found in it, and prints an executive-style summary --
this is the CLI-level stand-in for the "generate the executive report with
one click" feature until the PDF export and API layers are built.

Usage:
    python run_demo.py [path/to/financials.csv]
"""

from __future__ import annotations

import sys
from pathlib import Path

from app.engine.forecast import ForecastError
from app.engine.variance import material_variances
from app.engine.workspace import Workspace


def print_forecast(client_id: str, forecasts) -> None:
    print(f"\n  Forecast (next periods) -- {client_id}:")
    by_period: dict[str, dict] = {}
    for f in forecasts:
        by_period.setdefault(f.period, {})[f.scenario.value] = f

    for period in sorted(by_period):
        row = by_period[period]
        print(f"    {period}:")
        for scenario_name in ("best", "base", "worst"):
            f = row.get(scenario_name)
            if f is None:
                continue
            print(f"      {scenario_name:>5}:  revenue {f.revenue:>11,.0f}   EBITDA {f.ebitda:>11,.0f}")
        base = row.get("base")
        if base is not None:
            print(f"      assumptions: {base.assumptions}")


def print_report(report) -> None:
    k = report.actual_kpis
    print(f"\n{'=' * 70}")
    print(f"Client: {report.client_id}   Period: {report.period}")
    print(f"{'=' * 70}")
    print(f"  Revenue:        {k.revenue:>12,.0f}")
    print(f"  Gross Profit:   {k.gross_profit:>12,.0f}   ({k.gross_margin_pct}% margin)")
    print(f"  EBITDA:         {k.ebitda:>12,.0f}   ({k.ebitda_margin_pct}% margin)")
    print(f"  Net Income:     {k.net_income:>12,.0f}   ({k.net_margin_pct}% margin)")

    for label, results in (("vs Budget", report.variances_vs_budget), ("vs Prior Period", report.variances_vs_prior)):
        material = material_variances(results)
        print(f"\n  Material variances {label}:")
        if not material:
            print("    (none -- all KPIs within threshold)")
        for v in material:
            flag = "!!" if v.severity.value == "high" else "! "
            print(f"    [{flag}] {v.narrative}")


def main() -> None:
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "sample_data" / "sample_financials.csv"
    print(f"Loading: {csv_path}")

    workspace = Workspace.from_file(csv_path)
    print(f"Clients found in portfolio: {', '.join(workspace.client_ids)}")

    # Print the most recent period's report per client (the historical
    # months are mainly there to give the forecast engine a trend to learn
    # from -- the exec summary an advisor cares about is the latest one).
    latest_period_per_client = {}
    for report in workspace.build_portfolio_report():
        latest_period_per_client[report.client_id] = report

    for client_id in workspace.client_ids:
        print_report(latest_period_per_client[client_id])
        try:
            forecasts = workspace.build_forecast(client_id, periods_ahead=3)
            print_forecast(client_id, forecasts)
        except ForecastError as exc:
            print(f"\n  Forecast unavailable for {client_id}: {exc}")

    print(f"\n{'=' * 70}\nDone.\n")


if __name__ == "__main__":
    main()
