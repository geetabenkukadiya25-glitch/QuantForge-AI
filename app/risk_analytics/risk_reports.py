"""Report builders for the 8 Risk Analytics report kinds (Phase 17.7).
Each assembles a `RiskReport` purely from already-computed section dicts
(the caller runs the relevant analytic modules first) -- no new
computation happens here, only assembly + an HTML export.

No PDF library is installed in this project (`reportlab`/`fpdf` both
absent) and `app.analytics.report_generator.ReportGenerator` is itself
an unimplemented placeholder -- `export_html` produces a self-contained,
print-ready `.html` document instead of fabricating a `.pdf`.
"""

import html
import uuid
from datetime import datetime, timezone

from app.risk_analytics.risk_models import RiskReport, RiskReportKind


def _build(kind: RiskReportKind, title: str, source_description: str, sections: dict, tags: list[str] | None = None) -> RiskReport:
    return RiskReport(
        id=uuid.uuid4().hex,
        kind=kind,
        title=title,
        source_description=source_description,
        created_at=datetime.now(timezone.utc),
        sections=sections,
        tags=list(tags or []),
    )


def risk_summary_report(source_description: str, overview: dict) -> RiskReport:
    return _build(RiskReportKind.RISK_SUMMARY, "Risk Summary", source_description, {"overview": overview})


def portfolio_summary_report(source_description: str, portfolio_risk: dict, correlation: dict, exposure: dict) -> RiskReport:
    return _build(RiskReportKind.PORTFOLIO_SUMMARY, "Portfolio Summary", source_description, {"portfolio_risk": portfolio_risk, "correlation": correlation, "exposure": exposure})


def strategy_summary_report(source_description: str, overview: dict, heatmaps: dict) -> RiskReport:
    return _build(RiskReportKind.STRATEGY_SUMMARY, "Strategy Summary", source_description, {"overview": overview, "heatmaps": heatmaps})


def exposure_report(source_description: str, exposure: dict) -> RiskReport:
    return _build(RiskReportKind.EXPOSURE_REPORT, "Exposure Report", source_description, {"exposure": exposure})


def var_report(source_description: str, var_results: list[dict]) -> RiskReport:
    return _build(RiskReportKind.VAR_REPORT, "VaR Report", source_description, {"var": var_results})


def scenario_report(source_description: str, scenarios: list[dict]) -> RiskReport:
    return _build(RiskReportKind.SCENARIO_REPORT, "Scenario Report", source_description, {"scenarios": scenarios})


def monte_carlo_report(source_description: str, monte_carlo: dict) -> RiskReport:
    return _build(RiskReportKind.MONTE_CARLO_REPORT, "Monte Carlo Report", source_description, {"monte_carlo": monte_carlo})


def institutional_risk_report(source_description: str, sections: dict) -> RiskReport:
    """The "everything" report -- `sections` is expected to carry
    overview/drawdown/var/cvar/monte_carlo/scenario/correlation/heatmaps/
    exposure, whichever the caller has already computed."""
    return _build(RiskReportKind.INSTITUTIONAL_RISK_REPORT, "Institutional Risk Report", source_description, sections)


def _render_value(value) -> str:
    if isinstance(value, dict):
        rows = "".join(f"<tr><th>{html.escape(str(k))}</th><td>{_render_value(v)}</td></tr>" for k, v in value.items())
        return f"<table>{rows}</table>"
    if isinstance(value, list):
        if not value:
            return "<em>none</em>"
        return "".join(f"<div class='item'>{_render_value(v)}</div>" for v in value)
    return html.escape(str(value))


def export_html(report: RiskReport) -> bytes:
    sections_html = "".join(f"<h2>{html.escape(section_name.replace('_', ' ').title())}</h2>{_render_value(section_value)}" for section_name, section_value in report.sections.items())
    document = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{html.escape(report.title)}</title>
<style>
body {{ font-family: sans-serif; margin: 2rem; }}
table {{ border-collapse: collapse; margin-bottom: 1rem; }}
th, td {{ border: 1px solid #ccc; padding: 4px 8px; text-align: left; }}
.item {{ margin-bottom: 0.5rem; }}
</style></head>
<body>
<h1>{html.escape(report.title)}</h1>
<p><strong>Source:</strong> {html.escape(report.source_description)}</p>
<p><strong>Generated:</strong> {report.created_at.isoformat(timespec="seconds")}</p>
{sections_html}
</body></html>"""
    return document.encode("utf-8")
