"""
Streamlit page: MT5 JSON Bridge.

The central UI for the Institutional MT5 JSON Bridge (Phase 19.1) -- a
production-grade, READ-ONLY structured-data exchange layer built on top
of the Phase 19.0 MT5 Integration Layer. Everything here is
information exchange: exporting a versioned JSON document (terminal,
account, symbols, positions, orders, history, ticks, health,
diagnostics, compatibility) and importing CONFIGURATION-ONLY requests
(select symbol, set timeframe, history/diagnostic/health/refresh
requests). There is no order execution, no trade instruction anywhere
-- `BridgeImportKind` has no trade-related member, so one is not
representable, and `bridge_import.parse_import` additionally hard-
rejects any payload carrying a forbidden trade-related keyword.

Same 3-column Explorer/Workspace/Information shell, toolbar, tabs, and
notification/command-bar/status-bar conventions as every other
institutional page, `mtb_*` session-state prefix.
"""

import streamlit as st

from app.job_manager import get_job_manager
from app.mt5 import ConnectionState, get_bridge_exchange_manager, get_mt5_manager
from app.mt5.bridge_import import BridgeImportKind
from app.mt5.bridge_serializer import pretty_json
from app.mt5.bridge_validator import KNOWN_FIELDS, MAX_PAYLOAD_BYTES, REQUIRED_FIELDS
from app.ui.components import (
    notify,
    render_command_bar,
    render_info_card,
    render_notification_center,
    render_shell,
    render_status_bar,
)

st.set_page_config(page_title="MT5 JSON Bridge - QuantForge AI", page_icon="🌉", layout="wide")

header_cols = st.columns([5, 1, 1])
header_cols[0].title("MT5 JSON Bridge")
with header_cols[1]:
    render_notification_center()
with header_cols[2]:
    render_command_bar("MT5 JSON Bridge")
st.caption(
    "Read-only, versioned JSON exchange layer. Export produces a structured document; Import accepts "
    "configuration requests only -- there is no trade-related field or transport anywhere in this build."
)

manager = get_mt5_manager()
bridge = get_bridge_exchange_manager()

st.session_state.setdefault("mtb_last_export", None)
st.session_state.setdefault("mtb_last_import_result", None)

explorer_col, workspace_col, info_col = render_shell()

with explorer_col:
    st.subheader("Explorer")
    health = bridge.get_health()
    with st.container(border=True):
        st.markdown(f"**Schema Version:** {health.schema_version}")
        st.markdown(f"**Bridge Version:** {health.bridge_version}")
        st.markdown(f"**Connection:** {manager.connection_state.value}")

    st.markdown("**Recent Bridge Activity**")
    events = bridge.list_recent_audit_events(limit=10)
    if not events:
        st.caption("No bridge activity yet -- export or import something.")
    for event in events:
        st.caption(f"{event.event_type.value} — {event.timestamp.strftime('%H:%M:%S')}")

