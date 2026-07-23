"""`app.data_catalog.dependency_graph.build_dependency_tree` -- pure tree
shape assertions (Dataset -> Strategy -> Category -> Job)."""

from datetime import datetime, timezone

from app.data_catalog.dependency_graph import build_dependency_tree
from app.data_catalog.models import DatasetLineageEvent, LineageEventKind

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_tree_groups_by_matched_strategy_then_category() -> None:
    events = [
        DatasetLineageEvent(
            dataset_id="ds1", kind=LineageEventKind.USED_BY_BACKTEST, timestamp=NOW, inferred=True,
            job_id="j1", owner_page="Backtesting Dashboard", status="COMPLETED", label="Backtest: EMA Crossover",
        ),
        DatasetLineageEvent(
            dataset_id="ds1", kind=LineageEventKind.USED_BY_OPTIMIZATION, timestamp=NOW, inferred=True,
            job_id="j2", owner_page="Optimization Dashboard", status="COMPLETED", label="Optimization: EMA Crossover",
        ),
    ]
    tree = build_dependency_tree("EURUSD Hourly", events, strategy_names=["EMA Crossover"])

    assert tree.label == "EURUSD Hourly"
    assert tree.kind == "Dataset"
    assert len(tree.children) == 1
    strategy_node = tree.children[0]
    assert strategy_node.label == "EMA Crossover"
    assert strategy_node.kind == "Strategy"
    category_labels = {c.label.split(" (")[0] for c in strategy_node.children}
    assert category_labels == {"Backtest", "Optimization"}


def test_unmatched_jobs_go_to_unattributed_bucket() -> None:
    events = [
        DatasetLineageEvent(
            dataset_id="ds1", kind=LineageEventKind.USED_BY_VALIDATION, timestamp=NOW, inferred=True,
            job_id="j3", owner_page="Validation Dashboard", status="COMPLETED", label="Validation: unknown",
        ),
    ]
    tree = build_dependency_tree("EURUSD Hourly", events, strategy_names=["EMA Crossover"])
    assert len(tree.children) == 1
    assert tree.children[0].label == "(unattributed)"


def test_non_used_by_events_are_excluded_from_tree() -> None:
    events = [DatasetLineageEvent(dataset_id="ds1", kind=LineageEventKind.IMPORTED, timestamp=NOW, inferred=False)]
    tree = build_dependency_tree("EURUSD Hourly", events, strategy_names=[])
    assert tree.children == ()
