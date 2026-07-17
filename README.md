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

> **Status: Phase 10 (Optimization Engine).** Phase 1 established the
> project architecture. Phase 2 added a historical OHLCV data engine.
> Phase 3 added a professional chart engine. Phase 4 added the Strategy
> Definition Language. Phase 5 added the Market Context Engine. Phase 6
> added the Indicator Engine. Phase 7 added the Smart Money Engine.
> Phase 8 added the Strategy Builder, combining SDL, Market Context,
> Indicator, and Smart Money Engine outputs into a reusable, executable
> `StrategyModel`. Phase 9 added the Backtesting Engine — deterministic,
> candle-by-candle historical replay of a compiled `StrategyModel`. Phase
> 10 adds the Optimization Engine (`app/optimization_engine/`) — Grid
> Search and Random Search over `StrategyModel` parameters using the
> existing, unmodified Backtesting Engine. It never executes live trades,
> never connects to a broker, and never requires MetaTrader. No
> walk-forward, Monte Carlo, or AI are implemented yet. See
> [docs/ROADMAP.md](docs/ROADMAP.md).

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
│   └── optimization_engine/                  # Optimization Engine unit tests
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
