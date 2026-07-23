"""
Streamlit page: Data Catalog.

The institutional Data Catalog (Phase 17.5) -- a read-only governance
layer on top of Dataset Manager (Phase 18.6): lineage, a dependency
tree, usage analytics, catalog-wide search/filters, and its own audit
trail. This page never modifies `DatasetManager`, `JobManager`, or
`StrategyLibraryManager` state directly -- Archive/Restore/Delete call
straight through to the unchanged `DatasetManager` methods, and the
catalog only ever adds its own owner/notes overlay and observed lineage.

Built on the same 3-column Explorer/Workspace/Information shell,
toolbar, tabs, and notification/command-bar/status-bar conventions as
Dataset Manager (Phase 18.6) and every other dashboard.
"""

import streamlit as st

from app.data_catalog import DataCatalog
from app.dataset_manager.exceptions import ProtectedDatasetError
from app.ui.components import (
    ToolbarAction,
    notify,
    render_command_bar,
    render_info_card,
    render_notification_center,
    render_shell,
    render_status_bar,
    render_toolbar,
)

st.set_page_config(page_title="Data Catalog - QuantForge AI", page_icon="🗂️", layout="wide")

header_cols = st.columns([5, 1, 1])
header_cols[0].title("Data Catalog")
with header_cols[1]:
    render_notification_center()
with header_cols[2]:
    render_command_bar("Data Catalog")
st.caption(
    "Institutional catalog, lineage and dependency governance over every managed dataset. Read-only over "
    "Dataset Manager/Job Manager/Strategy Library -- this page never modifies engine, job, or strategy state."
)

catalog = DataCatalog()

st.session_state.setdefault("dc_selected_id", None)
st.session_state.setdefault("dc_delete_armed", False)

explorer_col, workspace_col, info_col = render_shell()

with explorer_col:
    st.subheader("Explorer")

    stats = catalog.catalog_statistics()
    stat_cols = st.columns(2)
    stat_cols[0].metric("Datasets", stats["total_datasets"])
    stat_cols[1].metric("Avg Quality", f"{stats['average_quality']}%" if stats["average_quality"] is not None else "—")

    query = st.text_input("Search", key="dc_search_query", placeholder="UUID, filename, symbol, tag, owner...")

    filter_choice = st.selectbox(
        "Filter",
        ["All", "Favorites", "Archived", "Recently Used", "Highest Quality", "Largest Dataset", "Unused", "Protected"],
        key="dc_filter_choice",
    )

    def _apply_filter(entries):
        if filter_choice == "Favorites":
            return [e for e in entries if e.favorite]
        if filter_choice == "Archived":
            return [e for e in entries if e.archived]
        if filter_choice == "Recently Used":
            return sorted((e for e in entries if e.last_used is not None), key=lambda e: e.last_used, reverse=True)
        if filter_choice == "Highest Quality":
            return sorted(entries, key=lambda e: e.quality_score, reverse=True)
        if filter_choice == "Largest Dataset":
            return sorted(entries, key=lambda e: e.version_count, reverse=True)
        if filter_choice == "Unused":
            return [e for e in entries if e.last_used is None]
        if filter_choice == "Protected":
            return [e for e in entries if e.protected]
        return [e for e in entries if not e.archived]

    entries = catalog.search(query) if query.strip() else catalog.list_catalog(archived=None)
    entries = _apply_filter(entries)

    if not entries:
        st.caption("Nothing here.")
    for entry in entries:
        with st.container(border=True):
            is_selected = st.session_state.dc_selected_id == entry.id
            star = "⭐ " if entry.favorite else ""
            lock = "🔒 " if entry.protected else ""
            archived_tag = " (archived)" if entry.archived else ""
            st.markdown(f"{'▶ ' if is_selected else ''}{star}{lock}**{entry.display_name}**{archived_tag}")
            st.caption(f"Quality {entry.quality_score}% · Owner: {entry.owner or '—'}")
            if st.button("Select", key=f"dc_select_{entry.id}", use_container_width=True, disabled=is_selected):
                st.session_state.dc_selected_id = entry.id
                st.rerun()

