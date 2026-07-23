"""JSON export/import for one `RiskReport` (Phase 17.7) -- mirrors
`app.workflow.workflow_serializer`. Thin wrapper over `to_dict`/`from_dict`.
"""

from app.risk_analytics.risk_models import RiskReport


def export_report(report: RiskReport) -> dict:
    return report.to_dict()


def import_report(data: dict) -> RiskReport:
    return RiskReport.from_dict(data)
