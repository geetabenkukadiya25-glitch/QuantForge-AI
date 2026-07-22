"""Strategy Statistics and the management-layer Suggestions tier -- both
pure, read-only, and independent of `app.sdl.validator`."""

from app.strategy_library import StrategyLibraryManager


def test_statistics_reflect_document_structure(manager: StrategyLibraryManager, example_path) -> None:
    stats = manager.compute_statistics(example_path)
    assert stats.indicator_count == 2  # fast_ma, slow_ma
    assert stats.condition_count == 2  # 2 entry rules, no filters/exit rules
    assert stats.filter_count == 0
    assert stats.risk_rule_count == 1  # risk_management block is set
    assert stats.lines_of_sdl > 0


def test_metadata_completeness_increases_with_more_optional_fields_filled(manager: StrategyLibraryManager) -> None:
    sparse_path = manager.new_strategy("sparse.yaml", "Sparse")
    sparse_stats = manager.compute_statistics(sparse_path)

    definition = manager.load_definition(sparse_path)
    rich = definition.model_copy(
        update={
            "metadata": definition.metadata.model_copy(update={"description": "A full description.", "author": "Someone", "category": "trend"}),
            "tags": ["trend", "custom"],
            "sessions": ["London"],
        }
    )
    manager.save(rich, "sparse.yaml", overwrite=True)
    rich_stats = manager.compute_statistics(sparse_path)

    assert rich_stats.metadata_completeness_pct > sparse_stats.metadata_completeness_pct
    assert rich_stats.metadata_completeness_pct == 100


def test_suggestions_flag_missing_description_and_risk_management(manager: StrategyLibraryManager) -> None:
    path = manager.new_strategy("needs_suggestions.yaml", "Needs Suggestions")
    suggestions = manager.compute_suggestions(path)
    paths = {s.path for s in suggestions}
    assert "metadata.description" in paths
    assert "risk_management" in paths


def test_fully_filled_strategy_has_fewer_suggestions(manager: StrategyLibraryManager, example_path) -> None:
    # The bundled example has risk_management + entry_rules but no description/tags-in-category context;
    # still fewer than a totally blank strategy.
    blank_path = manager.new_strategy("blank_for_suggestions.yaml", "Blank")
    assert len(manager.compute_suggestions(example_path)) < len(manager.compute_suggestions(blank_path))
