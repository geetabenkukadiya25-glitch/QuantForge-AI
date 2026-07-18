# QuantForge AI — Release Notes

## Version 1.0.0

**Release Date:** 2026-07-18

**First Stable Production Release.**

---

## Major Features

QuantForge AI is a complete, offline, deterministic AI-assisted strategy research platform covering the full pipeline from idea to a generated Expert Advisor:

```
Idea → AI Strategy Builder → Historical Data → Auto Backtest →
Optimization → Validation → Analytics → Replay →
Research → Knowledge Base → AI Extraction → Portfolio →
AI Assistant → EA Generator
```

- **Historical Data Engine** — CSV/MT5-export import, cleaning, validation, quality reporting.
- **Professional Chart Engine** — candlestick/OHLC charts, drawing tools, session overlays.
- **Strategy Definition Language (SDL)** — a machine-readable, versioned strategy document format.
- **Market Context Engine** — standardized market-state snapshots consumed by every downstream engine.
- **Indicator Engine** — 24 technical indicators as pure calculation components.
- **Smart Money Engine** — 32 Smart Money Concepts detectors.
- **Strategy Builder** — combines SDL, Context, Indicator, and Smart Money outputs into an executable, checksummed `StrategyModel`.
- **Backtesting Engine** — deterministic, candle-by-candle historical replay.
- **Optimization Engine** — Grid Search and Random Search over strategy parameters.
- **Walk Forward & Monte Carlo Validation Engine** — robustness/confidence/stability scoring of an optimized candidate.
- **Professional Replay Engine** — candle-by-candle playback with optional strategy/backtest overlays.
- **Research & Strategy Intelligence Engine** — cross-strategy comparison, ranking, and insights.
- **Knowledge Base Platform** — a curated trading-knowledge documentation system.
- **AI Strategy Extraction Engine** — converts external strategy documents (text, Pine Script, MQL4/5, pseudocode, etc.) into a draft SDL document, deterministically, offline.
- **Professional Portfolio Management Engine** — multi-strategy allocation, correlation, exposure, ranking, and portfolio-quality analytics.
- **AI Research Assistant** — a deterministic, offline natural-language search/explanation layer over everything already built in the platform.
- **EA Generator** — an offline MQL5 Expert Advisor source-code generator built from an already-validated `StrategyModel`.

Every "AI" component in this platform (AI Extraction, AI Assistant, EA Generator) is deterministic, offline, and rule-based — none call an external AI API or require internet access. **QuantForge AI never trades, never connects to a broker or MT5, and never places an order.** It is a research and code-generation platform only.

---

## Platform Statistics

| Metric | Count |
|---|---:|
| **Total Engines** | 17 (`app/*_engine/`, `app/sdl/`, `app/knowledge_base/`, `app/ai_extraction/`, `app/portfolio_engine/`, `app/ai_assistant/`, `app/ea_generator/`) |
| **Total UI Pages** | 17 (`app/ui/pages/`) |
| **Total Tests** | 2,166 |

---

## Verification Status

| Check | Result |
|---|---|
| **Compile Status** | ✅ Clean — `py_compile` across `app/` and `tests/`, 0 errors |
| **Runtime Status** | ✅ Verified — `python main.py api` / `python main.py ui` both start cleanly |
| **API Status** | ✅ `GET /health` → 200 |
| **UI Status** | ✅ All 17 pages verified via `AppTest` — 0 exceptions |
| **Test Suite** | ✅ 2,166 / 2,166 passing |
| **Production Certification** | ✅ Complete — see `PRODUCTION_CERTIFICATION.md`, `PROJECT_HEALTH_SCORE.md` (94/100), `MODULE_SCORECARD.md`, `TECHNICAL_DEBT.md` |

---

## Known Limitations

These are intentional, documented scope boundaries — not defects:

- **No live trading, no broker connection, no MT5 connection.** The platform is research-and-generation only through v1.0.
- **EA Generator produces a skeleton, not a finished EA.** Generated MQL5 source includes `TODO` markers for indicator handle wiring and condition translation — a human developer must complete and compile it in MetaEditor before live use, per the project's "AI assists, humans approve" principle.
- **No embeddings, no vector database, no external AI API anywhere** — all "AI" components are deterministic and rule-based by design, not a limitation to be lifted later.
- **Optimization search methods are Grid Search and Random Search only** — smarter methods (genetic, Bayesian, particle swarm) are an explicitly deferred future enhancement (`PROJECT_IDEAS.md`).
- **No multi-user access control, no cloud deployment, no authentication layer** — this is a local, single-user platform through v1.0; see Future Roadmap below.
- A small number of low-severity technical-debt items remain tracked in `TECHNICAL_DEBT.md` (e.g. minor naming-convention drift in two modules, two orphaned `requirements.txt` entries) — none affect correctness, determinism, or security, and none block this release.

---

## Future Roadmap

Per `PROJECT_VISION.md`'s Approved Roadmap, **Phase 17 — Cloud Platform** begins only after this v1.0 tag: secure paid deployment, authentication, license validation, and cloud-hosted AI/EA/premium services.

Additional, unapproved future ideas (Research Governance, Data Governance, Artifact Management, Workflow Automation, Risk Infrastructure, Institutional Features, and a future Cloud Version) are tracked separately in `PROJECT_IDEAS.md` and will only be considered after v1.0 is complete, following the same phase-by-phase approval process used throughout this project's history.

---

## Full History

See `docs/ROADMAP.md` for the complete phase-by-phase build record, and `docs/ARCHITECTURE.md` for the module-by-module architecture reference.
