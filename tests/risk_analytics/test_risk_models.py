"""Round-trip checks for Risk Analytics data classes (Phase 17.7)."""

from datetime import datetime, timezone

from app.risk_analytics.risk_models import (
    ConsecutiveStreaks,
    RiskAuditEvent,
    RiskAuditEventType,
    RiskManagerState,
    RiskReport,
    RiskReportKind,
    VarResult,
)


def test_consecutive_streaks_to_dict() -> None:
    streaks = ConsecutiveStreaks(max_consecutive_wins=3, max_consecutive_losses=2, current_streak=1)
    assert streaks.to_dict() == {"max_consecutive_wins": 3, "max_consecutive_losses": 2, "current_streak": 1}


def test_var_result_to_dict() -> None:
    result = VarResult(method="HISTORICAL", confidence=0.95, value=123.45)
    assert result.to_dict() == {"method": "HISTORICAL", "confidence": 0.95, "value": 123.45}


def test_risk_audit_event_round_trip() -> None:
    event = RiskAuditEvent(event_type=RiskAuditEventType.ANALYZED, key="r1", timestamp=datetime.now(timezone.utc))
    restored = RiskAuditEvent.from_dict(event.to_dict())
    assert restored.event_type == RiskAuditEventType.ANALYZED
    assert restored.key == "r1"


def test_risk_report_round_trip() -> None:
    report = RiskReport(
        id="r1", kind=RiskReportKind.RISK_SUMMARY, title="Test Report", source_description="Test Source",
        created_at=datetime.now(timezone.utc), sections={"overview": {"a": 1}}, tags=["Forex"],
    )
    restored = RiskReport.from_dict(report.to_dict())
    assert restored.id == "r1"
    assert restored.kind == RiskReportKind.RISK_SUMMARY
    assert restored.sections == {"overview": {"a": 1}}
    assert restored.tags == ["Forex"]


def test_risk_manager_state_round_trip() -> None:
    report = RiskReport(id="r1", kind=RiskReportKind.VAR_REPORT, title="T", source_description="S", created_at=datetime.now(timezone.utc))
    state = RiskManagerState(reports={"r1": report})
    restored = RiskManagerState.from_dict(state.to_dict())
    assert "r1" in restored.reports
    assert restored.reports["r1"].kind == RiskReportKind.VAR_REPORT
