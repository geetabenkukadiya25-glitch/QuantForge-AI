"""
Streamlit page: Strategy Library (Phase 18 + Phase 18.1 IDE redesign).

A complete offline strategy MANAGEMENT system, presented as an IDE-style
workspace (Explorer / Editor+Tabs / Information panel): new/duplicate/
save/save-as/rename/delete, import/export, live search + filters,
favorites, recent, validation badges, an information panel, local
(git-free) version history, ready-made templates, compile-status
tracking, a three-tier validation panel (Errors/Warnings/Suggestions),
structural statistics, best-effort keyboard shortcuts, local autosave +
crash recovery, a soft same-machine editing lock, and an offline audit log.

UI and management ONLY -- this page never touches strategy execution, the
Strategy Builder, or any engine, and never changes SDL parser/schema
behavior. Every SDL operation (parse/validate/serialize/compile) delegates
to the unmodified `app.sdl` module; `app.strategy_library.StrategyLibraryManager`
is the only new orchestration layer, composed here, never duplicated.

Phase 18.1 is a PRESENTATION-ONLY redesign on top of Phase 18: a 3-column
IDE layout (Explorer / Editor+Tabs / Information), a centered `st.dialog`
for New Strategy, and card-style panels. No manager method, session-state
key, callback, or business-logic behavior changed from Phase 18 -- every
button here calls the exact same `StrategyLibraryManager`/`app.sdl`
functions Phase 18 already called; only their layout moved. Two honest
platform limitations (not fixable at the presentation layer alone):
Streamlit has no true resizable/drag panels (the 3 columns use a fixed
20/60/20 ratio), and `st.tabs` renders every tab's body on each script
run -- Streamlit only CSS-hides the inactive tabs, it does not lazily
skip their code.
"""

import time
import uuid
from pathlib import Path

import streamlit as st

from app.sdl import SDLParseError, SDLValidationError, StrategyCompiler, StrategyParser, StrategySerializer, StrategyValidator
from app.strategy_library import StrategyLibraryManager, list_template_names
from app.strategy_library.exceptions import DuplicateFilenameError, ProtectedStrategyError, StrategyLibraryError
from app.strategy_library.models import ValidationBadge
from app.ui.components import render_command_bar, render_notification_center, render_status_bar
from app.ui.keyboard_shortcuts import render_keyboard_shortcuts

st.set_page_config(page_title="Strategy Library - QuantForge AI", page_icon="📜", layout="wide")

header_cols_top = st.columns([5, 1, 1])
header_cols_top[0].title("Strategy Library")
with header_cols_top[1]:
    render_notification_center()
with header_cols_top[2]:
    render_command_bar("Strategy Library")
st.caption("An IDE-style workspace for SDL strategy documents -- new, duplicate, save, rename, delete, import/export, search, favorites, and version history, all offline.")

manager = StrategyLibraryManager()
parser = StrategyParser()
validator = StrategyValidator()
compiler = StrategyCompiler()
serializer = StrategySerializer()

_BADGE_ICON = {ValidationBadge.VALID: "✅", ValidationBadge.WARNING: "⚠️", ValidationBadge.INVALID: "❌"}
_FILTER_CHIPS = [
    "Forex", "Crypto", "Indices", "Commodities", "Stocks",
    "SMC", "ICT", "Breakout", "Scalping", "Swing", "Mean Reversion", "Trend", "Custom",
]

# ---------------------------------------------------------------------
# Session state -- identical to Phase 18; only `sl_show_new_dialog` is
# new, and it is purely a UI open/closed flag for the New Strategy modal.
# ---------------------------------------------------------------------

if "sl_session_token" not in st.session_state:
    st.session_state.sl_session_token = uuid.uuid4().hex
SESSION_TOKEN = st.session_state.sl_session_token

st.session_state.setdefault("sl_current_path", None)  # Path | None -- None while editing a not-yet-saved new strategy
st.session_state.setdefault("sl_is_open", False)
st.session_state.setdefault("sl_current_fmt", "yaml")
st.session_state.setdefault("sl_last_saved_text", "")
st.session_state.setdefault("sl_editor_textarea", "")
st.session_state.setdefault("sl_pending_editor_text", None)
st.session_state.setdefault("sl_last_autosave_signature", None)
st.session_state.setdefault("sl_last_autosave_check", 0.0)
st.session_state.setdefault("sl_delete_armed", False)
st.session_state.setdefault("sl_dismissed_recoveries", set())
st.session_state.setdefault("sl_jump_section", None)
st.session_state.setdefault("sl_search_query", "")
st.session_state.setdefault("sl_filter_selection", [])
st.session_state.setdefault("sl_favorites_only", False)
st.session_state.setdefault("sl_show_new_dialog", False)  # presentation-only: New Strategy modal open/closed
st.session_state.setdefault("sl_new_dialog_template", "Blank Strategy")  # presentation-only: pre-selected template

