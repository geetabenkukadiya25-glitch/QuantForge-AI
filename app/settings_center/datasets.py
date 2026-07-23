"""Dataset settings section (Phase 18.8) -- seeded from the real
`_PREVIEW_ROWS=100`/`_MAX_VERSIONS_PER_DATASET=20` constants in
`app.dataset_manager.dataset_manager` (read-only reference; this module
never imports or mutates `DatasetManager` itself)."""

from app.settings_center.settings_models import DatasetSettings


def defaults() -> DatasetSettings:
    from app.config.paths import get_paths

    paths = get_paths()
    return DatasetSettings(
        registry_path_display=str(paths.dataset_registry_dir),
        import_path_display=str(paths.downloads_dir),
        cache_enabled=True,
        cleanup_max_versions=20,  # matches `dataset_manager._MAX_VERSIONS_PER_DATASET`
        preview_rows=100,  # matches `dataset_manager._PREVIEW_ROWS`
    )


def validate(settings: DatasetSettings) -> list[str]:
    issues = []
    if settings.cleanup_max_versions < 1:
        issues.append("cleanup_max_versions must be >= 1")
    if settings.preview_rows < 1:
        issues.append("preview_rows must be >= 1")
    return issues
