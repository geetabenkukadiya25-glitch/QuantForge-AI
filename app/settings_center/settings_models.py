"""Data models for the Institutional Settings Center (Phase 18.8). Each
section is a flat, JSON-primitive dataclass (`to_dict = dataclasses.asdict`
shortcut, mirrors `app.risk_analytics.risk_models`'s pattern) so only
`SettingsState` itself (which nests dataclasses + a `datetime`) needs a
hand-rolled `to_dict`/`from_dict`.
"""

import dataclasses
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


def _asdict(obj: Any) -> dict:
    return dataclasses.asdict(obj)


@dataclass
class GeneralSettings:
    project_name: str = "QuantForge AI"
    organization: str = ""
    author: str = ""
    timezone: str = "UTC"
    language: str = "en"
    theme: str = "dark"

    to_dict = _asdict

    @staticmethod
    def from_dict(data: dict) -> "GeneralSettings":
        return GeneralSettings(**{f.name: data[f.name] for f in dataclasses.fields(GeneralSettings) if f.name in data})


@dataclass
class DatasetSettings:
    registry_path_display: str = ""
    import_path_display: str = ""
    cache_enabled: bool = True
    cleanup_max_versions: int = 20
    preview_rows: int = 100

    to_dict = _asdict

    @staticmethod
    def from_dict(data: dict) -> "DatasetSettings":
        return DatasetSettings(**{f.name: data[f.name] for f in dataclasses.fields(DatasetSettings) if f.name in data})


@dataclass
class WorkflowSettings:
    retry_count: int = 0
    timeout_seconds: float = 0.0  # 0 == disabled, mirrors `WorkflowStep.timeout=None` meaning "no timeout"
    parallel_jobs: int = 1
    queue_size: int = 0  # 0 == unbounded, mirrors the real (unbounded) `WorkflowQueue`

    to_dict = _asdict

    @staticmethod
    def from_dict(data: dict) -> "WorkflowSettings":
        return WorkflowSettings(**{f.name: data[f.name] for f in dataclasses.fields(WorkflowSettings) if f.name in data})


@dataclass
class JobSettings:
    history_retention: int = 2000
    refresh_interval_seconds: float = 1.0
    progress_update_frequency: float = 0.5
    cleanup_policy: str = "keep_last_n"

    to_dict = _asdict

    @staticmethod
    def from_dict(data: dict) -> "JobSettings":
        return JobSettings(**{f.name: data[f.name] for f in dataclasses.fields(JobSettings) if f.name in data})


@dataclass
class RiskSettings:
    default_confidence: float = 0.95
    var_pct: float = 0.95
    cvar_pct: float = 0.95
    monte_carlo_iterations: int = 200
    scenario_defaults: list[str] = field(default_factory=lambda: ["BULL", "BEAR", "SIDEWAYS"])

    to_dict = _asdict

    @staticmethod
    def from_dict(data: dict) -> "RiskSettings":
        kwargs = {f.name: data[f.name] for f in dataclasses.fields(RiskSettings) if f.name in data}
        if "scenario_defaults" in kwargs:
            kwargs["scenario_defaults"] = list(kwargs["scenario_defaults"])
        return RiskSettings(**kwargs)


@dataclass
class ChartSettings:
    theme: str = "dark"
    show_grid: bool = True
    font_family: str = "sans-serif"
    candle_up_color: str = "#26A69A"
    candle_down_color: str = "#EF5350"
    export_dpi: int = 150
    default_width: int = 1200
    default_height: int = 600

    to_dict = _asdict

    @staticmethod
    def from_dict(data: dict) -> "ChartSettings":
        return ChartSettings(**{f.name: data[f.name] for f in dataclasses.fields(ChartSettings) if f.name in data})


@dataclass
class ReportSettings:
    html_enabled: bool = True
    excel_enabled: bool = False  # no Excel export capability exists yet (no openpyxl/xlsxwriter) -- stored preference only
    pdf_enabled: bool = False  # no PDF library exists yet -- future flag, always False today
    branding_name: str = ""
    logo_path: str = ""
    footer_text: str = ""

    to_dict = _asdict

    @staticmethod
    def from_dict(data: dict) -> "ReportSettings":
        return ReportSettings(**{f.name: data[f.name] for f in dataclasses.fields(ReportSettings) if f.name in data})


