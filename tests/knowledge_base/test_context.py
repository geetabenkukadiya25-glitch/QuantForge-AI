"""`KnowledgeContext`: the standardized knowledge base input."""

from app.knowledge_base.context import KnowledgeContext


def test_context_bundles_entries_and_configuration(knowledge_context, entries, knowledge_configuration) -> None:
    assert knowledge_context.entries == entries
    assert knowledge_context.configuration is knowledge_configuration


def test_context_registries_default_to_none(knowledge_context) -> None:
    assert knowledge_context.indicator_registry is None
    assert knowledge_context.smc_registry is None


def test_context_can_carry_optional_registries(entries, knowledge_configuration, indicator_registry, smc_registry) -> None:
    context = KnowledgeContext(entries=entries, configuration=knowledge_configuration, indicator_registry=indicator_registry, smc_registry=smc_registry)
    assert context.indicator_registry is indicator_registry
    assert context.smc_registry is smc_registry


def test_context_is_a_frozen_dataclass(knowledge_context) -> None:
    import dataclasses

    assert dataclasses.is_dataclass(knowledge_context)
    try:
        knowledge_context.entries = ()  # type: ignore[misc]
        assert False, "expected FrozenInstanceError"
    except dataclasses.FrozenInstanceError:
        pass