# Canonical Streamlit pattern for programmatically changing a `key=`-bound
# widget's value: NEVER write `st.session_state.sl_editor_textarea`
# directly once `st.text_area(key="sl_editor_textarea", ...)` may already
# have run this script pass -- Streamlit forbids that
# (StreamlitAPIException). Instead, every place that wants to change the
# editor's content (open/new/close/restore/...) stages the new text in
# `sl_pending_editor_text` and triggers `st.rerun()`. This block is the
# ONLY place that ever assigns to `sl_editor_textarea` from code, and it
# runs unconditionally at the very top of the script -- always before the
# widget is (re)created -- so the assignment is always safe.
if st.session_state.sl_pending_editor_text is not None:
    st.session_state.sl_editor_textarea = st.session_state.sl_pending_editor_text
    st.session_state.sl_pending_editor_text = None


def _rerun_preserving_editor() -> None:
    """Use instead of a bare `st.rerun()` from any call site that wants
    to refresh the page WITHOUT changing editor content (Favorite,
    Delete's arm step, opening the New Strategy dialog, dismissing/
    discarding an unrelated crash-recovery record, ...).

    Root cause this works around: Streamlit resets a `key=`-bound
    widget's session-state value to its un-set default the moment a
    script run calls `st.rerun()` before that widget is (re)instantiated
    in that same run -- true for every one of the call sites above, since
    they all sit in code positioned before the editor's
    `st.text_area(...)` line. Confirmed by direct instrumentation: the
    widget's value is still correct right up to the `st.rerun()` call,
    but has already been reset by Streamlit before the NEXT run's first
    line of user code executes -- so it cannot be recovered after the
    fact (a shadow-copy fallback checked at the top of the next run is
    too late; Streamlit's reset happens before that point). The fix is to
    re-stage the CURRENT (still-correct, pre-rerun) value through the
    exact same `sl_pending_editor_text` mechanism `_open_strategy`/
    `_start_new_draft` already use, so the top-of-script block above
    reapplies it before the widget is recreated.
    """
    st.session_state.sl_pending_editor_text = st.session_state.sl_editor_textarea
    st.rerun()


def _current_path() -> Path | None:
    return st.session_state.sl_current_path


def _is_dirty() -> bool:
    return st.session_state.sl_editor_textarea != st.session_state.sl_last_saved_text


def _release_current_lock() -> None:
    path = _current_path()
    if path is not None and not manager.is_protected(path):
        manager.release_lock(path, SESSION_TOKEN)


def _open_strategy(path: Path, record_history: bool = True) -> None:
    _release_current_lock()
    text = manager.load_text(path)
    st.session_state.sl_current_path = path
    st.session_state.sl_is_open = True
    st.session_state.sl_current_fmt = manager.detect_format(path)
    st.session_state.sl_last_saved_text = text
    st.session_state.sl_pending_editor_text = text
    st.session_state.sl_last_autosave_signature = text
    st.session_state.sl_delete_armed = False
    st.session_state.sl_jump_section = None
    if not manager.is_protected(path):
        manager.acquire_lock(path, SESSION_TOKEN)
    if record_history:
        manager.record_recent(path)
        manager.record_opened(path)


def _start_new_draft(text: str, fmt: str) -> None:
    _release_current_lock()
    st.session_state.sl_current_path = None
    st.session_state.sl_is_open = True
    st.session_state.sl_current_fmt = fmt
    st.session_state.sl_last_saved_text = ""
    st.session_state.sl_pending_editor_text = text
    st.session_state.sl_last_autosave_signature = text
    st.session_state.sl_delete_armed = False
    st.session_state.sl_jump_section = None


def _close_strategy() -> None:
    _release_current_lock()
    st.session_state.sl_current_path = None
    st.session_state.sl_is_open = False
    st.session_state.sl_pending_editor_text = ""
    st.session_state.sl_last_saved_text = ""


def _after_save(new_path: Path) -> None:
    manager.discard_autosave(_current_path(), SESSION_TOKEN)
    _open_strategy(new_path, record_history=False)


# ---------------------------------------------------------------------
# Crash recovery (rule 27) -- shown before anything else, unchanged logic
# ---------------------------------------------------------------------

