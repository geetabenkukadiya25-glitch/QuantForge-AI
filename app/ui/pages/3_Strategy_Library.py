"""
Streamlit page: Strategy Library.

Open a strategy (from the bundled examples, the saved registry, or an
uploaded file), validate it, compile it, and inspect its SDL document and
validation report. Phase 4 scope only -- no indicators, strategy
execution, backtesting, optimization, or AI.
"""

import json
import tempfile
from pathlib import Path

import streamlit as st

from app.sdl import (
    SDLCompileError,
    SDLParseError,
    SDLValidationError,
    SchemaManager,
    StrategyCompiler,
    StrategyParser,
    StrategyRegistry,
    StrategySerializer,
    StrategyValidator,
)

st.set_page_config(page_title="Strategy Library - QuantForge AI", page_icon="📜", layout="wide")

st.title("Strategy Library")
st.caption("Open, validate, and compile Strategy Definition Language (SDL) documents.")

parser = StrategyParser()
validator = StrategyValidator()
serializer = StrategySerializer()
compiler = StrategyCompiler()
registry = StrategyRegistry()
schema_manager = SchemaManager()

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "sdl" / "examples"


def _load_examples() -> dict[str, Path]:
    return {path.stem: path for path in sorted(EXAMPLES_DIR.glob("*.yaml"))}


st.sidebar.header("Open Strategy")
source = st.sidebar.radio("Source", ["Bundled examples", "Saved registry", "Upload file"])

raw_data: dict | None = None
source_label = ""

if source == "Bundled examples":
    examples = _load_examples()
    if not examples:
        st.sidebar.warning("No bundled examples found.")
    else:
        choice = st.sidebar.selectbox("Example", list(examples.keys()))
        try:
            raw_data = parser.parse_file(examples[choice])
            source_label = f"example: {choice}"
        except SDLParseError as exc:
            st.sidebar.error(f"Could not parse example: {exc}")

elif source == "Saved registry":
    summaries = registry.list()
    if not summaries:
        st.sidebar.info("No strategies saved in the registry yet.")
    else:
        options = {f"{s.name} ({s.id})": s.id for s in summaries}
        choice = st.sidebar.selectbox("Strategy", list(options.keys()))
        try:
            definition = registry.load(options[choice])
            raw_data = serializer.to_dict(definition)
            source_label = f"registry: {options[choice]}"
        except SDLValidationError as exc:
            st.sidebar.error(f"Stored strategy is invalid: {exc}")

else:
    uploaded_file = st.sidebar.file_uploader("Strategy file", type=["yaml", "yml", "json"])
    if uploaded_file is not None:
        suffix = Path(uploaded_file.name).suffix
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = Path(tmp.name)
        try:
            raw_data = parser.parse_file(tmp_path)
            source_label = f"upload: {uploaded_file.name}"
        except SDLParseError as exc:
            st.sidebar.error(f"Could not parse file: {exc}")
        finally:
            tmp_path.unlink(missing_ok=True)

if raw_data is None:
    st.info("Open a strategy from the sidebar to get started.")
    with st.expander("Schema reference"):
        st.write("Top-level SDL sections:")
        st.code("\n".join(schema_manager.get_sections()))
        st.write("Required sections:", schema_manager.get_required_sections())
    st.stop()

st.subheader(f"Strategy: {source_label}")

result = validator.validate(raw_data)

col_sdl, col_report = st.columns(2)

with col_sdl:
    st.markdown("### Show SDL")
    fmt = st.radio("Format", ["YAML", "JSON"], horizontal=True, key="sdl_format")
    if result.definition is not None:
        text = (
            serializer.to_yaml(result.definition)
            if fmt == "YAML"
            else serializer.to_json(result.definition)
        )
    else:
        text = json.dumps(raw_data, indent=2, default=str)
    st.code(text, language="yaml" if fmt == "YAML" else "json")

with col_report:
    st.markdown("### Validation Report")
    if result.is_valid:
        st.success(f"Valid ({len(result.warnings)} warning(s))")
    else:
        st.error(f"Invalid ({len(result.errors)} error(s))")

    for issue in result.errors:
        st.markdown(f"- 🔴 **{issue.path}** — {issue.message}")
    for issue in result.warnings:
        st.markdown(f"- 🟡 **{issue.path}** — {issue.message}")

    st.markdown("### Compile")
    if st.button("Compile strategy", disabled=not result.is_valid):
        try:
            compiled = compiler.compile(result.definition)
        except (SDLValidationError, SDLCompileError) as exc:
            st.error(f"Compilation failed: {exc}")
        else:
            st.success("Compiled successfully.")
            st.write("Execution order:", compiled.execution_order or "(no ordered steps)")
            st.write("Checksum:", compiled.checksum)
            st.write("SDL version:", compiled.sdl_version)
            st.write("Compiled at:", compiled.compiled_at.isoformat())
