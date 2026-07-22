import pytest

from app.agents.fpa_agent import AgentNotConfiguredError
from app.agents.narrative import _parse_response, generate_narrative
from app.engine.workspace import Workspace
from pathlib import Path

SAMPLE_CSV = Path(__file__).resolve().parents[1] / "sample_data" / "sample_financials.csv"


def test_parse_response_well_formed_text():
    text = (
        "SUMMARY:\n"
        "Revenue grew and margins held steady.\n\n"
        "RISKS:\n"
        "- Client concentration in Acme\n"
        "- Rising opex\n\n"
        "OPPORTUNITIES:\n"
        "- Upsell advisory services\n"
    )

    narrative = _parse_response(text)

    assert narrative.summary == "Revenue grew and margins held steady."
    assert narrative.risks == ["Client concentration in Acme", "Rising opex"]
    assert narrative.opportunities == ["Upsell advisory services"]


def test_parse_response_missing_risks_and_opportunities():
    text = "SUMMARY:\nJust a summary, nothing else.\n"

    narrative = _parse_response(text)

    assert narrative.summary == "Just a summary, nothing else."
    assert narrative.risks == []
    assert narrative.opportunities == []


def test_parse_response_no_markers_at_all():
    text = "This is a plain response with no structure whatsoever."

    narrative = _parse_response(text)

    assert narrative.summary == text
    assert narrative.risks == []
    assert narrative.opportunities == []


def test_parse_response_empty_bullet_sections_are_empty_lists():
    text = "SUMMARY:\nSummary text.\n\nRISKS:\n\nOPPORTUNITIES:\n"

    narrative = _parse_response(text)

    assert narrative.risks == []
    assert narrative.opportunities == []


def test_generate_narrative_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    workspace = Workspace.from_file(SAMPLE_CSV)
    report = workspace.build_client_report("beacon-partners", "2026-06")

    with pytest.raises(AgentNotConfiguredError):
        generate_narrative(report)
