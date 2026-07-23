"""`compatibility.py` -- pure comparison logic."""

from app.mt5.compatibility import MIN_SUPPORTED_TERMINAL_BUILD, SUPPORTED_PACKAGE_VERSION, evaluate


def test_matching_package_version_and_build_is_fully_supported() -> None:
    result = evaluate(SUPPORTED_PACKAGE_VERSION, MIN_SUPPORTED_TERMINAL_BUILD)
    assert result.package_supported is True
    assert result.terminal_supported is True
    assert result.notes == []


def test_mismatched_package_version_produces_a_note_not_a_failure() -> None:
    result = evaluate("1.0.0", MIN_SUPPORTED_TERMINAL_BUILD)
    assert result.package_supported is False
    assert result.notes


def test_low_terminal_build_produces_a_note() -> None:
    result = evaluate(SUPPORTED_PACKAGE_VERSION, MIN_SUPPORTED_TERMINAL_BUILD - 1)
    assert result.terminal_supported is False
    assert result.notes


def test_unknown_terminal_build_is_none_not_false() -> None:
    result = evaluate(SUPPORTED_PACKAGE_VERSION, None)
    assert result.terminal_supported is None
