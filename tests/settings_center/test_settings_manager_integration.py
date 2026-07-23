"""`SettingsCenterManager` integration -- full CRUD/validate/reset/
export/import/backup/restore cycle, plus real `JobManager`-submitted
variants (deadline-bounded polling, mirrors Phase 17.7/17.8's pattern).
Every assertion checks genuinely-persisted state, never fabricated.
"""

import time

import pytest

from app.settings_center.exceptions import SettingsValidationError


def test_default_state_seeded_correctly(settings_manager) -> None:
    state = settings_manager.get_state()
    assert state.risk.monte_carlo_iterations == 200
    assert state.datasets.preview_rows == 100


def test_update_section_persists_and_bumps_version(settings_manager) -> None:
    before = settings_manager.get_state()
    settings_manager.update_section("risk", monte_carlo_iterations=500)
    after = settings_manager.get_state()
    assert after.risk.monte_carlo_iterations == 500
    assert after.version > before.version


def test_update_section_rejects_invalid_values(settings_manager) -> None:
    with pytest.raises(SettingsValidationError):
        settings_manager.update_section("risk", default_confidence=5.0)
    # Rejected update must not have been persisted.
    assert settings_manager.get_state().risk.default_confidence == 0.95


def test_reset_section_to_defaults(settings_manager) -> None:
    settings_manager.update_section("charts", export_dpi=999)
    settings_manager.reset_section_to_defaults("charts")
    assert settings_manager.get_state().charts.export_dpi == 150


def test_full_cycle_update_export_reset_import(settings_manager) -> None:
    settings_manager.update_section("general", project_name="Custom Project", organization="Acme")
    settings_manager.update_section("risk", monte_carlo_iterations=1234)

    exported = settings_manager.export_now()

    settings_manager.reset_all_to_defaults()
    reset_state = settings_manager.get_state()
    assert reset_state.general.project_name != "Custom Project"
    assert reset_state.risk.monte_carlo_iterations == 200

    restored = settings_manager.import_now(exported)
    assert restored.general.project_name == "Custom Project"
    assert restored.general.organization == "Acme"
    assert restored.risk.monte_carlo_iterations == 1234


def test_backup_and_restore_now(settings_manager) -> None:
    settings_manager.update_section("general", author="Alice")
    name = settings_manager.backup_now(label="checkpoint")
    assert any(b["name"] == name for b in settings_manager.list_backups())

    settings_manager.update_section("general", author="Bob")
    assert settings_manager.get_state().general.author == "Bob"

    settings_manager.restore_now(name)
    assert settings_manager.get_state().general.author == "Alice"


def test_restore_unknown_backup_raises(settings_manager) -> None:
    with pytest.raises(FileNotFoundError):
        settings_manager.restore_now("nonexistent-backup")


def test_path_override_set_and_reset(settings_manager) -> None:
    settings_manager.set_path_override("data_dir", "/custom/data")
    assert settings_manager.get_state().path_overrides["data_dir"] == "/custom/data"
    settings_manager.reset_path_override("data_dir")
    assert "data_dir" not in settings_manager.get_state().path_overrides


def test_audit_events_recorded_for_real_actions(settings_manager) -> None:
    settings_manager.update_section("risk", monte_carlo_iterations=300)
    settings_manager.backup_now()
    kinds = {e.event_type.value for e in settings_manager.list_audit_events()}
    assert {"CREATED", "SECTION_UPDATED", "BACKED_UP"}.issubset(kinds)


def test_submit_export_runs_as_a_real_job(settings_manager) -> None:
    from app.job_manager import JobState, get_job_manager

    job_manager = get_job_manager()
    job = settings_manager.submit_export()
    deadline = time.time() + 10
    while job_manager.get(job.id).state not in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED) and time.time() < deadline:
        time.sleep(0.02)
    finished = job_manager.get(job.id)
    assert finished.state == JobState.COMPLETED, finished.error
    assert isinstance(finished.result, bytes)
    assert b"general" in finished.result


def test_submit_backup_and_submit_restore_run_as_real_jobs(settings_manager) -> None:
    from app.job_manager import JobState, get_job_manager

    job_manager = get_job_manager()
    settings_manager.update_section("general", author="Carol")

    backup_job = settings_manager.submit_backup(label="job-test")
    deadline = time.time() + 10
    while job_manager.get(backup_job.id).state not in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED) and time.time() < deadline:
        time.sleep(0.02)
    finished_backup = job_manager.get(backup_job.id)
    assert finished_backup.state == JobState.COMPLETED, finished_backup.error
    backup_name = finished_backup.result

    settings_manager.update_section("general", author="Dave")

    restore_job = settings_manager.submit_restore(backup_name)
    deadline = time.time() + 10
    while job_manager.get(restore_job.id).state not in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED) and time.time() < deadline:
        time.sleep(0.02)
    finished_restore = job_manager.get(restore_job.id)
    assert finished_restore.state == JobState.COMPLETED, finished_restore.error
    assert settings_manager.get_state().general.author == "Carol"


def test_submit_import_runs_as_a_real_job(settings_manager) -> None:
    from app.job_manager import JobState, get_job_manager

    job_manager = get_job_manager()
    settings_manager.update_section("general", project_name="Job Import Target")
    payload = settings_manager.export_now()
    settings_manager.reset_all_to_defaults()

    job = settings_manager.submit_import(payload)
    deadline = time.time() + 10
    while job_manager.get(job.id).state not in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED) and time.time() < deadline:
        time.sleep(0.02)
    finished = job_manager.get(job.id)
    assert finished.state == JobState.COMPLETED, finished.error
    assert settings_manager.get_state().general.project_name == "Job Import Target"