recoverable = [
    r for r in manager.list_recoverable_autosaves()
    if r.key not in st.session_state.sl_dismissed_recoveries
]
if recoverable:
    with st.container(border=True):
        st.warning(f"🛟 Recovered Strategy Found ({len(recoverable)})")
        for record in recoverable:
            original_path = manager.path_from_state_key(record.original_key) if record.original_key else None
            label = original_path.name if original_path else "(new, unsaved strategy)"
            st.markdown(f"**{label}** -- autosaved {record.saved_at.isoformat(timespec='seconds')}")
            cols = st.columns(4)
            if cols[0].button("Restore", key=f"recover_restore_{record.key}"):
                _start_new_draft(record.content, record.fmt)
                if original_path is not None:
                    st.session_state.sl_current_path = original_path
                    st.session_state.sl_last_saved_text = manager.load_text(original_path) if original_path.exists() else ""
                st.session_state.sl_dismissed_recoveries.add(record.key)
                st.rerun()
            if cols[1].button("Discard", key=f"recover_discard_{record.key}"):
                manager.discard_autosave(original_path, record.key.split(":", 1)[-1] if record.original_key is None else SESSION_TOKEN)
                st.session_state.sl_dismissed_recoveries.add(record.key)
                _rerun_preserving_editor()
            with cols[2].popover("Compare"):
                left, right = st.columns(2)
                left.caption("Original (on disk)")
                left.code(manager.load_text(original_path) if original_path and original_path.exists() else "(no file on disk)", language="yaml")
                right.caption("Autosaved")
                right.code(record.content, language=record.fmt)
            if cols[3].button("Dismiss", key=f"recover_dismiss_{record.key}"):
                st.session_state.sl_dismissed_recoveries.add(record.key)
                _rerun_preserving_editor()

render_keyboard_shortcuts()


# =======================================================================
# New Strategy -- centered modal dialog (was a sidebar popover in Phase
# 18). Reuses the exact same `manager.new_strategy` /
# `manager.new_strategy_from_template` calls. The extra Description /
# Market / Primary Symbol / Primary Timeframe fields are applied via the
# SAME `load_definition()` + `.model_copy(update=...)` + `save()` pattern
# every other flow on this page already uses (see Rename) -- no new
# manager method, no SDL model change.
# =======================================================================


@st.dialog("Create New Strategy")
def _new_strategy_dialog() -> None:
    with st.form("sl_new_form"):
        filename = st.text_input("Filename", value="my_strategy.yaml")
        name = st.text_input("Strategy Name", value="My Strategy")
        author = st.text_input("Author", value="")
        description = st.text_area("Description", value="", height=80)
        template_options = ["Blank Strategy"] + [t for t in list_template_names() if t != "Blank Strategy"]
        preselected = st.session_state.sl_new_dialog_template
        template = st.selectbox("Template", template_options, index=template_options.index(preselected) if preselected in template_options else 0)
        market_asset_class = st.text_input("Market / Asset Class", value="forex")
        primary_symbol = st.text_input("Primary Symbol", value="EURUSD")
        primary_timeframe = st.text_input("Primary Timeframe", value="H1")

        cancel_col, create_col = st.columns(2)
        cancelled = cancel_col.form_submit_button("Cancel", use_container_width=True)
        created = create_col.form_submit_button("Create", type="primary", use_container_width=True)

    if cancelled:
        st.session_state.sl_show_new_dialog = False
        st.session_state.sl_new_dialog_template = "Blank Strategy"
        _rerun_preserving_editor()

    if created:
        try:
            if template == "Blank Strategy":
                path = manager.new_strategy(filename, name, author=author or None)
            else:
                path = manager.new_strategy_from_template(template, filename, name, author=author or None)

            updates: dict = {}
            if description:
                base = manager.load_definition(path)
                updates["metadata"] = base.metadata.model_copy(update={"description": description})
            if market_asset_class or primary_symbol or primary_timeframe:
                base = manager.load_definition(path)
                if market_asset_class:
                    updates["market"] = base.market.model_copy(update={"asset_class": market_asset_class})
                if primary_symbol:
                    updates["symbols"] = [primary_symbol]
                if primary_timeframe:
                    updates["timeframes"] = [primary_timeframe]
                    updates["primary_timeframe"] = primary_timeframe
            if updates:
                definition = manager.load_definition(path).model_copy(update=updates)
                manager.save(definition, filename, fmt="yaml", overwrite=True)
        except (DuplicateFilenameError, SDLValidationError, StrategyLibraryError) as exc:
            st.error(str(exc))
        else:
            st.session_state.sl_show_new_dialog = False
            st.session_state.sl_new_dialog_template = "Blank Strategy"
            _open_strategy(path)
            st.rerun()


if st.session_state.sl_show_new_dialog:
    _new_strategy_dialog()

# =======================================================================
# 3-column IDE layout: Explorer (20%) / Editor + Tabs (60%) / Information (20%)
# Streamlit has no drag-resizable columns -- this is a fixed-ratio
# approximation of the requested 20/60/20 split.
# =======================================================================

left_col, center_col, right_col = st.columns([1, 3, 1], gap="medium")

