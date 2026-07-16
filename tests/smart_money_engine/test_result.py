"""Tests for SMCDetection / SMCResult."""

import json

from app.smart_money_engine.result import SMCDetection, SMCResult


def _make_result(**overrides) -> SMCResult:
    defaults = dict(
        detector_name="Swing High",
        category="Structure",
        detector_version="1.0.0",
        result_version="1.0.0",
        symbol="EURUSD",
        timeframe="H1",
        parameters={"left_bars": 5, "right_bars": 5},
        detections=(SMCDetection(index=3, datetime="2024-01-01T03:00:00", label="Swing High", price=101.5),),
    )
    defaults.update(overrides)
    return SMCResult(**defaults)


def test_to_dict_is_json_safe() -> None:
    result = _make_result()
    json.dumps(result.to_dict())  # must not raise


def test_to_dict_contains_expected_keys() -> None:
    result = _make_result()
    data = result.to_dict()
    assert data["detector_name"] == "Swing High"
    assert data["detections"][0]["price"] == 101.5


def test_empty_detections_default() -> None:
    result = _make_result(detections=())
    assert result.detections == ()
    assert result.to_dict()["detections"] == []


def test_detection_to_dict_contains_all_fields() -> None:
    detection = SMCDetection(
        index=0,
        datetime="2024-01-01T00:00:00",
        label="Bullish FVG",
        direction="bullish",
        top=101.0,
        bottom=100.0,
        end_index=2,
        end_datetime="2024-01-01T02:00:00",
        notes="test",
    )
    data = detection.to_dict()
    assert data["label"] == "Bullish FVG"
    assert data["top"] == 101.0
    assert data["end_index"] == 2
