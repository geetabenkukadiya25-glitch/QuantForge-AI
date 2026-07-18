"""Missing Information Detector: the explicit "ask a human" list.

Pure aggregation over already-extracted mentions -- never a judgment
about strategy quality, only about completeness of what was found.
"""

from app.ai_extraction.models import (
    DetectorMention,
    ExtractionWarning,
    IndicatorMention,
    MissingInformationReport,
    RiskMention,
    RuleMention,
    SessionMention,
    TimeframeMention,
)


class MissingInformationDetector:
    """Flags empty or thin extraction categories."""

    def detect(
        self,
        indicators: tuple[IndicatorMention, ...],
        detectors: tuple[DetectorMention, ...],
        entry_rules: tuple[RuleMention, ...],
        exit_rules: tuple[RuleMention, ...],
        risk_mentions: tuple[RiskMention, ...],
        sessions: tuple[SessionMention, ...],
        timeframes: tuple[TimeframeMention, ...],
        name_detected: bool,
        description_detected: bool,
    ) -> MissingInformationReport:
        missing: list[str] = []
        warnings: list[ExtractionWarning] = []

        if not name_detected:
            missing.append("strategy_name")
            warnings.append(ExtractionWarning(category="strategy_name", message="No title/heading detected; a placeholder name was used.", severity="warning"))
        if not description_detected:
            missing.append("description")
            warnings.append(ExtractionWarning(category="description", message="No descriptive paragraph detected.", severity="info"))
        if not entry_rules:
            missing.append("entry_rules")
            warnings.append(ExtractionWarning(category="entry_rules", message="No entry rules detected. This is a required field for an executable strategy.", severity="warning"))
        if not exit_rules:
            missing.append("exit_rules")
            warnings.append(ExtractionWarning(category="exit_rules", message="No exit rules detected.", severity="warning"))
        if not indicators and not detectors:
            missing.append("indicators_or_detectors")
            warnings.append(ExtractionWarning(category="indicators", message="No indicators or Smart Money structures detected.", severity="warning"))
        if not risk_mentions:
            missing.append("risk_management")
            warnings.append(ExtractionWarning(category="risk_management", message="No risk management statements detected (stop loss, position sizing, etc.).", severity="warning"))
        if not timeframes:
            missing.append("timeframes")
            warnings.append(ExtractionWarning(category="timeframes", message="No timeframe detected; a placeholder ('UNKNOWN') was used.", severity="warning"))
        if not sessions:
            missing.append("sessions")
            warnings.append(ExtractionWarning(category="sessions", message="No trading session detected.", severity="info"))

        missing.append("symbol")
        warnings.append(ExtractionWarning(category="symbol", message="This engine does not detect trading symbols; a placeholder ('UNKNOWN') was used. A human must set the real symbol.", severity="warning"))

        return MissingInformationReport(missing_items=tuple(missing), warnings=tuple(warnings))
