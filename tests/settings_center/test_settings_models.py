"""`settings_models.py` -- round-trip serialization for every section and
the top-level `SettingsState`."""

from app.settings_center.settings_models import (
    ChartSettings,
    DatasetSettings,
    GeneralSettings,
    JobSettings,
    LoggingSettings,
    NotificationSettings,
    ReportSettings,
    RiskSettings,
    SettingsState,
    WorkflowSettings,
)


def test_general_settings_round_trip() -> None:
    settings = GeneralSettings(project_name="P", organization="O", author="A", timezone="UTC", language="en", theme="light")
    assert GeneralSettings.from_dict(settings.to_dict()) == settings


def test_dataset_settings_round_trip() -> None:
    settings = DatasetSettings(registry_path_display="/x", cache_enabled=False, cleanup_max_versions=5, preview_rows=50)
    assert DatasetSettings.from_dict(settings.to_dict()) == settings


def test_workflow_settings_round_trip() -> None:
    settings = WorkflowSettings(retry_count=3, timeout_seconds=30.0, parallel_jobs=2, queue_size=10)
    assert WorkflowSettings.from_dict(settings.to_dict()) == settings


def test_job_settings_round_trip() -> None:
    settings = JobSettings(history_retention=500, refresh_interval_seconds=2.0, progress_update_frequency=1.0, cleanup_policy="manual")
    assert JobSettings.from_dict(settings.to_dict()) == settings


def test_risk_settings_round_trip_with_list_field() -> None:
    settings = RiskSettings(scenario_defaults=["BULL", "HIGH_VOLATILITY"])
    restored = RiskSettings.from_dict(settings.to_dict())
    assert restored == settings
    assert restored.scenario_defaults == ["BULL", "HIGH_VOLATILITY"]


def test_chart_settings_round_trip() -> None:
    settings = ChartSettings(theme="light", export_dpi=300)
    assert ChartSettings.from_dict(settings.to_dict()) == settings


def test_report_settings_round_trip() -> None:
    settings = ReportSettings(branding_name="Acme", logo_path="/logo.png", footer_text="footer")
    assert ReportSettings.from_dict(settings.to_dict()) == settings


def test_notification_settings_round_trip() -> None:
    settings = NotificationSettings(toast_enabled=False, notify_on_errors=False)
    assert NotificationSettings.from_dict(settings.to_dict()) == settings


def test_logging_settings_round_trip() -> None:
    settings = LoggingSettings(log_level="DEBUG", audit_retention_days=30)
    assert LoggingSettings.from_dict(settings.to_dict()) == settings


def test_settings_state_round_trip() -> None:
    state = SettingsState()
    state.risk.monte_carlo_iterations = 999
    state.path_overrides["data_dir"] = "/custom/path"
    restored = SettingsState.from_dict(state.to_dict())
    assert restored.risk.monte_carlo_iterations == 999
    assert restored.path_overrides == {"data_dir": "/custom/path"}
    assert restored.version == state.version


def test_settings_state_section_accessor() -> None:
    state = SettingsState()
    assert state.section("risk") is state.risk
    try:
        state.section("nonexistent")
        assert False, "expected KeyError"
    except KeyError:
        pass