with workspace_col:
    tabs = st.tabs(["Overview", "Export", "Import", "Schema", "Payload", "Validation", "Health", "Audit", "Statistics", "Explorer"])
    (
        overview_tab, export_tab, import_tab, schema_tab, payload_tab,
        validation_tab, health_tab, audit_tab, statistics_tab, explorer_tab,
    ) = tabs

    with overview_tab:
        cols = st.columns(4)
        cols[0].metric("Export Count", health.export_count)
        cols[1].metric("Import Count", health.import_count)
        cols[2].metric("Transport Status", health.transport_status)
        cols[3].metric("Checksum Status", health.checksum_status)
        st.markdown(f"**Connection State:** {manager.connection_state.value}")
        st.caption("This bridge performs information exchange only -- no order execution, no trade instruction.")

    with export_tab:
        st.caption("Builds a real, versioned JSON document from live read-only MT5 data.")
        with st.form("mtb_export_form"):
            sections = st.multiselect(
                "Sections",
                ["terminal", "account", "symbols", "positions", "orders", "health", "diagnostics", "compatibility"],
                default=["terminal", "account", "symbols", "positions", "orders", "health", "diagnostics", "compatibility"],
            )
            history_symbol = st.text_input("History/Ticks Symbol (optional)", key="mtb_export_symbol")
            timeframe = st.text_input("History Timeframe", value="H1")
            submitted = st.form_submit_button("Generate Export")
            if submitted:
                document = bridge.export(
                    include=set(sections) or None,
                    history_symbol=history_symbol.strip() or None,
                    history_timeframe=timeframe.strip() or "H1",
                    tick_symbol=history_symbol.strip() or None,
                )
                st.session_state.mtb_last_export = document
                notify("info", "Export generated.")
                st.rerun()
        if st.session_state.mtb_last_export:
            st.markdown(f"**Checksum:** `{st.session_state.mtb_last_export.get('checksum', '')}`")
            st.json(st.session_state.mtb_last_export)

    with import_tab:
        st.caption("Paste a configuration-only import request. Trade-related fields are structurally rejected.")
        st.markdown("**Supported kinds:** " + ", ".join(k.value for k in BridgeImportKind))
        example = '{\n  "kind": "HEALTH_REQUEST",\n  "params": {}\n}'
        raw_request = st.text_area("Import Request JSON", value=example, height=180, key="mtb_import_raw")
        if st.button("Validate & Apply", key="mtb_apply_import"):
            result = bridge.import_request(raw_request)
            st.session_state.mtb_last_import_result = {"success": result.success, "issues": result.issues, "result": result.result}
            if result.success:
                notify("info", "Import applied.")
            else:
                notify("error", "; ".join(result.issues) if result.issues else "Import rejected.")
            st.rerun()
        if st.session_state.mtb_last_import_result:
            st.json(st.session_state.mtb_last_import_result)

    with schema_tab:
        st.markdown(f"**Schema Version:** {bridge.schema_version()}")
        st.markdown(f"**Required Fields:** {', '.join(sorted(REQUIRED_FIELDS))}")
        st.markdown(f"**Max Payload Size:** {MAX_PAYLOAD_BYTES:,} bytes")
        st.dataframe(
            [{"Field": name, "Type": type_.__name__} for name, type_ in sorted(KNOWN_FIELDS.items())],
            use_container_width=True,
            hide_index=True,
        )
        st.caption("Forward/backward compatible: unknown fields are flagged, not fatal by construction; new fields may be added additively in a future minor version.")

    with payload_tab:
        if st.session_state.mtb_last_export:
            st.code(pretty_json(st.session_state.mtb_last_export), language="json")
        else:
            st.caption("Generate an export in the Export tab to see its pretty-printed payload here.")

    with validation_tab:
        st.caption("Paste any JSON document to validate it against the bridge schema.")
        default_doc = pretty_json(st.session_state.mtb_last_export) if st.session_state.mtb_last_export else "{}"
        doc_to_validate = st.text_area("Document JSON", value=default_doc, height=200, key="mtb_validate_raw")
        if st.button("Validate", key="mtb_run_validate"):
            issues = bridge.validate(doc_to_validate)
            st.session_state.mtb_validation_issues = issues
            if issues:
                notify("warning", f"{len(issues)} validation issue(s) found.")
            else:
                notify("info", "Document is valid.")
            st.rerun()
        stored_issues = st.session_state.get("mtb_validation_issues")
        if stored_issues is not None:
            if stored_issues:
                st.dataframe([{"Issue": i} for i in stored_issues], use_container_width=True, hide_index=True)
            else:
                st.success("No issues found.")

    with health_tab:
        cols = st.columns(3)
        cols[0].metric("Export Count", health.export_count)
        cols[1].metric("Import Count", health.import_count)
        cols[2].metric("Payload Count", health.payload_count)
        render_info_card("Bridge Health", [
            ("Bridge Version", health.bridge_version),
            ("Schema Version", health.schema_version),
            ("Last Export", health.last_export_at.strftime("%Y-%m-%d %H:%M:%S") if health.last_export_at else "—"),
            ("Last Import", health.last_import_at.strftime("%Y-%m-%d %H:%M:%S") if health.last_import_at else "—"),
            ("Last Validation", health.last_validation_at.strftime("%Y-%m-%d %H:%M:%S") if health.last_validation_at else "—"),
            ("Last Validation OK", health.last_validation_ok if health.last_validation_ok is not None else "—"),
            ("Transport Status", health.transport_status),
            ("Checksum Status", health.checksum_status),
        ])

    with audit_tab:
        all_events = bridge.list_recent_audit_events(limit=100)
        if all_events:
            st.dataframe(
                [{"Event": e.event_type.value, "Key": e.key, "Timestamp": e.timestamp.isoformat(timespec="seconds")} for e in all_events],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("No bridge audit events yet.")

    with statistics_tab:
        events = bridge.list_recent_audit_events(limit=200)
        counts: dict[str, int] = {}
        for event in events:
            counts[event.event_type.value] = counts.get(event.event_type.value, 0) + 1
        if counts:
            st.dataframe([{"Event Type": k, "Count": v} for k, v in sorted(counts.items())], use_container_width=True, hide_index=True)
        else:
            st.caption("No statistics yet.")

    with explorer_tab:
        st.caption("Transports registered for a future real bridge (all disabled -- no live IPC/network exists in this build).")
        for transport in bridge.list_transports():
            with st.container(border=True):
                st.markdown(f"**{transport.display_name}**")
                st.caption(transport.description)
                st.button("Connect", key=f"mtb_connect_{transport.display_name}", disabled=True, help="Not implemented -- no real IPC/network transport exists in this build.")

with info_col:
    st.subheader("Information")
    render_info_card("MT5 JSON Bridge", [
        ("Connection State", manager.connection_state.value),
        ("Export Count", health.export_count),
        ("Import Count", health.import_count),
    ])

render_status_bar(
    module="MT5 JSON Bridge",
    execution_status="Connected" if manager.connection_state == ConnectionState.CONNECTED else manager.connection_state.value,
    **get_job_manager().status_counts(),
)
