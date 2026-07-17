"""Pre-execution validation for a `KnowledgeContext`."""

from app.knowledge_base.context import KnowledgeContext
from app.knowledge_base.models import KnowledgeConfiguration
from app.knowledge_base.validator import KnowledgeValidator
from tests.knowledge_base.conftest import make_entry


def test_valid_context_passes(knowledge_context) -> None:
    result = KnowledgeValidator().validate(knowledge_context)
    assert result.is_valid


def test_empty_entries_is_rejected(knowledge_configuration) -> None:
    context = KnowledgeContext(entries=(), configuration=knowledge_configuration)
    result = KnowledgeValidator().validate(context)
    assert not result.is_valid
    assert any("entries" in issue.path for issue in result.errors)


def test_below_minimum_entries_is_rejected(entries) -> None:
    config = KnowledgeConfiguration(min_entries_required=10)
    context = KnowledgeContext(entries=entries, configuration=config)
    result = KnowledgeValidator().validate(context)
    assert not result.is_valid


def test_duplicate_entry_ids_are_rejected(entry_fvg, knowledge_configuration) -> None:
    context = KnowledgeContext(entries=(entry_fvg, entry_fvg), configuration=knowledge_configuration)
    result = KnowledgeValidator().validate(context)
    assert not result.is_valid
    assert any("Duplicate entry id" in e.message for e in result.errors)


def test_duplicate_titles_are_rejected_by_default(knowledge_configuration) -> None:
    e1 = make_entry("a", title="Same Title")
    e2 = make_entry("b", title="Same Title")
    context = KnowledgeContext(entries=(e1, e2), configuration=knowledge_configuration)
    result = KnowledgeValidator().validate(context)
    assert not result.is_valid
    assert any("Duplicate title" in e.message for e in result.errors)


def test_duplicate_titles_allowed_when_configured() -> None:
    e1 = make_entry("a", title="Same Title")
    e2 = make_entry("b", title="Same Title")
    config = KnowledgeConfiguration(require_unique_titles=False)
    context = KnowledgeContext(entries=(e1, e2), configuration=config)
    result = KnowledgeValidator().validate(context)
    assert result.is_valid


def test_dangling_related_entry_id_is_rejected(knowledge_configuration) -> None:
    entry = make_entry("a", related_entry_ids=("does-not-exist",))
    context = KnowledgeContext(entries=(entry,), configuration=knowledge_configuration)
    result = KnowledgeValidator().validate(context)
    assert not result.is_valid
    assert any("unknown entry id" in e.message for e in result.errors)


def test_self_referencing_related_entry_id_is_rejected(knowledge_configuration) -> None:
    entry = make_entry("a", related_entry_ids=("a",))
    context = KnowledgeContext(entries=(entry,), configuration=knowledge_configuration)
    result = KnowledgeValidator().validate(context)
    assert not result.is_valid
    assert any("cannot reference itself" in e.message for e in result.errors)


def test_valid_indicator_type_reference_passes(indicator_registry, knowledge_configuration) -> None:
    entry = make_entry("a", related_indicator_types=("SMA",))
    context = KnowledgeContext(entries=(entry,), configuration=knowledge_configuration, indicator_registry=indicator_registry)
    result = KnowledgeValidator().validate(context)
    assert result.is_valid


def test_unknown_indicator_type_reference_is_rejected(indicator_registry, knowledge_configuration) -> None:
    entry = make_entry("a", related_indicator_types=("SESSION_RANGE_HIGH",))
    context = KnowledgeContext(entries=(entry,), configuration=knowledge_configuration, indicator_registry=indicator_registry)
    result = KnowledgeValidator().validate(context)
    assert not result.is_valid
    assert any("not a registered Indicator Engine name" in e.message for e in result.errors)


def test_valid_detector_type_reference_passes(smc_registry, knowledge_configuration) -> None:
    entry = make_entry("a", related_detector_types=("Order Block",))
    context = KnowledgeContext(entries=(entry,), configuration=knowledge_configuration, smc_registry=smc_registry)
    result = KnowledgeValidator().validate(context)
    assert result.is_valid


def test_unknown_detector_type_reference_is_rejected(smc_registry, knowledge_configuration) -> None:
    entry = make_entry("a", related_detector_types=("ORDER_BLOCK",))
    context = KnowledgeContext(entries=(entry,), configuration=knowledge_configuration, smc_registry=smc_registry)
    result = KnowledgeValidator().validate(context)
    assert not result.is_valid
    assert any("not a registered Smart Money Engine name" in e.message for e in result.errors)


def test_component_references_skipped_without_registries(knowledge_configuration) -> None:
    entry = make_entry("a", related_indicator_types=("totally-made-up",), related_detector_types=("also-made-up",))
    context = KnowledgeContext(entries=(entry,), configuration=knowledge_configuration)
    result = KnowledgeValidator().validate(context)
    assert result.is_valid


def test_report_lists_every_error() -> None:
    from app.knowledge_base.validator import KnowledgeCheckResult, KnowledgeIssue

    result = KnowledgeCheckResult(errors=[KnowledgeIssue(path="a", message="bad")])
    assert "FAILED" in result.report()
    assert "a: bad" in result.report()