# -----------------------------------------------------------------------
# LEFT PANEL -- Strategy Explorer: search, filters, favorites, recent,
# and a folder tree (Examples / My Strategies / Templates / Favorites /
# Archive). Same `manager.list_entries()` / `search()` / `filter_entries()`
# / `toggle_favorite()` / `list_recent()` calls Phase 18 already used --
# only their container changed from `st.sidebar` to this column.
# -----------------------------------------------------------------------

with left_col:
    st.subheader("Strategy Explorer")

    explorer_action_cols = st.columns(2)
    if explorer_action_cols[0].button("➕ New", use_container_width=True, type="primary"):
        st.session_state.sl_show_new_dialog = True
        _rerun_preserving_editor()

    with explorer_action_cols[1].popover("⬆️ Import", use_container_width=True):
        # Lives in the Explorer (not the center toolbar) so it stays
        # reachable even with nothing open yet -- matching Phase 18's
        # sidebar placement (a hard "Import must keep working" backward-
        # compatibility requirement; the center toolbar only renders once
        # a strategy is already open).
        uploaded = st.file_uploader("SDL file", type=["yaml", "yml", "json"], key="sl_import_uploader")
        import_overwrite = st.checkbox("Overwrite if a file with this name exists", value=False)
        if uploaded is not None and st.button("Import"):
            import tempfile

            suffix = Path(uploaded.name).suffix
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(uploaded.getvalue())
                tmp_path = Path(tmp.name)
            try:
                imported_path = manager.import_file(tmp_path, filename=uploaded.name, overwrite=import_overwrite)
            except SDLParseError as exc:
                st.error(f"Rejected: could not parse '{uploaded.name}': {exc}")
            except SDLValidationError as exc:
                st.error(f"Rejected: '{uploaded.name}' failed validation: {exc}")
            except DuplicateFilenameError as exc:
                st.error(str(exc))
            else:
                st.success(f"Imported '{imported_path.name}'.")
                _open_strategy(imported_path)
                st.rerun()
            finally:
                tmp_path.unlink(missing_ok=True)

    st.text_input("🔎 Search", key="sl_search_query", placeholder="name, id, author, tag, category...")
    st.multiselect("Filters", _FILTER_CHIPS, key="sl_filter_selection")
    st.checkbox("⭐ Favorites only", key="sl_favorites_only")

    all_entries = manager.list_entries()
    visible_entries = manager.search(all_entries, st.session_state.sl_search_query)
    visible_entries = manager.filter_entries(visible_entries, st.session_state.sl_filter_selection)
    if st.session_state.sl_favorites_only:
        visible_entries = [e for e in visible_entries if e.is_favorite]

    st.caption(f"{len(visible_entries)} of {len(all_entries)} strategies")

    def _render_strategy_card(entry, context: str) -> None:
        """One Explorer card: name, protected/favorite/compile/validation/
        unsaved indicators, and an Open action. Selected strategy (the one
        currently in the editor) is visually highlighted.

        `context` disambiguates widget keys when the same strategy can
        legitimately render in more than one folder tab in the same
        script run (e.g. a favorited user strategy appears in both "My
        Strategies" and "Favorites" -- `st.tabs` renders every tab's body
        every run, it only CSS-hides the inactive ones, so both cards
        exist simultaneously and need distinct keys)."""
        is_selected = st.session_state.sl_current_path == entry.path
        card = st.container(border=True)
        title_cols = card.columns([1, 5, 1])
        star = "⭐" if entry.is_favorite else "☆"
        if title_cols[0].button(star, key=f"fav_{context}_{entry.path}"):
            manager.toggle_favorite(entry.path)
            _rerun_preserving_editor()
        name_label = f"**{'▶ ' if is_selected else ''}{entry.name}**{' 🔒' if entry.is_protected else ''}"
        title_cols[1].markdown(name_label)
        title_cols[2].markdown(_BADGE_ICON[entry.validation_badge])

        compile_status = manager.get_compile_status(entry.path)
        compile_icon = "—" if compile_status is None else ("✓" if compile_status.success else "❌")
        unsaved_marker = " · ● unsaved" if is_selected and _is_dirty() else ""
        card.caption(f"{entry.filename} · compile {compile_icon}{unsaved_marker}")

        if card.button("Open", key=f"open_{context}_{entry.path}", use_container_width=True, disabled=is_selected):
            _open_strategy(entry.path)
            st.rerun()

    tree_tabs = st.tabs(["Examples", "My Strategies", "Templates", "Favorites", "Archive"])

    with tree_tabs[0]:
        examples = [e for e in visible_entries if e.is_protected]
        if not examples:
            st.caption("No examples match the current search/filters.")
        for entry in examples:
            _render_strategy_card(entry, context="examples")

    with tree_tabs[1]:
        user_strategies = [e for e in visible_entries if not e.is_protected]
        if not user_strategies:
            st.caption("No user strategies match the current search/filters.")
        for entry in user_strategies:
            _render_strategy_card(entry, context="mystrategies")

    with tree_tabs[2]:
        st.caption("Start a new strategy from a template.")
        for template_name in list_template_names():
            if st.button(template_name, key=f"template_{template_name}", use_container_width=True):
                st.session_state.sl_new_dialog_template = template_name
                st.session_state.sl_show_new_dialog = True
                _rerun_preserving_editor()

    with tree_tabs[3]:
        favorites = [e for e in visible_entries if e.is_favorite]
        if not favorites:
            st.caption("No favorites yet -- star a strategy to pin it here.")
        for entry in favorites:
            _render_strategy_card(entry, context="favorites")

    with tree_tabs[4]:
        st.caption("No archived strategies. Archiving is not implemented in this phase.")

    recent_paths = manager.list_recent()
    if recent_paths:
        st.divider()
        st.subheader("Recent")
        for recent_path in recent_paths:
            if st.button(recent_path.name, key=f"recent_{recent_path}", use_container_width=True):
                _open_strategy(recent_path)
                st.rerun()

