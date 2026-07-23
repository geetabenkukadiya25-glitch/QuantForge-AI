"""Per-section `defaults()`/`validate()` -- confirms defaults match the
REAL constants found in the reuse audit, and that validation catches bad
input without needing a `SettingsCenterManager`."""

from app.settings_center import charts, datasets, general, jobs, logging, notifications, reports, risk, workflow


def test_general_defaults_and_validate() -> None:
    settings = general.defaults()
    assert settings.project_name  # seeded from Settings.app_name, never empty
    assert general.validate(settings) == []
    settings.project_name = ""
    assert "project_name must not be empty" in general.validate(settings)


def test_datasets_defaults_match_dataset_manager_constants() -> None:
    settings = datasets.defaults()
    assert settings.preview_rows == 100  # matches dataset_manager._PREVIEW_ROWS
    assert settings.cleanup_max_versions == 20  # matches dataset_manager._MAX_VERSIONS_PER_DATASET
    assert datasets.validate(settings) == []


def test_workflow_defaults_and_validate() -> None:
    settings = workflow.defaults()
    assert workflow.validate(settings) == []
    settings.parallel_jobs = 0
    assert any("parallel_jobs" in issue for issue in workflow.validate(settings))


def test_jobs_defaults_match_job_manager_constant() -> None:
    settings = jobs.defaults()
    assert settings.history_retention == 2000  # matches job_manager.job_history._MAX_RECORDS
    assert jobs.validate(settings) == []
    settings.cleanup_policy = "nonsense"
    assert any("cleanup_policy" in issue for issue in jobs.validate(settings))


def test_risk_defaults_match_risk_manager_constants() -> None:
    settings = risk.defaults()
    assert settings.monte_carlo_iterations == 200  # matches RiskManager keyword default
    assert settings.default_confidence == 0.95
    assert risk.validate(settings) == []
    settings.default_confidence = 1.5
    assert any("default_confidence" in issue for issue in risk.validate(settings))


def test_charts_defaults_match_chart_engine_theme() -> None:
    from app.chart_engine.themes import DARK_THEME

    settings = charts.defaults()
    assert settings.candle_up_color == DARK_THEME.up
    assert settings.candle_down_color == DARK_THEME.down
    assert charts.validate(settings) == []
    settings.export_dpi = 0
    assert any("export_dpi" in issue for issue in charts.validate(settings))


def test_reports_defaults_and_locked_toggles() -> None:
    settings = reports.defaults()
    assert reports.validate(settings) == []
    settings.excel_enabled = True
    issues = reports.validate(settings)
    assert any("excel_enabled" in issue for issue in issues)


def test_notifications_defaults_and_locked_toggles() -> None:
    settings = notifications.defaults()
    assert notifications.validate(settings) == []
    settings.desktop_enabled = True
    issues = notifications.validate(settings)
    assert any("desktop_enabled" in issue for issue in issues)


def test_logging_defaults_seeded_from_settings() -> None:
    from app.config.settings import get_settings

    settings = logging.defaults()
    assert settings.log_level == get_settings().log_level
    assert logging.validate(settings) == []
    settings.log_level = "NOT_A_LEVEL"
    assert any("log_level" in issue for issue in logging.validate(settings))
