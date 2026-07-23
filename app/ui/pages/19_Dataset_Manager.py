"""
Streamlit page: Dataset Manager.

The central UI for the Dataset Manager (Phase 18.6) -- every imported
historical dataset is now a persistent, managed `DatasetRecord`
(`app.dataset_manager`) instead of a session-only upload; this page is
where import/export/rename/duplicate/archive/restore/delete/validate/
reindex/refresh-metadata/generate-statistics live, alongside search,
favorites, tags, version history, and the audit log.

Built on the same 3-column Explorer/Workspace/Information shell,
toolbar, tabs, and notification/command-bar/status-bar conventions
already used by every other dashboard (Phase 18.2/18.3), following the
same list-select pattern as the Job Manager page (Phase 18.4) rather
than Strategy Library's live-editor pattern, since datasets are managed
as whole immutable files, not edited in place.
"""

import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from app.dataset_manager import STANDARD_TAGS, DatasetManager
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

st.set_page_config(page_title="Dataset Manager - QuantForge AI", page_icon="🗄️", layout="wide")

header_cols = st.columns([5, 1, 1])
header_cols[0].title("Dataset Manager")
with header_cols[1]:
    render_notification_center()
with header_cols[2]:
    render_command_bar("Dataset Manager")
st.caption(
    "Central registry for every imported historical dataset -- import, search, tag, favorite, archive, "
    "validate, and export. This page never touches any trading/strategy/backtesting engine."
)

manager = DatasetManager()

st.session_state.setdefault("dm_selected_id", None)
st.session_state.setdefault("dm_delete_armed", False)

explorer_col, workspace_col, info_col = render_shell()

with explorer_col:
    st.subheader("Explorer")

    with st.expander("➕ Import dataset"):
        uploaded = st.file_uploader("CSV file (standard or MT5 export format)", type=["csv"], key="dm_import_uploader")
        if uploaded is not None and st.button("Import", key="dm_import_confirm"):
            record = manager.import_dataset_from_bytes(uploaded.getvalue(), filename=uploaded.name)
            st.session_state.dm_selected_id = record.id
            notify("success", f"Imported '{record.display_name}'.")
            st.rerun()

    query = st.text_input("Search", key="dm_search_query", placeholder="Filename, symbol, timeframe, tag...")
    tag_filter = st.multiselect("Tags", list(STANDARD_TAGS), key="dm_tag_filter")

    tab_names = ["Imported", "Favorites", "Recent", "Archive"]
    imported_tab, favorites_tab, recent_tab, archive_tab = st.tabs(tab_names)

    def _apply_search_and_tags(records):
        if query.strip():
            records = manager.search(query)
            if tag_filter:
                records = [r for r in records if set(tag_filter) & set(r.tags)]
        elif tag_filter:
            records = [r for r in records if set(tag_filter) & set(r.tags)]
        return records

    def _render_entry_list(records, list_key: str) -> None:
        if not records:
            st.caption("Nothing here.")
            return
        for record in records:
            with st.container(border=True):
                is_selected = st.session_state.dm_selected_id == record.id
                star = "⭐ " if record.favorite else ""
                lock = "🔒 " if record.protected else ""
                st.markdown(f"{'▶ ' if is_selected else ''}{star}{lock}**{record.display_name}**")
                st.caption(f"{record.symbol or '—'} · {record.timeframe or '—'} · {record.rows:,} rows")
                if st.button("Select", key=f"dm_select_{list_key}_{record.id}", use_container_width=True, disabled=is_selected):
                    st.session_state.dm_selected_id = record.id
                    st.rerun()

    with imported_tab:
        _render_entry_list(_apply_search_and_tags(manager.list_entries(archived=False)), "imported")
    with favorites_tab:
        _render_entry_list(_apply_search_and_tags(manager.filter_entries(favorite=True, archived=False)), "favorites")
    with recent_tab:
        _render_entry_list(manager.list_recent(), "recent")
    with archive_tab:
        _render_entry_list(_apply_search_and_tags(manager.list_entries(archived=True)), "archive")

