"""Shared fixtures for knowledge_base tests."""

import pytest

from app.indicator_engine.registry import IndicatorRegistry
from app.knowledge_base.context import KnowledgeContext
from app.knowledge_base.models import DifficultyLevel, KnowledgeCategory, KnowledgeConfiguration, KnowledgeEntry
from app.smart_money_engine.registry import SMCRegistry


@pytest.fixture
def indicator_registry() -> IndicatorRegistry:
    registry = IndicatorRegistry()
    registry.register_builtins()
    return registry


@pytest.fixture
def smc_registry() -> SMCRegistry:
    registry = SMCRegistry()
    registry.register_builtins()
    return registry


def make_entry(entry_id: str, **overrides) -> KnowledgeEntry:
    base = dict(
        entry_id=entry_id,
        title=f"Title for {entry_id}",
        category=KnowledgeCategory.SMC,
        summary="A short summary.",
        content="Full content body describing the concept in detail.",
        difficulty=DifficultyLevel.BEGINNER,
    )
    base.update(overrides)
    return KnowledgeEntry(**base)


@pytest.fixture
def entry_fvg() -> KnowledgeEntry:
    return make_entry(
        "fvg-101", title="Fair Value Gaps 101", category=KnowledgeCategory.FAIR_VALUE_GAPS, difficulty=DifficultyLevel.BEGINNER,
        tags=("smc", "imbalance"), asset_classes=("forex",), timeframes=("H1", "H4"), sessions=("London",),
    )


@pytest.fixture
def entry_order_block(entry_fvg) -> KnowledgeEntry:
    return make_entry(
        "ob-101", title="Order Blocks 101", category=KnowledgeCategory.ORDER_BLOCKS, difficulty=DifficultyLevel.INTERMEDIATE,
        tags=("smc", "structure"), related_entry_ids=(entry_fvg.entry_id,),
    )


@pytest.fixture
def entry_risk() -> KnowledgeEntry:
    return make_entry(
        "risk-101", title="Risk Management 101", category=KnowledgeCategory.RISK_MANAGEMENT, difficulty=DifficultyLevel.ADVANCED,
        tags=("risk",),
    )


@pytest.fixture
def entries(entry_fvg, entry_order_block, entry_risk) -> tuple[KnowledgeEntry, ...]:
    return (entry_fvg, entry_order_block, entry_risk)


@pytest.fixture
def knowledge_configuration() -> KnowledgeConfiguration:
    return KnowledgeConfiguration()


@pytest.fixture
def knowledge_context(entries, knowledge_configuration) -> KnowledgeContext:
    return KnowledgeContext(entries=entries, configuration=knowledge_configuration)
