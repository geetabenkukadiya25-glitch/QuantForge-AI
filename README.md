# QuantForge AI

Institutional-grade AI Strategy Research Platform.

> Governed by [`PROJECT_VISION.md`](PROJECT_VISION.md) — the project's
> constitution. Read it before starting any development task.

QuantForge AI is not just a backtester — it's a complete strategy research
laboratory covering the full pipeline from idea to deployable Expert
Advisor:

```
Idea → AI Strategy Builder → Historical Data → Auto Backtest →
Optimization → Analytics → Walk Forward → Monte Carlo →
Risk Analysis → MT5 EA Generator
```

> **Status: Phase 1-16 complete** (plus a Phase 14 Knowledge Base
> submodule and a Portfolio Management Engine, both added ahead of order
> by approval).
> Phase 1 established the project architecture. Phase 2 added a
> historical OHLCV data engine. Phase 3 added a professional chart
> engine. Phase 4 added the Strategy Definition Language. Phase 5 added
> the Market Context Engine. Phase 6 added the Indicator Engine. Phase 7
> added the Smart Money Engine. Phase 8 added the Strategy Builder,
> combining SDL, Market Context, Indicator, and Smart Money Engine
> outputs into a reusable, executable `StrategyModel`. Phase 9 added the
> Backtesting Engine — deterministic, candle-by-candle historical replay
> of a compiled `StrategyModel`. Phase 10 added the Optimization Engine —
> Grid Search and Random Search over `StrategyModel` parameters using the
> existing, unmodified Backtesting Engine. Phase 11 added the Walk
> Forward & Monte Carlo Validation Engine (`app/validation_engine/`) —
> validates an already-chosen Optimization Engine candidate via
> walk-forward windowing and Monte Carlo resampling. Phase 12 added the
> Professional Replay Engine (`app/replay_engine/`) — candle-by-candle
> playback of historical data (Timeline, Cursor, Player, Controller) that
> MAY overlay an already-built strategy's indicators/detections and an
> already-run backtest's trade lifecycle, purely for visualization.
> Ahead of Phase 13, the Research & Strategy Intelligence Engine
> (`app/research_engine/`) and a Knowledge Base Platform
> (`app/knowledge_base/`) were added additively as submodules of the
> already-approved Phase 14 — per explicit user approval,
> `PROJECT_VISION.md`'s roadmap numbering was left unchanged. Phase 13
> adds the AI Strategy Extraction Engine (`app/ai_extraction/`) —
> converts already-obtained external strategy document text (YouTube
> transcript, PDF, Markdown, plain text, Pine Script, MQL4/5,
> EasyLanguage, pseudocode, OCR text) into a draft SDL document, a
> confidence report, and a missing-information report. It is a
> deterministic, offline, pattern/keyword-matching pipeline — NOT a
> generative AI model, and it NEVER calls an external API. It MUST NOT
> generate trading ideas; every output is an explicit DRAFT requiring
> human review before use, per `PROJECT_VISION.md`'s "AI assists, humans
> approve" principle. After Phase 13/14, the Professional Portfolio
> Management Engine (`app/portfolio_engine/`) was added as another
> approved-but-unplanned additive module (the same non-renumbering rule
> as the Research Engine before it — `PROJECT_VISION.md`'s locked roadmap
> still lists Phase 15 as "AI Research Assistant," unchanged) — it
> combines multiple already-completed strategies into a single portfolio:
> allocation (Equal Weight, Risk Parity, Volatility Weight, Sharpe
> Weight, Manual Weight), correlation, exposure, ranking, and portfolio-
> quality analytics. It NEVER trades, NEVER connects to a broker or MT5,
> NEVER optimizes, and NEVER validates — only aggregation over
> already-completed Strategy Builder/Backtesting (and optionally
> Optimization/Validation/Replay/Research) outputs. Phase 15 — the
> official Phase 15 of `PROJECT_VISION.md`'s Approved Roadmap — adds the
> AI Research Assistant (`app/ai_assistant/`): a deterministic, offline
> assistant that searches and explains data already present inside
> QuantForge AI. It is NOT an LLM, NEVER connects to any external AI API
> or service, and NEVER requires internet access — no embeddings, no
> vector database. It is strictly read-only: it NEVER trades, optimizes,
> validates, replays, or rebuilds a strategy. Phase 16 — the official
> Phase 16 of `PROJECT_VISION.md`'s Approved Roadmap — adds the EA
> Generator (`app/ea_generator/`): an OFFLINE CODE GENERATOR that
> produces production-quality-skeleton MetaTrader 5 (MQL5) Expert
> Advisor source code from an already-built `StrategyModel`. It does
> NOT compile MT5, does NOT execute trades, does NOT connect to a
> broker, does NOT call MetaTrader, does NOT run a Python bridge, and
> does NOT call any external API — it only generates source code. Phase
> 17 — the official Phase 17 of `PROJECT_VISION.md`'s Approved Roadmap —
> adds the Cloud Platform Foundation (`app/cloud_platform/`): the
> architectural foundation ONLY for a future cloud-hosted deployment.
> This phase is completely OFFLINE — no authentication, no cloud
> synchronization, no networking, no APIs, no background workers, no
> databases, no websocket communication, no remote execution, and no
> external service calls. It is a management layer that stores
> references (ids, names, checksums) to artifacts produced by other
> engines, and never inspects their internals. Phase 17.1 builds Cloud
> Workspace Management directly on top of that foundation (still inside
> `app/cloud_platform/`, no new engine): local, offline research
> workspace/project lifecycle management (create, open, close, rename,
> archive, restore, soft-delete, favorite, tags, notes, snapshot) with a
> deterministic, checksummed history. Still 100% offline — no
> authentication, no users, no cloud sync, no networking, no APIs, no
> background workers, no database, no file upload, no remote execution.
> Phase 17.2 adds the Local Artifact Registry (still inside
> `app/cloud_platform/`, no new engine): a deterministic registry
> managing ONLY metadata and references for every research artifact
> QuantForge AI produces (datasets, strategies, SDL, compiled
> strategies, every engine's results, snapshots, reports, and more),
> including dependency tracking with cycle detection. It is NOT cloud
> storage and NOT a filesystem indexer — it never inspects an
> artifact's actual content. Still 100% offline — no authentication, no
> users, no organizations, no permissions, no networking, no APIs, no
> database, no broker/MetaTrader/execution-engine code. Phase 17.3 adds
> a Project Versioning & Snapshot System (still inside
> `app/cloud_platform/`, no new engine) — an internal, deterministic
> version-history layer (NOT Git, NOT source-code versioning) for
> workspaces, artifacts, and 13 other object types: branching version
> trees, checksum-based comparison, and restore-by-new-version (never
> by mutating history). Still 100% offline — no authentication, no
> users, no networking, no database, no workers, no broker/MetaTrader/
> execution-engine code. See [docs/ROADMAP.md](docs/ROADMAP.md).

## Future Institutional Roadmap

Ideas for future, unapproved versions beyond the current roadmap —
research governance, data governance, artifact management, workflow
automation, risk infrastructure, institutional features, and a future
cloud version — are tracked separately in
[PROJECT_IDEAS.md](PROJECT_IDEAS.md). None of it is implemented,
scheduled, or approved; the current project remains offline,
deterministic, and research-only through Version 1.0.

## Tech stack

Python 3.12+, FastAPI, Streamlit, Pandas, NumPy, Plotly, VectorBT,
Backtesting.py, TA, MetaTrader5, SQLite.

## Project structure

```
QuantForge AI/
├── app/
│   ├── core/            # Base engine/strategy interfaces, feature flags, event bus
│   ├── config/           # Settings (env-driven) and resolved paths
│   ├── data_engine/       # Historical data: import, validate, clean, export
│   ├── chart_engine/       # Candlestick/OHLC charts, drawing tools, sessions
│   ├── sdl/                 # Strategy Definition Language (parse/validate/compile/registry)
│   │   ├── examples/
│   │   └── library/
│   ├── context_engine/     # Market Context Engine (standardized market state)
│   │   └── snapshots/
│   ├── indicator_engine/    # 24 technical indicators (calculation only)
│   │   └── indicators/        # one module per indicator, grouped by category
│   ├── smart_money_engine/   # 32 Smart Money Concepts detectors (detection only)
│   │   └── detectors/          # one module per detector, grouped by category
│   ├── strategy_builder/      # Combines SDL + Context + Indicator + SMC into StrategyModel
│   ├── backtesting_engine/     # Deterministic historical replay of a StrategyModel
│   │   └── results/
│   ├── optimization_engine/     # Grid/Random Search over StrategyModel parameters
│   │   └── results/
│   ├── validation_engine/        # Walk Forward + Monte Carlo validation of a chosen candidate
│   │   └── results/
│   ├── replay_engine/             # Candle-by-candle historical replay (visualization only)
│   │   └── results/
│   ├── research_engine/            # Cross-strategy comparison, ranking, insights (Phase 14 submodule)
│   │   └── results/
│   ├── knowledge_base/              # Trading-knowledge documentation platform (Phase 14 submodule)
│   │   └── entries/
│   ├── ai_extraction/                # Converts external strategy documents into draft SDL (Phase 13)
│   │   └── results/
│   ├── portfolio_engine/              # Multi-strategy portfolio allocation, correlation, ranking, analytics
│   │   └── results/
│   ├── ai_assistant/                   # Deterministic, offline search/explanations (Phase 15)
│   │   └── results/
│   ├── ea_generator/                    # Offline MQL5 EA source-code generator (Phase 16)
│   │   └── results/
│   ├── cloud_platform/                   # Cloud Platform Foundation -- offline, in-memory (Phase 17)
│   ├── data/              # (future phase) live/multi-provider data sourcing
│   │   ├── historical/
│   │   └── downloads/
│   ├── strategies/        # (future phase) AI-driven BaseStrategy building
│   │   └── generated/
│   ├── backtests/          # Backtest, walk-forward, Monte Carlo engines
│   ├── optimization/        # Parameter optimization engine
│   ├── analytics/            # Analytics engine and report generator
│   │   ├── reports/
│   │   └── charts/
│   ├── ai/                    # (future phase) AI indicator suggestions, YouTube strategy import
│   │   └── youtube/
│   ├── mt5/                    # MT5 connector and EA generator
│   │   └── ea_generator/
│   ├── database/                 # SQLite connection + schema
│   ├── utils/                     # Logging
│   ├── api/                        # FastAPI application
│   └── ui/                          # Streamlit dashboard
│       └── pages/                    # Streamlit multipage app pages
├── tests/
│   ├── data_engine/                  # Historical data engine unit tests
│   ├── chart_engine/                  # Chart engine unit tests
│   ├── sdl/                            # SDL unit tests
│   ├── context_engine/                  # Market Context Engine unit tests
│   ├── indicator_engine/                 # Indicator Engine unit tests
│   ├── smart_money_engine/                # Smart Money Engine unit tests
│   ├── strategy_builder/                   # Strategy Builder unit tests
│   ├── backtesting_engine/                  # Backtesting Engine unit tests
│   ├── optimization_engine/                  # Optimization Engine unit tests
│   ├── validation_engine/                     # Walk Forward & Monte Carlo Validation Engine unit tests
│   ├── replay_engine/                          # Replay Engine unit tests
│   ├── research_engine/                         # Research & Strategy Intelligence Engine unit tests
│   ├── knowledge_base/                           # Knowledge Base Platform unit tests
│   ├── ai_extraction/                             # AI Strategy Extraction Engine unit tests
│   ├── portfolio_engine/                           # Portfolio Management Engine unit tests
│   ├── ai_assistant/                                # AI Research Assistant unit tests
│   ├── ea_generator/                                 # EA Generator Engine unit tests
│   └── cloud_platform/                                # Cloud Platform Foundation unit tests
├── docs/
│   └── sdl/                            # SDL specification, schema reference, examples, dev guide
├── main.py
├── requirements.txt
├── PROJECT_VISION.md
└── .env.example
```

## Getting started

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # optional, defaults work out of the box
```

### Run

```bash
python main.py init-db   # initialize the SQLite database
python main.py api       # FastAPI server (http://localhost:8000/health)
python main.py ui        # Streamlit dashboard (http://localhost:8501)
```

### Test

```bash
pytest
```

## Historical Data Engine

```python
from app.data_engine import DataLoader, DataExporter, generate_quality_report

loader = DataLoader()
df = loader.load_csv("EURUSD_H1.csv")   # standard CSV or MT5 export format
print(loader.statistics(df))
print(generate_quality_report(df).to_dict())

DataExporter().to_parquet(df, "EURUSD_H1.parquet")
```

Or via the Streamlit dashboard: `python main.py ui`, then open the
**Historical Data** page to browse, preview, and generate a data quality
report for a CSV file.

## Chart Engine

```python
from app.chart_engine import ChartEngine, ChartConfig, DrawingManager, HorizontalLine

engine = ChartEngine()
fig = engine.render(
    df,  # any DataFrame with Datetime, Open, High, Low, Close (+ Volume)
    config=ChartConfig(theme="dark", show_volume=True),
    chart_type="candlestick",
    show_sessions=True,
)

drawings = DrawingManager()
drawings.add(HorizontalLine(price=1.1050, label="Resistance"))
fig = engine.render(df, drawings=drawings)

from app.chart_engine import ExportManager
ExportManager().to_html(fig, "chart.html")
```

Or via the Streamlit dashboard: `python main.py ui`, then open the
**Chart Engine** page for interactive candlestick/OHLC charts with
timeframe/theme selectors, drawing tools, and export.

## Strategy Definition Language (SDL)

A strategy is a machine-readable document — not Python, not MQL5. Every
future engine must consume the same SDL.

```python
from app.sdl import StrategyParser, StrategyValidator, StrategyCompiler, StrategyRegistry

data = StrategyParser().parse_file("app/sdl/examples/moving_average_cross.yaml")
result = StrategyValidator().validate(data)
print(result.report())

if result.is_valid:
    compiled = StrategyCompiler().compile(result.definition)
    print(compiled.execution_order, compiled.checksum)

    StrategyRegistry().save(result.definition)
```

Or via the Streamlit dashboard: `python main.py ui`, then open the
**Strategy Library** page to open, validate, and compile a strategy and
inspect its SDL document and validation report.

See [docs/sdl/SPECIFICATION.md](docs/sdl/SPECIFICATION.md),
[docs/sdl/SCHEMA_REFERENCE.md](docs/sdl/SCHEMA_REFERENCE.md),
[docs/sdl/EXAMPLES.md](docs/sdl/EXAMPLES.md), and
[docs/sdl/DEVELOPER_GUIDE.md](docs/sdl/DEVELOPER_GUIDE.md).

## Market Context Engine

No decision engine may consume raw market data directly — every one
consumes a standardized `ContextSnapshot` instead. This engine never
generates trading signals.

```python
from datetime import datetime, timezone
from app.context_engine import MarketContextEngine

engine = MarketContextEngine()
snapshot = engine.build_context(
    symbol="EURUSD",
    timeframe="H1",
    current_datetime=datetime(2024, 1, 3, 8, 30, tzinfo=timezone.utc),
    candle_index=42,
    symbol_spec={
        "digits": 5, "point": 0.00001, "tick_size": 0.00001,
        "tick_value": 1.0, "spread": 1.2, "contract_size": 100000, "currency": "USD",
    },
)
print(snapshot.market.session)   # active trading session, progress, open/close
print(snapshot.time)             # calendar decomposition (day/week/month/quarter/year)

engine.save(snapshot)            # filesystem-backed registry
```

Or via the Streamlit dashboard: `python main.py ui`, then open the
**Context Viewer** page to build a snapshot, inspect its validation
report, view feature flags, and browse saved snapshots.

### Feature flags & events (`app/core/`)

```python
from app.core import FeatureFlagManager, FeatureFlag, FeatureStage, EventBus

flags = FeatureFlagManager()
flags.register(FeatureFlag(name="my_experimental_view", stage=FeatureStage.EXPERIMENTAL))
flags.is_enabled("my_experimental_view")   # False by default, always False in production

bus = EventBus()
bus.subscribe("my.event", lambda event: print(event.payload))
bus.publish("my.event", {"hello": "world"})
```

## Indicator Engine

24 indicators as pure calculation components — this engine never
generates trading signals.

```python
from app.indicator_engine import IndicatorEngine, IndicatorContext

engine = IndicatorEngine()
context = IndicatorContext(data=df, symbol="EURUSD", timeframe="H1")  # standard OHLCV DataFrame

result = engine.compute("RSI", context, window=14)
print(result.values["RSI"][-1])   # most recent RSI value

for meta in engine.search(category="Volatility"):
    print(meta.name, meta.parameters)

engine.disable("Parabolic SAR")   # feature-flag-backed; compute() now raises IndicatorDisabledError
```

Or via the Streamlit dashboard: `python main.py ui`, then open the
**Indicator Explorer** page to browse indicator metadata/parameters,
toggle indicators on/off, and preview a calculation over an uploaded CSV.

## Smart Money Engine

32 Smart Money Concepts detectors as pure detection/description
components — this engine never generates trading signals.

```python
from app.smart_money_engine import SmartMoneyEngine, SMCContext

engine = SmartMoneyEngine()
context = SMCContext(data=df, symbol="EURUSD", timeframe="H1")  # standard OHLCV DataFrame

result = engine.detect("Fair Value Gap", context)
for d in result.detections[:3]:
    print(d.label, d.direction, d.top, d.bottom)

for meta in engine.search(category="Liquidity"):
    print(meta.name, meta.parameters)

engine.disable("Order Block")   # feature-flag-backed; detect() now raises SMCDetectorDisabledError
```

Detectors can optionally use precomputed Indicator Engine / Market
Context Engine outputs:

```python
from app.indicator_engine import IndicatorContext, IndicatorEngine

atr = IndicatorEngine().compute("ATR", IndicatorContext(data=df))
context = SMCContext(data=df, indicators={"ATR": atr})   # DisplacementDetector will use it
```

Or via the Streamlit dashboard: `python main.py ui`, then open the
**Smart Money Explorer** page to browse detector metadata/parameters,
toggle detectors on/off, and preview detections overlaid on a
candlestick chart.

## Strategy Builder

Combines SDL, Market Context, Indicator, and Smart Money Engine outputs
into a reusable, executable `StrategyModel`. It does not execute trades,
backtest, optimize parameters, or generate AI decisions.

```python
from app.indicator_engine import IndicatorRegistry
from app.smart_money_engine import SMCRegistry
from app.sdl import StrategyParser, StrategyValidator as SDLValidator
from app.strategy_builder import StrategyBuilder, StrategyContext

indicator_registry = IndicatorRegistry()
indicator_registry.register_builtins()
smc_registry = SMCRegistry()
smc_registry.register_builtins()

data = StrategyParser().parse_file("app/sdl/examples/moving_average_cross.yaml")
sdl_definition = SDLValidator().validate(data).definition

context = StrategyContext(
    sdl_definition=sdl_definition,
    indicator_registry=indicator_registry,
    smc_registry=smc_registry,
)

model = StrategyBuilder().build(context)   # raises StrategyValidationError on failure
print(model.execution_pipeline.describe())
print(model.checksum, hash(model))          # immutable, hashable, versioned

# Or, without exceptions:
result = StrategyBuilder().try_build(context)
if not result.is_valid:
    print(result.validation.report())
```

Or via the Streamlit dashboard: `python main.py ui`, then open the
**Strategy Builder Explorer** page for the validation report, dependency
graph, execution pipeline preview, and strategy summary.

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the module layout,
design principles, and how the pipeline stages map to packages.
