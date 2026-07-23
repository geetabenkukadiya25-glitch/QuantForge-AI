"""Report settings section (Phase 18.8) -- stores format/branding
preferences only. No Excel/PDF export capability exists anywhere in the
repo (confirmed absent in the reuse audit: no `openpyxl`/`xlsxwriter`,
`app.analytics.report_generator.ReportGenerator` is an unimplemented
stub) -- `excel_enabled`/`pdf_enabled` are forward-looking preferences,
not toggles for functionality that exists today."""

from app.settings_center.settings_models import ReportSettings


def defaults() -> ReportSettings:
    return ReportSettings(html_enabled=True, excel_enabled=False, pdf_enabled=False, branding_name="", logo_path="", footer_text="")


def validate(settings: ReportSettings) -> list[str]:
    issues = []
    if settings.excel_enabled:
        issues.append("excel_enabled cannot be True -- no Excel export capability is implemented in this project yet")
    if settings.pdf_enabled:
        issues.append("pdf_enabled cannot be True -- no PDF export capability is implemented in this project yet")
    return issues
