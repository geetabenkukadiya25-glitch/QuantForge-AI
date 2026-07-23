"""`ipc.py` -- every `BridgeTransport` method raises `NotImplementedError`,
mirroring `test_cloud_provider.py`'s style exactly."""

import pytest

from app.mt5.ipc import BridgeTransport, LocalSocketTransport, NamedPipeTransport

_ALL_TRANSPORTS = [BridgeTransport, NamedPipeTransport, LocalSocketTransport]


@pytest.mark.parametrize("transport_cls", _ALL_TRANSPORTS)
def test_every_method_raises_not_implemented(transport_cls) -> None:
    transport = transport_cls()
    with pytest.raises(NotImplementedError):
        transport.send("payload")
    with pytest.raises(NotImplementedError):
        transport.receive()


def test_placeholder_transports_have_descriptive_metadata() -> None:
    for transport_cls in _ALL_TRANSPORTS[1:]:
        assert transport_cls.display_name
        assert transport_cls.description
        assert transport_cls.display_name != BridgeTransport.display_name


def test_instantiation_is_safe_pure_metadata() -> None:
    for transport_cls in _ALL_TRANSPORTS:
        transport_cls()