# -----------------------------------------------------------------------
# No strategy open yet -- show guidance across the full width and stop,
# exactly like Phase 18 (`st.info` + `st.stop()`), just without a sidebar.
# -----------------------------------------------------------------------

if not st.session_state.sl_is_open:
    with center_col:
        st.info("Open a strategy from the Explorer, or click **New**, to get started.")
    render_status_bar(module="Strategy Library", strategy_status="—", validation_status="—", execution_status="Ready")
    st.stop()

current_path = _current_path()
is_new_draft = current_path is None
is_protected = current_path is not None and manager.is_protected(current_path)
locked_by_other = current_path is not None and not is_protected and manager.is_locked_by_other(current_path, SESSION_TOKEN)

if current_path is not None and not is_protected and not locked_by_other:
    manager.heartbeat_lock(current_path, SESSION_TOKEN)

if locked_by_other:
    with center_col:
        st.error("This strategy is already open.")
    render_status_bar(module="Strategy Library", strategy_status=current_path.name, validation_status="—", execution_status="Locked")
    st.stop()

# -----------------------------------------------------------------------
# CENTER PANEL -- primary workspace: sticky toolbar, large editor, tabs
# for Validation / Compile / Statistics / Suggestions / Version History /
# Audit Log. Every action below calls the exact same manager/SDL function
# Phase 18 already called -- only the layout moved.
# -----------------------------------------------------------------------

