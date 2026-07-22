"""Best-effort browser keyboard shortcuts for a Streamlit page (Phase 18
rule 25).

Streamlit has no native key-binding API. This injects a small, inert
`<script>` (via `st.iframe`, given a raw HTML string) that listens for
`keydown` on the page and, on a match, finds and clicks the Streamlit
button whose visible label equals the mapped action -- i.e. it never
bypasses Streamlit's own event handling, it only simulates the same
click a user would make. Two honest limitations:

- Some combinations (`Ctrl+N`, `Ctrl+S`) are intercepted by the browser
  itself (new window / save page) in some browsers/embedding contexts
  before this script ever sees the keydown event -- there is no way for
  page JavaScript to override that.
- The label match is exact and case-sensitive, so a toolbar button's
  visible text must match the `label` passed here exactly.
"""

import streamlit as st

#: Shortcut spec: (key, ctrl, shift) -> visible button label to click.
DEFAULT_SHORTCUTS: dict[tuple[str, bool, bool], str] = {
    ("n", True, False): "New",
    ("s", True, False): "Save",
    ("s", True, True): "Save As",
    ("d", True, False): "Duplicate",
    ("f", True, False): "Search",
    ("r", True, False): "Rename",
    ("delete", True, False): "Delete",
    ("enter", True, False): "Compile",
}


def render_keyboard_shortcuts(shortcuts: dict[tuple[str, bool, bool], str] | None = None) -> None:
    """Render the (invisible) shortcut listener. Call once per page."""
    mapping = shortcuts or DEFAULT_SHORTCUTS
    entries = ",".join(
        f'{{key:{key!r},ctrl:{str(ctrl).lower()},shift:{str(shift).lower()},label:{label!r}}}'
        for (key, ctrl, shift), label in mapping.items()
    )
    st.iframe(
        f"""
        <script>
        const shortcuts = [{entries}];
        function clickButtonByLabel(label) {{
            const doc = window.parent.document;
            const buttons = doc.querySelectorAll('button');
            for (const btn of buttons) {{
                if (btn.innerText.trim() === label) {{
                    btn.click();
                    return true;
                }}
            }}
            return false;
        }}
        window.parent.document.addEventListener('keydown', function(e) {{
            for (const s of shortcuts) {{
                if (e.key.toLowerCase() === s.key && e.ctrlKey === s.ctrl && e.shiftKey === s.shift) {{
                    if (clickButtonByLabel(s.label)) {{
                        e.preventDefault();
                    }}
                    return;
                }}
            }}
        }});
        </script>
        """,
        height=1,
        width=1,
    )
