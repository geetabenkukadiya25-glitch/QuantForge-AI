"""Pure builder for the Dataset -> Strategy -> Backtest -> Optimization ->
Validation -> Replay -> Research -> Reports dependency tree (Phase 17.5).
No state, no I/O -- takes already-computed `DatasetLineageEvent`s and a
list of known strategy display names (read-only lookup against
`StrategyLibraryManager`) and groups them into a `DatasetDependencyNode`
tree for the Streamlit page to render with plain nested `st.expander`s.
"""

from app.data_catalog.models import DatasetDependencyNode, DatasetLineageEvent, LineageEventKind

_CATEGORY_LABELS: dict[LineageEventKind, str] = {
    LineageEventKind.USED_BY_BACKTEST: "Backtest",
    LineageEventKind.USED_BY_OPTIMIZATION: "Optimization",
    LineageEventKind.USED_BY_VALIDATION: "Validation",
    LineageEventKind.USED_BY_REPLAY: "Replay",
    LineageEventKind.USED_BY_RESEARCH: "Research",
    LineageEventKind.USED_BY_PORTFOLIO: "Portfolio",
    LineageEventKind.USED_BY_REPORTS: "Reports",
    LineageEventKind.USED_BY_OTHER: "Other",
}

_UNATTRIBUTED_STRATEGY = "(unattributed)"


def _matched_strategy(label: str, strategy_names: list[str]) -> str | None:
    """Best-effort: a job's name (e.g. "Backtest: EMA Crossover") already
    embeds the strategy's display name -- match it against the known
    library, read-only, no strategy_library modification."""
    for name in strategy_names:
        if name and name.lower() in label.lower():
            return name
    return None


def _job_leaf(event: DatasetLineageEvent) -> DatasetDependencyNode:
    status = event.status or "?"
    ts = event.timestamp.strftime("%Y-%m-%d %H:%M")
    leaf_label = f"{event.label or event.job_id or 'job'} ({status}, {ts})"
    return DatasetDependencyNode(label=leaf_label, kind="Job")


def build_dependency_tree(dataset_label: str, events: list[DatasetLineageEvent], strategy_names: list[str]) -> DatasetDependencyNode:
    used_by_events = [e for e in events if e.kind in _CATEGORY_LABELS]

    by_strategy: dict[str, list[DatasetLineageEvent]] = {}
    for event in used_by_events:
        strategy = _matched_strategy(event.label, strategy_names) or _UNATTRIBUTED_STRATEGY
        by_strategy.setdefault(strategy, []).append(event)

    strategy_nodes: list[DatasetDependencyNode] = []
    for strategy_name, strategy_events in sorted(by_strategy.items(), key=lambda kv: (kv[0] == _UNATTRIBUTED_STRATEGY, kv[0])):
        by_category: dict[str, list[DatasetLineageEvent]] = {}
        for event in strategy_events:
            by_category.setdefault(_CATEGORY_LABELS[event.kind], []).append(event)

        category_nodes = [
            DatasetDependencyNode(
                label=f"{category} ({len(cat_events)})",
                kind="Category",
                children=tuple(_job_leaf(e) for e in sorted(cat_events, key=lambda e: e.timestamp, reverse=True)),
            )
            for category, cat_events in sorted(by_category.items())
        ]
        strategy_nodes.append(DatasetDependencyNode(label=strategy_name, kind="Strategy", children=tuple(category_nodes)))

    return DatasetDependencyNode(label=dataset_label, kind="Dataset", children=tuple(strategy_nodes))