with center_col:
    header_cols = st.columns([5, 1])
    header_cols[0].subheader(current_path.name if current_path else "(new, unsaved strategy)")
    if is_protected:
        header_cols[1].markdown("🔒 **Built-in Example**")
    if _is_dirty():
        st.markdown("● **Unsaved Changes**")

    # --- Toolbar (single row) -----------------------------------------
    toolbar = st.columns(10)

    with toolbar[0].popover("Open"):
        st.caption("Open any strategy without leaving the editor.")
        for entry in manager.list_entries():
            if st.button(entry.name, key=f"toolbar_open_{entry.path}", use_container_width=True):
                _open_strategy(entry.path)
                st.rerun()

    if toolbar[1].button("Save", disabled=is_protected or is_new_draft):
        try:
            raw = parser.parse(st.session_state.sl_editor_textarea, st.session_state.sl_current_fmt)
            result = validator.validate(raw)
            if not result.is_valid:
                st.error("Cannot save: document is invalid. See the Validation tab.")
            else:
                saved = manager.save(result.definition, current_path.name, fmt=st.session_state.sl_current_fmt, overwrite=True)
                _after_save(saved)
                st.success(f"Saved '{saved.name}'.")
                st.rerun()
        except SDLParseError as exc:
            st.error(f"Cannot save: {exc}")

    with toolbar[2].popover("Save As"):
        with st.form("sl_save_as_form"):
            save_as_filename = st.text_input("New filename", value=(current_path.stem + "_new.yaml" if current_path else "new_strategy.yaml"))
            save_as_fmt = st.radio("Format", ["yaml", "json"], horizontal=True)
            if st.form_submit_button("Save As"):
                try:
                    raw = parser.parse(st.session_state.sl_editor_textarea, st.session_state.sl_current_fmt)
                    result = validator.validate(raw)
                    if not result.is_valid:
                        st.error("Cannot save: document is invalid. See the Validation tab.")
                    else:
                        saved = manager.save_as(result.definition, save_as_filename, fmt=save_as_fmt)
                        _after_save(saved)
                        st.success(f"Saved as '{saved.name}'.")
                        st.rerun()
                except (SDLParseError, DuplicateFilenameError) as exc:
                    st.error(str(exc))

    with toolbar[3].popover("Duplicate"):
        if current_path is None:
            st.caption("Save this strategy first to duplicate it.")
        else:
            duplicated_def, suggested_name, dup_fmt = manager.duplicate(current_path)
            with st.form("sl_duplicate_form"):
                dup_filename = st.text_input("Filename for the duplicate", value=suggested_name)
                if st.form_submit_button("Create Duplicate"):
                    try:
                        saved = manager.save(duplicated_def, dup_filename, fmt=dup_fmt, overwrite=False)
                    except DuplicateFilenameError as exc:
                        st.error(str(exc))
                    else:
                        _open_strategy(saved)
                        st.success(f"Duplicated to '{saved.name}'.")
                        st.rerun()

    with toolbar[4].popover("Rename"):
        if is_protected or current_path is None:
            st.caption("Built-in examples cannot be renamed. Use Save As." if is_protected else "Save this strategy first.")
        else:
            with st.form("sl_rename_form"):
                rename_filename = st.text_input("New filename", value=current_path.name)
                rename_name = st.text_input("New display name (optional)")
                if st.form_submit_button("Rename"):
                    try:
                        renamed = manager.rename(current_path, rename_filename, new_name=rename_name or None)
                    except (DuplicateFilenameError, ProtectedStrategyError) as exc:
                        st.error(str(exc))
                    else:
                        _open_strategy(renamed, record_history=False)
                        st.success(f"Renamed to '{renamed.name}'.")
                        st.rerun()

    with toolbar[5]:
        if is_protected:
            st.button("Delete", disabled=True, help="This strategy is protected.")
        elif current_path is None:
            st.button("Delete", disabled=True, help="Save this strategy first.")
        elif not st.session_state.sl_delete_armed:
            if st.button("Delete"):
                st.session_state.sl_delete_armed = True
                _rerun_preserving_editor()
        else:
            if st.button("⚠ Confirm", type="primary"):
                manager.delete(current_path)
                _close_strategy()
                st.success("Deleted.")
                st.rerun()

    with toolbar[6].popover("Export"):
        export_fmt = st.radio("Format", ["yaml", "json"], horizontal=True, key="sl_export_fmt")
        try:
            if current_path is not None and not _is_dirty():
                export_text = manager.export_text(current_path, export_fmt)
            else:
                raw = parser.parse(st.session_state.sl_editor_textarea, st.session_state.sl_current_fmt)
                result = validator.validate(raw)
                if not result.is_valid:
                    export_text = None
                elif export_fmt == "yaml":
                    export_text = serializer.to_yaml(result.definition)
                else:
                    export_text = serializer.to_json(result.definition)
        except SDLParseError:
            export_text = None
        if export_text is None:
            st.caption("Fix validation errors to export.")
        else:
            st.download_button(
                "Download",
                data=export_text,
                file_name=(current_path.stem if current_path else "strategy") + ("." + export_fmt if export_fmt == "json" else ".yaml"),
                mime="application/json" if export_fmt == "json" else "text/yaml",
            )

    validate_clicked = toolbar[7].button("Validate")
    compile_clicked = toolbar[8].button("Compile")

    favorite_disabled = current_path is None
    current_is_favorite = current_path is not None and manager.is_favorite(current_path)
    if toolbar[9].button("⭐" if current_is_favorite else "☆", disabled=favorite_disabled, help="Toggle favorite"):
        manager.toggle_favorite(current_path)
        _rerun_preserving_editor()

    # --- Parse + validate the CURRENT editor buffer (live, not just on-disk) ---

    parse_error: str | None = None
    live_result = None
    try:
        live_raw = parser.parse(st.session_state.sl_editor_textarea, st.session_state.sl_current_fmt)
        live_result = validator.validate(live_raw)
    except SDLParseError as exc:
        parse_error = str(exc)

    if validate_clicked and current_path is not None:
        manager.record_validated(current_path)

    compile_message: tuple[str, str] | None = None  # (level, message) for "Compile" tab + toast
    if compile_clicked:
        if live_result is None or not live_result.is_valid:
            if current_path is not None:
                manager.record_compile_result(current_path, success=False, duration_seconds=0.0, error_message=parse_error or "Validation failed.")
            compile_message = ("error", "Cannot compile: document is invalid.")
        else:
            t0 = time.perf_counter()
            try:
                compiled = compiler.compile(live_result.definition)
                duration = time.perf_counter() - t0
                if current_path is not None:
                    manager.record_compile_result(current_path, success=True, duration_seconds=duration)
                compile_message = ("success", f"Compiled successfully in {duration * 1000:.1f} ms. Checksum: {compiled.checksum[:16]}...")
            except Exception as exc:  # noqa: BLE001 -- surfaced to the user, and recorded either way
                duration = time.perf_counter() - t0
                if current_path is not None:
                    manager.record_compile_result(current_path, success=False, duration_seconds=duration, error_message=str(exc))
                compile_message = ("error", f"Compilation failed: {exc}")
        if compile_message[0] == "success":
            st.success(compile_message[1])
        else:
            st.error(compile_message[1])

    # --- Large editor + tabs --------------------------------------------

    tab_names = ["Editor", "Validation", "Compile", "Statistics", "Suggestions", "Version History", "Audit Log"]
    editor_tab, validation_tab, compile_tab, statistics_tab, suggestions_tab, history_tab, audit_tab = st.tabs(tab_names)

    with editor_tab:
        st.text_area("SDL document", key="sl_editor_textarea", height=560, label_visibility="collapsed")

    with validation_tab:
        if parse_error is not None:
            st.error(f"Parse error: {parse_error}")
        elif live_result is not None:
            if live_result.errors:
                st.markdown("**Errors**")
                for issue in live_result.errors:
                    if st.button(f"🔴 {issue.path} — {issue.message}", key=f"err_{issue.path}_{issue.message}"):
                        st.session_state.sl_jump_section = issue.path.split(".")[0]
            if live_result.warnings:
                st.markdown("**Warnings**")
                for issue in live_result.warnings:
                    if st.button(f"🟡 {issue.path} — {issue.message}", key=f"warn_{issue.path}_{issue.message}"):
                        st.session_state.sl_jump_section = issue.path.split(".")[0]
            if not live_result.errors and not live_result.warnings:
                st.success("No errors or warnings.")
            if st.session_state.sl_jump_section:
                st.info(f"📍 Jumped to section: `{st.session_state.sl_jump_section}` -- find it in the Editor tab.")

    with compile_tab:
        status = manager.get_compile_status(current_path) if current_path is not None else None
        if compile_message is not None:
            (st.success if compile_message[0] == "success" else st.error)(compile_message[1])
        if status is None:
            st.caption("✓ Never Compiled")
        elif status.success:
            st.success(f"✓ Compile Success -- {status.compiled_at.isoformat(timespec='seconds')} ({status.duration_seconds * 1000:.1f} ms)")
        else:
            st.error(f"❌ Compile Failed -- {status.compiled_at.isoformat(timespec='seconds')} ({status.duration_seconds * 1000:.1f} ms): {status.error_message}")
        st.caption("Use the Compile button in the toolbar to (re)compile the current editor content.")

    with statistics_tab:
        if live_result is not None and live_result.definition is not None:
            if current_path is not None and not _is_dirty():
                stats = manager.compute_statistics(current_path)
            else:
                from app.strategy_library.statistics import compute_statistics as _compute_stats

                stats = _compute_stats(live_result.definition, st.session_state.sl_editor_textarea)
            stat_cols = st.columns(3)
            stat_cols[0].metric("Lines of SDL", stats.lines_of_sdl)
            stat_cols[0].metric("Indicators", stats.indicator_count)
            stat_cols[1].metric("Conditions", stats.condition_count)
            stat_cols[1].metric("Filters", stats.filter_count)
            stat_cols[2].metric("Risk Rules", stats.risk_rule_count)
            stat_cols[2].metric("Metadata Completeness", f"{stats.metadata_completeness_pct}%")
        else:
            st.caption("Fix parse/validation errors to compute statistics.")

    with suggestions_tab:
        if live_result is not None and live_result.definition is not None:
            from app.strategy_library.suggestions import compute_suggestions as _compute_suggestions

            suggestions = _compute_suggestions(live_result.definition)
            if suggestions:
                for suggestion in suggestions:
                    if st.button(f"💡 {suggestion.path} — {suggestion.message}", key=f"sugg_{suggestion.path}"):
                        st.session_state.sl_jump_section = suggestion.path.split(".")[0]
            else:
                st.success("No suggestions -- this strategy's metadata looks complete.")
        else:
            st.caption("Fix parse/validation errors to compute suggestions.")

    with history_tab:
        if current_path is None:
            st.caption("Save this strategy first to start version history.")
        else:
            versions = manager.list_versions(current_path)
            if not versions:
                st.caption("No versions recorded yet.")
            for version in reversed(versions):
                vcols = st.columns([3, 1])
                vcols[0].write(f"v{version.version_id} -- {version.note} -- {version.saved_at.isoformat(timespec='seconds')}")
                if not is_protected and vcols[1].button("Restore", key=f"restore_v{version.version_id}"):
                    manager.restore_version(current_path, version.version_id)
                    _open_strategy(current_path, record_history=False)
                    st.rerun()

    with audit_tab:
        if current_path is None:
            st.caption("Save this strategy first to start its audit trail.")
        else:
            events = manager.list_audit_events(current_path, limit=50)
            if not events:
                st.caption("No audit events recorded yet.")
            for event in events:
                st.caption(f"{event.timestamp.isoformat(timespec='seconds')} -- {event.event_type.value}")

