# PROJECT_VISION.md

**This file is the permanent constitution for the QuantForge AI project.**

Every future development task must read and follow this file before writing or
modifying any code. If a new request conflicts with this document, explain the
conflict and do not implement the conflicting change without explicit approval.

---

## Project Identity

**Project Name:** QuantForge AI

**Mission:** Build an institutional-grade trading strategy research,
backtesting, optimization, replay, analytics, and MT5 EA generation platform.

**Long-Term Vision:** QuantForge AI will become a complete trading research
operating system where users can:

- Import historical market data
- Analyze charts
- Build strategies
- Backtest and optimize strategies
- Run walk-forward and Monte Carlo validation
- Practice using replay mode
- Review results with AI assistance
- Generate MT5 Expert Advisors
- Manage strategy versions and research history
- Use the platform through a secure paid web and desktop application

---

## Core Principles

- Modular architecture first.
- Backward compatibility first.
- Test before merge.
- Security by design.
- Privacy by design.
- No hardcoded secrets.
- Configuration-driven behavior.
- Clean architecture and SOLID principles.
- Explicit error handling.
- Full documentation for every phase.
- Human review before critical automated decisions.
- AI assists, humans approve.

---

## Development Workflow

Every phase must follow this order:

1. Build
2. Compile
3. Run tests
4. Validate behavior
5. Fix issues
6. Update documentation
7. Commit
8. Wait for approval

No phase is complete until all tests pass and documentation is updated.

---

## Architecture Rules

- Use engine-based architecture.
- Each module must be independent and replaceable.
- Avoid tight coupling between modules.
- Use clear interfaces and abstractions.
- Keep data flow explicit.
- Separate UI, business logic, data access, AI services, and external
  integrations.
- Future plugins must be sandboxed and permission-controlled.
- Do not duplicate logic across modules.
- Do not introduce hidden dependencies.

---

## Single Source of Truth (SSOT)

Every business concept shall have exactly one authoritative representation.

| Concept | Authoritative Module |
|---------|----------------------|
| Historical Data | Data Engine |
| Charts | Chart Engine |
| Strategies | SDL |
| Indicators | Indicator Engine |
| Backtests | Backtesting Engine |
| EA Generation | EA Generator |

No module may redefine or duplicate another module's business logic.

---

## Feature Flag System

Every major engine must support feature flags.

- Experimental features shall remain disabled by default.
- No unfinished feature may affect stable modules.
- Production mode must expose only stable features.
- Feature flags are read from configuration, not hardcoded.

---

## Event Driven Architecture

Major modules should communicate through events instead of tight coupling
whenever practical.

- Future engines should be able to subscribe to events without modifying
  existing modules.

---

## Context Before Decision

No trading decision engine may directly consume raw market data.

- Every decision engine must consume standardized Market Context produced
  by the Market Context Engine.

---

## Coding Standards

- Use Python type hints.
- Write clear docstrings.
- Use structured logging.
- Handle exceptions explicitly.
- Write unit tests for new functionality.
- Keep functions focused and small.
- Avoid global mutable state.
- Avoid hardcoded paths.
- Use environment variables for configuration.
- Use a centralized settings/config system.

---

## Security Vision

Security is a first-class requirement.

The system must be designed to reduce risk, not claim to be impossible to
hack.

Required security principles:

- Zero trust architecture where appropriate.
- Authentication required for protected features.
- Role-based access control.
- Least privilege access.
- No secrets stored in source code.
- Encrypted transport for network communication.
- Encrypted storage for sensitive local data where appropriate.
- License validation for paid access.
- Device activation and license management support.
- Audit logging for security-sensitive actions.
- Integrity checks for production builds.
- Signed updates when production deployment exists.
- Rate limiting and request validation for APIs.
- Dependency and secret scanning before release.
- Security testing before production releases.
- Safe failure behavior when validation fails.

---

## Paid Product and Deployment Vision

QuantForge AI is intended to become a paid platform.

Preferred architecture:

- Desktop or web client
- Secure backend API
- Cloud-based authentication
- Cloud-based license validation
- Cloud-hosted AI services
- Cloud-hosted EA generation
- Cloud-hosted premium features
- Local offline grace period where appropriate

Sensitive business logic, license control, AI services, and premium features
should not rely solely on unrestricted client-side access.

---

## AI and Automation Rules

AI may assist with:

- Strategy extraction
- Code generation
- Report analysis
- Optimization suggestions
- Trade review

AI may not automatically execute critical trading decisions without human
approval.

**YouTube strategy workflow:**

1. Import video or transcript
2. Extract strategy rules
3. Present extracted rules to the user
4. Require human review and approval
5. Generate Python strategy code only after approval
6. Run backtest
7. Generate report
8. Generate MT5 EA only after validated approval

---

## Approved Roadmap

| Phase | Name |
|-------|------|
| 1 | Foundation |
| 2 | Historical Data Engine |
| 3 | Professional Chart Engine |
| 4 | Strategy Definition Language (SDL) |
| 5 | Market Context Engine |
| 6 | Indicator Engine |
| 7 | Smart Money Engine |
| 8 | Strategy Builder |
| 9 | Backtesting Engine |
| 10 | Optimization Engine |
| 11 | Replay Engine |
| 12 | Walk Forward & Monte Carlo |
| 13 | AI Strategy Extraction |
| 14 | Knowledge Base |
| 15 | AI Research Assistant |
| 16 | EA Generator |
| 17 | Cloud Platform |

---

## Approved Future Features

- Professional charting
- Drawing tools
- Multi-timeframe analysis
- Market session overlays
- Strategy builder
- Backtesting
- Optimization
- Walk-forward validation
- Monte Carlo analysis
- Replay mode
- Manual trading simulator
- AI trade review
- Strategy version control
- Experiment manager
- Strategy library
- Dataset manager
- Risk lab
- Portfolio testing
- Institutional report generator
- AI chat assistant
- MT5 EA generation
- Plugin system
- Secure paid deployment

---

## Market Replay Vision

Replay mode must allow:

- Candle-by-candle playback
- Play, pause, stop
- Rewind and fast forward
- Jump to date and time
- Manual buy and sell actions
- Manual stop loss and take profit
- Risk-reward measurement
- Trade journaling
- Session scoring
- Replay session save and load
- AI feedback after replay completion

---

## Definition of Done

A phase is complete only when:

- Code compiles successfully.
- All tests pass.
- No existing functionality is broken.
- Documentation is updated.
- Architecture remains consistent.
- Security considerations are reviewed.
- The phase stays within its approved scope.

---

## Out of Scope Rule

Do not implement features from future phases unless explicitly approved.

If a requested feature belongs to a later phase, document it and wait for
approval.

Do not add hidden features.

Do not expand scope silently.

---

## Parking Lot for Future Ideas

Future ideas may be documented here but must not be implemented
automatically.

Examples:

- Additional broker integrations
- Mobile applications
- Cloud synchronization
- Advanced AI coaching
- Strategy marketplace
- Collaborative research features

---

## Final Non-Negotiable Rules

- PROJECT_VISION.md is the highest authority for the project.
- Read this file before every development task.
- Follow the approved roadmap.
- Preserve backward compatibility.
- Do not bypass tests.
- Do not bypass security requirements.
- Do not store secrets in code.
- Do not implement unapproved scope.
- Update documentation with every completed phase.
- Stop after completing the approved phase and wait for the next instruction.
