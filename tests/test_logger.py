"""Tests for the logging system."""

import logging

from app.utils.logger import get_logger


def test_get_logger_returns_namespaced_logger() -> None:
    logger = get_logger("tests.example")
    assert logger.name == "quantforge.tests.example"


def test_root_logger_has_handlers_configured() -> None:
    get_logger("tests.example")
    root = logging.getLogger("quantforge")
    assert len(root.handlers) > 0