with workspace_col:
    selected_id = st.session_state.dm_selected_id
    selected = manager.get(selected_id) if selected_id else None

    toolbar_clicked = render_toolbar(
        [
            ToolbarAction("📤 Export", "export", enabled=selected is not None, disabled_reason=None if selected else "Select a dataset first."),
            ToolbarAction("✎ Rename", "rename", enabled=selected is not None, disabled_reason=None if selected else "Select a dataset first."),
            ToolbarAction("⧉ Duplicate", "duplicate", enabled=selected is not None, disabled_reason=None if selected else "Select a dataset first."),
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
            ToolbarAction("✓ Validate", "validate", enabled=selected is not None, disabled_reason=None if selected else "Select a dataset first."),
            ToolbarAction("⟲ Reindex", "reindex", enabled=selected is not None, disabled_reason=None if selected else "Select a dataset first."),
            ToolbarAction("🔄 Refresh Metadata", "refresh_metadata", enabled=selected is not None, disabled_reason=None if selected else "Select a dataset first."),
        ]
    )

    if selected is not None:
        if toolbar_clicked.get("rename"):
            st.session_state.dm_rename_open = True
        if toolbar_clicked.get("duplicate"):
            dup = manager.duplicate(selected.id)
            st.session_state.dm_selected_id = dup.id
            notify("success", f"Duplicated as '{dup.display_name}'.")
            st.rerun()
        if toolbar_clicked.get("archive_toggle"):
            if selected.archived:
                manager.restore(selected.id)
                notify("info", f"Restored '{selected.display_name}'.")
            else:
                manager.archive(selected.id)
                notify("info", f"Archived '{selected.display_name}'.")
            st.rerun()
        if toolbar_clicked.get("delete"):
            st.session_state.dm_delete_armed = True
        if toolbar_clicked.get("validate"):
            _, health = manager.revalidate(selected.id)
            notify("success" if health.score >= 80 else "warning", f"Revalidated: quality score {health.score}%.")
            st.rerun()
        if toolbar_clicked.get("reindex"):
            manager.reindex(selected.id)
            notify("success", "Reindexed.")
            st.rerun()
        if toolbar_clicked.get("refresh_metadata"):
            manager.refresh_metadata(selected.id)
            notify("success", "Metadata refreshed.")
            st.rerun()

    if selected is None:
        st.info("Select a dataset in the Explorer, or import a new one.")
        render_status_bar(module="Dataset Manager", execution_status="Ready")
        st.stop()

    if st.session_state.get("dm_rename_open"):
        with st.form("dm_rename_form"):
            new_name = st.text_input("New display name", value=selected.display_name)
            submitted = st.form_submit_button("Save")
            if submitted:
                manager.rename(selected.id, new_name)
                st.session_state.dm_rename_open = False
                notify("success", "Renamed.")
                st.rerun()

    if st.session_state.dm_delete_armed:
        st.warning(f"Delete '{selected.display_name}'? This cannot be undone.")
        confirm_cols = st.columns(2)
        if confirm_cols[0].button("Confirm Delete", type="primary"):
            try:
                manager.delete(selected.id)
            except ProtectedDatasetError as exc:
                st.error(str(exc))
            else:
                st.session_state.dm_selected_id = None
                st.session_state.dm_delete_armed = False
                notify("warning", f"Deleted '{selected.display_name}'.")
                st.rerun()
        if confirm_cols[1].button("Cancel"):
            st.session_state.dm_delete_armed = False
            st.rerun()

    if toolbar_clicked.get("export"):
        st.session_state.dm_export_open = True
    if st.session_state.get("dm_export_open"):
        with st.form("dm_export_form"):
            fmt = st.selectbox("Format", ["csv", "parquet", "sqlite"])
            submitted = st.form_submit_button("Export")
            if submitted:
                suffix = {"csv": ".csv", "parquet": ".parquet", "sqlite": ".db"}[fmt]
                mime = {"csv": "text/csv", "parquet": "application/octet-stream", "sqlite": "application/octet-stream"}[fmt]
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp_path = Path(tmp.name)
                manager.export(selected.id, tmp_path, fmt)
                payload = tmp_path.read_bytes()
                tmp_path.unlink(missing_ok=True)
                st.download_button("Download", data=payload, file_name=f"{selected.display_name}{suffix}", mime=mime)

    preview_tab, statistics_tab, health_tab, metadata_tab, versions_tab, audit_tab = st.tabs(
        ["Preview", "Statistics", "Health", "Metadata", "Version History", "Audit Log"]
    )

    with preview_tab:
        preview = manager.preview(selected.id, n=100)
        st.dataframe(pd.DataFrame(list(preview.rows)), use_container_width=True, hide_index=True)
        st.caption(f"Showing {len(preview.rows)} of {preview.total_rows:,} row(s).")
        st.markdown("**Columns**")
        st.dataframe(
            [{"Name": c.name, "Type": c.dtype, "Null Count": c.null_count, "Unique Count": c.unique_count} for c in preview.columns],
            use_container_width=True,
            hide_index=True,
        )

    with statistics_tab:
        stats = manager.generate_statistics(selected.id)
        cols = st.columns(4)
        cols[0].metric("Rows", f"{stats.rows:,}")
        cols[1].metric("Columns", stats.columns)
        cols[2].metric("Candles", f"{stats.candles:,}")
        cols[3].metric("Sessions", stats.sessions)
        cols2 = st.columns(4)
        cols2[0].metric("Symbol", stats.symbol or "—")
        cols2[1].metric("Timeframe", stats.timeframe or "—")
        cols2[2].metric("Memory (KB)", f"{stats.memory_usage_bytes / 1024:,.1f}")
        cols2[3].metric("Disk (KB)", f"{stats.disk_size_bytes / 1024:,.1f}")
        st.caption(f"Date range: {stats.date_range_start or '—'} to {stats.date_range_end or '—'} · Frequency: {stats.frequency or '—'}")

    with health_tab:
        health = manager.get_health(selected.id)
        st.metric("Quality Score", f"{health.score}%")
        st.progress(health.score / 100)
        for check in health.checks:
            st.markdown(f"{'✅' if check.passed else '⚠️'} **{check.name.replace('_', ' ').title()}** — {check.message}")
        if health.suggestions:
            st.markdown("**Suggestions**")
            for suggestion in health.suggestions:
                st.markdown(f"- {suggestion}")

    with metadata_tab:
        with st.form("dm_metadata_form"):
            description = st.text_area("Description", value=selected.description)
            notes = st.text_area("Notes", value=selected.notes)
            tags = st.multiselect("Tags", list(STANDARD_TAGS), default=[t for t in selected.tags if t in STANDARD_TAGS])
            custom_tags = st.text_input("Custom tags (comma-separated)", value=", ".join(t for t in selected.tags if t not in STANDARD_TAGS))
            protected = st.checkbox("Protected (cannot be deleted)", value=selected.protected)
            submitted = st.form_submit_button("Save metadata")
            if submitted:
                manager.set_description(selected.id, description)
                manager.set_notes(selected.id, notes)
                all_tags = list(tags) + [t.strip() for t in custom_tags.split(",") if t.strip()]
                manager.remove_tags(selected.id, selected.tags)
                manager.add_tags(selected.id, all_tags)
                manager.set_protected(selected.id, protected)
                notify("success", "Metadata saved.")
                st.rerun()

        st.markdown("**All fields**")
        st.json(
            {
                "id": selected.id,
                "filename": selected.filename,
                "import_date": selected.import_date.isoformat(),
                "created": selected.created.isoformat(),
                "modified": selected.modified.isoformat(),
                "last_used": selected.last_used.isoformat() if selected.last_used else None,
                "file_size": selected.file_size,
                "hash": selected.hash,
                "checksum": selected.checksum,
                "encoding": selected.encoding,
                "delimiter": selected.delimiter,
                "source": selected.source.value,
                "missing_values": selected.missing_values,
                "duplicate_rows": selected.duplicate_rows,
            }
        )

    with versions_tab:
        versions = manager.list_versions(selected.id)
        if not versions:
            st.caption("No version history yet.")
        else:
            st.dataframe(
                [{"Event": v.event_type.value, "Timestamp": v.timestamp.isoformat(timespec="seconds"), "Note": v.note} for v in versions],
                use_container_width=True,
                hide_index=True,
            )

    with audit_tab:
        events = manager.list_audit_events(selected.id)
        if not events:
            st.caption("No audit events yet.")
        else:
            st.dataframe(
                [{"Event": e.event_type.value, "Timestamp": e.timestamp.isoformat(timespec="seconds")} for e in events],
                use_container_width=True,
                hide_index=True,
            )

