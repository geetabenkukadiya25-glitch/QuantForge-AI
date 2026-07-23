"""Report builders for the 5 Governance report kinds (Phase 17.8) --
mirrors `app.risk_analytics.risk_reports` exactly: pure assembly of
already-computed data into a persisted document, plus an HTML export.
No PDF library is installed in this project (same finding as Phase
17.7) -- `export_html` produces a self-contained, print-ready `.html`
document instead of fabricating a `.pdf`.
"""

import html
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class GovernanceReportKind(str, Enum):
    GOVERNANCE_SUMMARY = "GOVERNANCE_SUMMARY"
    APPROVAL_REPORT = "APPROVAL_REPORT"
    COMPLIANCE_REPORT = "COMPLIANCE_REPORT"
    RESEARCH_REPORT = "RESEARCH_REPORT"
    INSTITUTIONAL_GOVERNANCE_REPORT = "INSTITUTIONAL_GOVERNANCE_REPORT"


@dataclass
class GovernanceReport:
    id: str
    kind: GovernanceReportKind
    title: str
    source_description: str
    created_at: datetime
    sections: dict[str, Any]
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "title": self.title,
            "source_description": self.source_description,
            "created_at": self.created_at.isoformat(),
            "sections": self.sections,
            "tags": list(self.tags),
        }

    @staticmethod
    def from_dict(data: dict) -> "GovernanceReport":
        return GovernanceReport(
            id=data["id"],
            kind=GovernanceReportKind(data["kind"]),
            title=data["title"],
            source_description=data["source_description"],
            created_at=datetime.fromisoformat(data["created_at"]),
            sections=data.get("sections", {}),
            tags=list(data.get("tags", [])),
        )


def _build(kind: GovernanceReportKind, title: str, source_description: str, sections: dict, tags: list[str] | None = None) -> GovernanceReport:
    return GovernanceReport(
        id=uuid.uuid4().hex,
        kind=kind,
        title=title,
        source_description=source_description,
        created_at=datetime.now(timezone.utc),
        sections=sections,
        tags=list(tags or []),
    )


def governance_summary_report(source_description: str, records: list[dict]) -> GovernanceReport:
    return _build(GovernanceReportKind.GOVERNANCE_SUMMARY, "Governance Summary", source_description, {"records": records})


def approval_report(source_description: str, decision_history: list[dict]) -> GovernanceReport:
    return _build(GovernanceReportKind.APPROVAL_REPORT, "Approval Report", source_description, {"decisions": decision_history})


def compliance_report(source_description: str, compliance: dict) -> GovernanceReport:
    return _build(GovernanceReportKind.COMPLIANCE_REPORT, "Compliance Report", source_description, {"compliance": compliance})


def research_report(source_description: str, records: list[dict]) -> GovernanceReport:
    return _build(GovernanceReportKind.RESEARCH_REPORT, "Research Report", source_description, {"records": records})


def institutional_governance_report(source_description: str, sections: dict) -> GovernanceReport:
    """The "everything" report -- `sections` is expected to carry
    records/compliance/policy/audit summaries, whichever the caller has
    already computed."""
    return _build(GovernanceReportKind.INSTITUTIONAL_GOVERNANCE_REPORT, "Institutional Governance Report", source_description, sections)


def _render_value(value) -> str:
    if isinstance(value, dict):
        rows = "".join(f"<tr><th>{html.escape(str(k))}</th><td>{_render_value(v)}</td></tr>" for k, v in value.items())
        return f"<table>{rows}</table>"
    if isinstance(value, list):
        if not value:
            return "<em>none</em>"
        return "".join(f"<div class='item'>{_render_value(v)}</div>" for v in value)
    return html.escape(str(value))


def export_html(report: GovernanceReport) -> bytes:
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
