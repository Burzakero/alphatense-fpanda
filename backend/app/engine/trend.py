"""
Client trend engine.

Rolls a client's actual-period history into a Revenue/EBITDA/Net-margin
trend, for the "one month is a snapshot, twelve months tells a story"
gap a single-period report leaves open. Reuses engine/kpis.py's KPI math
per period rather than recomputing anything -- this module is purely a
reshape of already-correct numbers into a time series.

Kept pure (no I/O) and takes the client's already-loaded statement
history, same convention as the rest of the engine -- Workspace owns
fetching that history.
"""

from __future__ import annotations

from app.engine.kpis import calculate_kpis_for_all
from app.models.domain import ClientTrend, ClientTrendPoint, FinancialStatement


class TrendError(Exception):
    """Raised when a client has fewer than 2 actual periods on file -- there's no trend
    to show from a single snapshot. Mirrors engine/forecast.py's ForecastError."""


def _narrative_for(client_id: str, points: list[ClientTrendPoint]) -> str:
    first, last = points[0], points[-1]
    revenue_change = last.revenue - first.revenue
    direction = "grew" if revenue_change > 0 else "shrank" if revenue_change < 0 else "held flat"

    sentence = (
        f"{client_id}'s revenue {direction} from {first.revenue:,.0f} in {first.period} "
        f"to {last.revenue:,.0f} in {last.period}"
    )
    if first.revenue != 0:
        pct = abs(revenue_change) / abs(first.revenue) * 100
        sentence += f" ({pct:.1f}%)"

    ebitda_change = last.ebitda - first.ebitda
    ebitda_direction = "improved" if ebitda_change > 0 else "declined" if ebitda_change < 0 else "was unchanged"
    sentence += f"; EBITDA {ebitda_direction} from {first.ebitda:,.0f} to {last.ebitda:,.0f} over the same window."

    return sentence


def build_client_trend(client_id: str, history: list[FinancialStatement], max_periods: int = 12) -> ClientTrend:
    """Build a Revenue/EBITDA/Net-margin trend from a client's actual statement history.

    `history` should already be filtered to this client's ACTUAL scenario
    (same convention as Workspace.client_history). Raises TrendError if
    fewer than 2 periods are present -- a single snapshot has no trend.
    Keeps only the most recent `max_periods` periods once sorted.
    """
    if len(history) < 2:
        raise TrendError(f"'{client_id}' has fewer than 2 actual periods on file -- no trend to show.")

    sorted_history = sorted(history, key=lambda s: s.period)[-max_periods:]
    kpis = calculate_kpis_for_all(sorted_history)

    points = [
        ClientTrendPoint(period=k.period, revenue=k.revenue, ebitda=k.ebitda, net_margin_pct=k.net_margin_pct)
        for k in kpis
    ]

    return ClientTrend(
        client_id=client_id,
        periods=[p.period for p in points],
        points=points,
        narrative=_narrative_for(client_id, points),
    )
