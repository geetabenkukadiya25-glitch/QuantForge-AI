"""`language.py` -- confirms the single, honestly-documented supported value."""

from app.settings_center.language import Language


def test_only_english_supported() -> None:
    assert [lang.value for lang in Language] == ["en"]