# -----------------------------------------------------------------------
# RIGHT PANEL -- Strategy Information, as bordered cards. Same
# `live_result`/`manager.get_entry`/`manager.get_compile_status`/
# `compute_statistics` data Phase 18 already computed -- only its layout
# (single scrolling column -> titled cards) changed.
# -----------------------------------------------------------------------

with right_col:
    st.subheader("Strategy Information")

    if parse_error is not None:
        st.error(f"Parse error: {parse_error}")
    elif live_result is not None and live_result.definition is not None:
        definition = live_result.definition
        md = definition.metadata

        with st.container(border=True):
            st.markdown("**General Information**")
            st.write(f"Name: **{md.name}**")
            st.write(f"ID: `{md.id}`")
            st.write(f"Version: {md.strategy_version}  ·  SDL {md.sdl_version}")
            st.write(f"Author: {md.author or '—'}")
            st.write(f"Description: {md.description or '—'}")

        with st.container(border=True):
            st.markdown("**Market**")
            st.write(f"Asset Class: {definition.market.asset_class}")
            st.write(f"Market Type: {definition.market.market_type or '—'}")
            st.write(f"Symbols: {', '.join(definition.symbols)}")
            st.write(f"Timeframes: {', '.join(definition.timeframes)}")
            st.write(f"Primary Timeframe: {definition.primary_timeframe or '—'}")

        with st.container(border=True):
            st.markdown("**Compile Status**")
            status = manager.get_compile_status(current_path) if current_path is not None else None
            if status is None:
                st.caption("✓ Never Compiled")
            elif status.success:
                st.success(f"✓ Success ({status.duration_seconds * 1000:.1f} ms)")
            else:
                st.error("❌ Failed")

        with st.container(border=True):
            st.markdown("**Validation Status**")
            if live_result.is_valid and not live_result.warnings:
                st.success("✅ Valid")
            elif live_result.is_valid:
                st.warning("⚠️ Valid with warnings")
            else:
                st.error("❌ Invalid")

        with st.container(border=True):
            st.markdown("**Statistics**")
            if current_path is not None and not _is_dirty():
                stats = manager.compute_statistics(current_path)
            else:
                from app.strategy_library.statistics import compute_statistics as _compute_stats

                stats = _compute_stats(definition, st.session_state.sl_editor_textarea)
            st.write(f"Metadata Completeness: {stats.metadata_completeness_pct}%")
            st.write(f"Indicator count: {stats.indicator_count}")
            st.write(f"Rule count: {stats.condition_count}")
            st.write(f"Filter count: {stats.filter_count}")
            st.write(f"Risk rules: {stats.risk_rule_count}")
            if current_path is not None and current_path.exists():
                st.write(f"Last Modified: {manager.get_entry(current_path).modified_at.isoformat(timespec='seconds')}")

        with st.container(border=True):
            st.markdown("**Flags**")
            st.write(f"Favorites: {'⭐ Yes' if (current_path is not None and manager.is_favorite(current_path)) else '☆ No'}")
            st.write(f"Protected: {'🔒 Yes (built-in example)' if is_protected else 'No'}")
    else:
        st.caption("Nothing to show yet.")