@dataclass
class NotificationSettings:
    toast_enabled: bool = True
    desktop_enabled: bool = False  # no desktop-notification integration exists yet -- stored preference only
    sounds_enabled: bool = False  # no sound integration exists yet -- stored preference only
    notify_on_job_completion: bool = True
    notify_on_errors: bool = True

    to_dict = _asdict

    @staticmethod
    def from_dict(data: dict) -> "NotificationSettings":
        return NotificationSettings(**{f.name: data[f.name] for f in dataclasses.fields(NotificationSettings) if f.name in data})


@dataclass
class LoggingSettings:
    log_level: str = "INFO"
    audit_retention_days: int = 90
    runtime_retention_days: int = 30
    cleanup_enabled: bool = True

    to_dict = _asdict

    @staticmethod
    def from_dict(data: dict) -> "LoggingSettings":
        return LoggingSettings(**{f.name: data[f.name] for f in dataclasses.fields(LoggingSettings) if f.name in data})


SECTION_TYPES: dict[str, type] = {
    "general": GeneralSettings,
    "datasets": DatasetSettings,
    "workflow": WorkflowSettings,
    "jobs": JobSettings,
    "risk": RiskSettings,
    "charts": ChartSettings,
    "reports": ReportSettings,
    "notifications": NotificationSettings,
    "logging": LoggingSettings,
}


@dataclass
class SettingsState:
    """The single persisted document -- one instance per process, mirrors
    `WorkflowManagerState`/`GovernanceManagerState`'s "one flat state
    object" shape, except here the state itself IS the whole settings
    surface (there's no dict-of-records; Settings is a singleton)."""

    general: GeneralSettings = field(default_factory=GeneralSettings)
    datasets: DatasetSettings = field(default_factory=DatasetSettings)
    workflow: WorkflowSettings = field(default_factory=WorkflowSettings)
    jobs: JobSettings = field(default_factory=JobSettings)
    risk: RiskSettings = field(default_factory=RiskSettings)
    charts: ChartSettings = field(default_factory=ChartSettings)
    reports: ReportSettings = field(default_factory=ReportSettings)
    notifications: NotificationSettings = field(default_factory=NotificationSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)
    path_overrides: dict[str, str] = field(default_factory=dict)
    version: int = 1
    updated_at: datetime = field(default_factory=lambda: datetime.now())

    def to_dict(self) -> dict:
        return {
            "general": self.general.to_dict(),
            "datasets": self.datasets.to_dict(),
            "workflow": self.workflow.to_dict(),
            "jobs": self.jobs.to_dict(),
            "risk": self.risk.to_dict(),
            "charts": self.charts.to_dict(),
            "reports": self.reports.to_dict(),
            "notifications": self.notifications.to_dict(),
            "logging": self.logging.to_dict(),
            "path_overrides": dict(self.path_overrides),
            "version": self.version,
            "updated_at": self.updated_at.isoformat(),
        }

    @staticmethod
    def from_dict(data: dict) -> "SettingsState":
        return SettingsState(
            general=GeneralSettings.from_dict(data.get("general", {})),
            datasets=DatasetSettings.from_dict(data.get("datasets", {})),
            workflow=WorkflowSettings.from_dict(data.get("workflow", {})),
            jobs=JobSettings.from_dict(data.get("jobs", {})),
            risk=RiskSettings.from_dict(data.get("risk", {})),
            charts=ChartSettings.from_dict(data.get("charts", {})),
            reports=ReportSettings.from_dict(data.get("reports", {})),
            notifications=NotificationSettings.from_dict(data.get("notifications", {})),
            logging=LoggingSettings.from_dict(data.get("logging", {})),
            path_overrides=dict(data.get("path_overrides", {})),
            version=data.get("version", 1),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
        )

    def section(self, name: str):
        if name not in SECTION_TYPES:
            raise KeyError(f"Unknown settings section '{name}'.")
        return getattr(self, name)
