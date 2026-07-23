"""Bridge transport interface (Phase 19.0) -- future foundation only,
mirroring `app.cloud_sync.cloud_provider.CloudProvider`'s discipline
exactly. `BridgeTransport` defines the shape a real transport (named
pipe, local socket, or similar) would someday implement to hand
`json_bridge` payloads to an external consumer such as "SMC GOLD AI
TRADER PRO". Every method here unconditionally raises
`NotImplementedError`. This file must never import `socket`, `asyncio`
network primitives, or any other network-capable library -- "Bridge
only. No execution," and this phase does not wire up a live transport.
"""


class BridgeTransport:
    """Base interface a real transport would subclass and implement.
    Instantiating this class is safe (pure metadata); calling either
    method is not supported and says so explicitly."""

    display_name: str = "No Transport"
    description: str = "No bridge transport is implemented -- this is a schema/foundation-only build."

    def _not_implemented(self, method_name: str) -> NotImplementedError:
        return NotImplementedError(f"{type(self).__name__}.{method_name}() is not implemented -- the MT5 Integration Layer provides no real IPC/network transport.")

    def send(self, payload: str) -> None:
        raise self._not_implemented("send")

    def receive(self) -> str:
        raise self._not_implemented("receive")


class NamedPipeTransport(BridgeTransport):
    display_name = "Named Pipe (Windows)"
    description = "Would hand bridge JSON to a local named pipe for an external EA to read. Not implemented -- no IPC code exists."


class LocalSocketTransport(BridgeTransport):
    display_name = "Local Socket"
    description = "Would hand bridge JSON to a local TCP/Unix socket. Not implemented -- no network code exists."