# ---------------------------------------------------------------------
# Autosave (rule 26) -- every ~30s, or immediately after this rerun if
# the editor content changed since the last autosave. Streamlit has no
# persistent background timer; `st.fragment(run_every=...)` is the
# closest offline, dependency-free equivalent for a synchronous,
# rerun-per-interaction app. Unchanged from Phase 18.
# ---------------------------------------------------------------------


@st.fragment(run_every=30)
def _autosave_fragment() -> None:
    if not st.session_state.sl_is_open:
        return
    current_text = st.session_state.sl_editor_textarea
    if current_text == st.session_state.sl_last_autosave_signature:
        return  # never overwrite the original automatically -- only autosave real, new edits
    manager.autosave(st.session_state.sl_current_path, SESSION_TOKEN, st.session_state.sl_current_fmt, current_text)
    st.session_state.sl_last_autosave_signature = current_text


_autosave_fragment()

# ---------------------------------------------------------------------
# Global status bar (Phase 18.2/18.3) -- additive only, reads the exact
# same manager/session-state values already computed above.
# ---------------------------------------------------------------------

render_status_bar(
    module="Strategy Library",
    strategy_status=(current_path.name if current_path else "(new, unsaved strategy)") if st.session_state.sl_is_open else "—",
    validation_status=(
        ("✅ Valid" if live_result.is_valid and not live_result.warnings else "⚠️ Valid with warnings" if live_result.is_valid else "❌ Invalid")
        if st.session_state.sl_is_open and live_result is not None
        else "—"
    ),
    execution_status="Editing" if st.session_state.sl_is_open and _is_dirty() else "Ready",
)