with info_col:
    st.subheader("Information")
    if selected is not None:
        render_info_card(
            "General",
            [
                ("Display name", selected.display_name),
                ("Filename", selected.filename),
                ("Source", selected.source.value),
                ("Favorite", "Yes" if selected.favorite else "No"),
                ("Archived", "Yes" if selected.archived else "No"),
            ],
        )
        fav_label = "☆ Unfavorite" if selected.favorite else "⭐ Favorite"
        if st.button(fav_label, key="dm_toggle_favorite", use_container_width=True):
            manager.toggle_favorite(selected.id)
            st.rerun()
        render_info_card(
            "Statistics",
            [("Rows", f"{selected.rows:,}"), ("Columns", selected.columns), ("Candles", f"{selected.candles:,}"), ("File size", f"{selected.file_size / 1024:,.1f} KB")],
        )
        health = manager.get_health(selected.id)
        render_info_card("Health", [("Score", f"{health.score}%"), ("Warnings", len(health.warnings)), ("Errors", len(health.errors))])
        render_info_card("Metadata", [("Symbol", selected.symbol or "—"), ("Timeframe", selected.timeframe or "—"), ("Hash", selected.checksum)])
        render_info_card("Version", [("Total versions", len(manager.list_versions(selected.id))), ("Modified", selected.modified.strftime("%Y-%m-%d %H:%M"))])
        render_info_card("Tags", [("Tags", ", ".join(selected.tags) or "—")])
        render_info_card("Audit", [("Total events", len(manager.list_audit_events(selected.id)))])
    else:
        st.caption("Select a dataset in the Explorer to see its details.")

render_status_bar(
    module="Dataset Manager",
    execution_status="Ready" if selected is None else selected.display_name,
)
