"""One aggregated "run diagnostics" pass (Phase 19.0): package import
check, terminal discovery, connection ping, symbol availability. Every
step is read-only and best-effort -- a failed step is recorded in the
report, never raised past this function (except the caller-visible
report itself), so the UI can always render a full diagnostics run.
"""

from dataclasses import dataclass, field

from app.mt5.connection_manager import ConnectionManager, import_mt5
from app.mt5.exceptions import MT5Error, MT5NotInstalledError
from app.mt5.mt5_models import ConnectionState
from app.mt5.terminal_discovery import discover_terminals


@dataclass
class DiagnosticStep:
    name: str
    passed: bool
    detail: str


@dataclass
class DiagnosticsReport:
    steps: list[DiagnosticStep] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(step.passed for step in self.steps)


def run_diagnostics(connection: ConnectionManager, sample_symbol: str = "EURUSD") -> DiagnosticsReport:
    report = DiagnosticsReport()

    try:
        import_mt5()
        report.steps.append(DiagnosticStep("MetaTrader5 package import", True, "Package imported successfully."))
    except MT5NotInstalledError as exc:
        report.steps.append(DiagnosticStep("MetaTrader5 package import", False, str(exc)))
        return report  # nothing further can be checked without the package

    discovered = discover_terminals()
    report.steps.append(DiagnosticStep(
        "Terminal discovery",
        True,  # discovery finding nothing is not itself a failure -- initialize() can still locate one
        f"Found {len(discovered)} candidate terminal executable(s)." if discovered else "No terminal executables found in common install locations (this is not necessarily a problem).",
    ))

    report.steps.append(DiagnosticStep(
        "Connection state",
        connection.state == ConnectionState.CONNECTED,
        f"Current state: {connection.state.value}.",
    ))

    if connection.state == ConnectionState.CONNECTED:
        try:
            latency_ms = connection.ping()
            report.steps.append(DiagnosticStep("Ping", True, f"Round-trip latency: {latency_ms:.1f} ms."))
        except MT5Error as exc:
            report.steps.append(DiagnosticStep("Ping", False, str(exc)))

        try:
            from app.mt5.symbol_manager import get_symbol_info

            get_symbol_info(connection, sample_symbol)
            report.steps.append(DiagnosticStep("Sample symbol availability", True, f"'{sample_symbol}' is available."))
        except MT5Error as exc:
            report.steps.append(DiagnosticStep("Sample symbol availability", False, str(exc)))
    else:
        report.steps.append(DiagnosticStep("Ping", False, "Skipped -- not connected."))
        report.steps.append(DiagnosticStep("Sample symbol availability", False, "Skipped -- not connected."))

    return report
