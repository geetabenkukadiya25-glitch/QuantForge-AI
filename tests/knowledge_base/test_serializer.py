"""`KnowledgeSerializer`: to_dict/to_json/to_yaml round-trip, plus per-entry export."""

import json

import yaml

from app.knowledge_base.runner import KnowledgeRunner
from app.knowledge_base.serializer import KnowledgeSerializer


def test_to_dict_is_json_safe(knowledge_context) -> None:
    result = KnowledgeRunner().execute(knowledge_context)
    data = KnowledgeSerializer().to_dict(result)
    assert data["result_id"] == result.result_id
    assert data["checksum"] == result.checksum


def test_to_json_round_trips(knowledge_context) -> None:
    result = KnowledgeRunner().execute(knowledge_context)
    text = KnowledgeSerializer().to_json(result)
    parsed = json.loads(text)
    assert parsed["checksum"] == result.checksum


def test_to_json_canonical_is_stable(knowledge_context) -> None:
    result = KnowledgeRunner().execute(knowledge_context)
    a = KnowledgeSerializer().to_json(result, canonical=True)
    b = KnowledgeSerializer().to_json(result, canonical=True)
    assert a == b


def test_to_yaml_round_trips(knowledge_context) -> None:
    result = KnowledgeRunner().execute(knowledge_context)
    text = KnowledgeSerializer().to_yaml(result)
    parsed = yaml.safe_load(text)
    assert parsed["checksum"] == result.checksum


def test_entry_to_dict(entry_fvg) -> None:
    data = KnowledgeSerializer().entry_to_dict(entry_fvg)
    assert data["entry_id"] == entry_fvg.entry_id


def test_entry_to_json(entry_fvg) -> None:
    text = KnowledgeSerializer().entry_to_json(entry_fvg)
    parsed = json.loads(text)
    assert parsed["entry_id"] == entry_fvg.entry_id


def test_entry_to_markdown_contains_title_and_content(entry_fvg) -> None:
    text = KnowledgeSerializer().entry_to_markdown(entry_fvg)
    assert entry_fvg.title in text
    assert entry_fvg.content in text
    assert entry_fvg.category.value in text