with workspace_col:
    selected_id = st.session_state.dc_selected_id
    selected = catalog.get(selected_id) if selected_id else None

    toolbar_clicked = render_toolbar(
        [
            ToolbarAction("🔄 Refresh Catalog", "sync", enabled=True),
            ToolbarAction(
                "🗄 Archive" if not (selected and selected.archived) else "↩ Restore",
                "archive_toggle",
                enabled=selected is not None,
                disabled_reason=None if selected else "Select a dataset first.",
            ),
            ToolbarAction(
                "🗑 Delete",
                "delete",
                enabled=selected is not None and not selected.protected,
                disabled_reason="Protected datasets cannot be deleted." if selected and selected.protected else (None if selected else "Select a dataset first."),
            ),
        ]
    )

    if toolbar_clicked.get("sync"):
        count = catalog.sync()
        notify("success", f"Catalog synced: {count} lineage event(s) recorded.")
        st.rerun()

    if selected is not None:
        from app.dataset_manager import DatasetManager

        datasets = DatasetManager()

        if toolbar_clicked.get("archive_toggle"):
            st.session_state.dc_archive_warn = True
        if toolbar_clicked.get("delete"):
            st.session_state.dc_delete_armed = True

    if selected is None:
        st.info("Select a dataset in the Explorer to view its catalog entry.")
        render_status_bar(module="Data Catalog", execution_status="Ready")
        st.stop()

    impact = catalog.impact(selected.id)
    if st.session_state.get("dc_archive_warn") or st.session_state.dc_delete_armed:
        if impact["total_references"] > 0:
            st.warning(
                f"This dataset is referenced by: {impact['strategies']} strategy(ies), {impact['backtests']} backtest(s), "
                f"{impact['optimizations']} optimization(s), {impact['validations']} validation(s), "
                f"{impact['replay_sessions']} replay session(s), {impact['reports']} report(s). "
                "This is a warning only -- the action below is never blocked."
            )
        else:
            st.info("No observed references to this dataset yet.")

    if st.session_state.get("dc_archive_warn"):
        confirm_cols = st.columns(2)
        if confirm_cols[0].button("Confirm " + ("Restore" if selected.archived else "Archive"), type="primary"):
            if selected.archived:
                datasets.restore(selected.id)
                notify("info", f"Restored '{selected.display_name}'.")
            else:
                datasets.archive(selected.id)
                notify("info", f"Archived '{selected.display_name}'.")
            st.session_state.dc_archive_warn = False
            st.rerun()
        if confirm_cols[1].button("Cancel"):
            st.session_state.dc_archive_warn = False
            st.rerun()

    if st.session_state.dc_delete_armed:
        confirm_cols = st.columns(2)
        if confirm_cols[0].button("Confirm Delete", type="primary"):
            try:
                datasets.delete(selected.id)
            except ProtectedDatasetError as exc:
                st.error(str(exc))
            else:
                st.session_state.dc_selected_id = None
                st.session_state.dc_delete_armed = False
                notify("warning", f"Deleted '{selected.display_name}'.")
                st.rerun()
        if confirm_cols[1].button("Cancel", key="dc_delete_cancel"):
            st.session_state.dc_delete_armed = False
            st.rerun()

    catalog_tab, lineage_tab, dependencies_tab, usage_tab, quality_tab, history_tab, audit_tab = st.tabs(
        ["Catalog", "Lineage", "Dependencies", "Usage", "Quality", "History", "Audit"]
    )

    with catalog_tab:
        with st.form("dc_owner_form"):
            owner = st.text_input("Owner", value=selected.owner)
            notes = st.text_area("Catalog notes", value="")
            submitted = st.form_submit_button("Save")
            if submitted:
                catalog.set_owner(selected.id, owner)
                catalog.set_catalog_notes(selected.id, notes)
                notify("success", "Catalog metadata saved.")
                st.rerun()
        st.json(
            {
                "id": selected.id,
                "filename": selected.filename,
                "display_name": selected.display_name,
                "description": selected.description,
                "owner": selected.owner,
                "created": selected.created.isoformat(),
                "modified": selected.modified.isoformat(),
                "imported": selected.imported.isoformat(),
                "last_used": selected.last_used.isoformat() if selected.last_used else None,
                "source": selected.source,
                "hash": selected.hash,
                "version_count": selected.version_count,
                "tags": list(selected.tags),
                "quality_score": selected.quality_score,
                "favorite": selected.favorite,
                "archived": selected.archived,
                "protected": selected.protected,
            }
        )

    with lineage_tab:
        events = catalog.lineage(selected.id)
        if not events:
            st.caption("No lineage recorded yet. Click \"Refresh Catalog\" to sync.")
        else:
            st.dataframe(
                [
                    {
                        "Event": e.kind.value,
                        "Timestamp": e.timestamp.isoformat(timespec="seconds"),
                        "Status": e.status or "—",
                        "Owner Page": e.owner_page or "—",
                        "Confidence": "Inferred" if e.inferred else "Exact",
                    }
                    for e in events
                ],
                use_container_width=True,
                hide_index=True,
            )
            st.caption(
                "\"Exact\" events are read directly from Dataset Manager's own audit log/version history. "
                "\"Inferred\" events are best-effort correlations between dataset usage and Job Manager history."
            )

    with dependencies_tab:
        tree = catalog.dependency_tree(selected.id)
        if not tree.children:
            st.caption("No dependents observed yet. Click \"Refresh Catalog\" to sync.")

        def _render_node(node) -> None:
            if not node.children:
                st.caption(f"• {node.label}")
                return
            with st.expander(f"{node.label} ({len(node.children)})"):
                for child in node.children:
                    _render_node(child)

        for strategy_node in tree.children:
            _render_node(strategy_node)

    with usage_tab:
        usage = catalog.usage_stats(selected.id)
        cols = st.columns(4)
        cols[0].metric("Times Used", usage.times_used)
        cols[1].metric("Current Jobs", usage.current_jobs)
        cols[2].metric("Completed Jobs", usage.completed_jobs)
        cols[3].metric("Strategies Referencing", usage.strategies_referencing)
        cols2 = st.columns(4)
        cols2[0].metric("Validation Runs", usage.validation_runs)
        cols2[1].metric("Optimization Runs", usage.optimization_runs)
        cols2[2].metric("Replay Runs", usage.replay_runs)
        cols2[3].metric("Reports Generated", usage.reports_generated)
        st.caption(
            f"Last used: {usage.last_used.strftime('%Y-%m-%d %H:%M') if usage.last_used else '—'} · "
            f"Average runtime: {f'{usage.average_runtime_seconds:,.1f}s' if usage.average_runtime_seconds is not None else '—'}"
        )

    with quality_tab:
        from app.dataset_manager import DatasetManager

        health = DatasetManager().get_health(selected.id)
        st.metric("Quality Score", f"{health.score}%")
        st.progress(health.score / 100)
        if health.warnings:
            st.markdown("**Warnings**")
            for warning in health.warnings:
                st.markdown(f"- {warning}")
        if health.errors:
            st.markdown("**Errors**")
            for error in health.errors:
                st.markdown(f"- {error}")
        if health.suggestions:
            st.markdown("**Recommendations**")
            for suggestion in health.suggestions:
                st.markdown(f"- {suggestion}")
        st.caption("Quality is computed and owned by Dataset Manager -- never recalculated here.")

    with history_tab:
        from app.dataset_manager import DatasetManager

        versions = DatasetManager().list_versions(selected.id)
        if not versions:
            st.caption("No version history yet.")
        else:
            st.dataframe(
                [{"Event": v.event_type.value, "Timestamp": v.timestamp.isoformat(timespec="seconds"), "Note": v.note} for v in versions],
                use_container_width=True,
                hide_index=True,
            )

    with audit_tab:
        audit_events = catalog.audit_events(selected.id)
        if not audit_events:
            st.caption("No catalog audit events yet.")
        else:
            st.dataframe(
                [{"Event": e.event_type.value, "Timestamp": e.timestamp.isoformat(timespec="seconds")} for e in audit_events],
                use_container_width=True,
                hide_index=True,
            )

with info_col:
    st.subheader("Information")
    if selected is not None:
        render_info_card("General", [("Display name", selected.display_name), ("Owner", selected.owner or "—"), ("Description", selected.description or "—")])
        render_info_card("Quality", [("Score", f"{selected.quality_score}%")])
        usage = catalog.usage_stats(selected.id)
        render_info_card("Usage Summary", [("Times used", usage.times_used), ("Strategies", usage.strategies_referencing)])
        lineage_events = catalog.lineage(selected.id)
        render_info_card(
            "Lineage Summary",
            [
                ("Total events", len(lineage_events)),
                ("Exact", sum(1 for e in lineage_events if not e.inferred)),
                ("Inferred", sum(1 for e in lineage_events if e.inferred)),
            ],
        )
    else:
        st.caption("Select a dataset in the Explorer to see its details.")

render_status_bar(
    module="Data Catalog",
    execution_status="Ready" if selected is None else selected.display_name,
)
