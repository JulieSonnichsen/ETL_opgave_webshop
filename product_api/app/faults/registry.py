from collections.abc import Callable, Mapping
from typing import Any, TypeVar

from .base import Fault


FaultType = TypeVar("FaultType", bound=type[Fault])
FaultFactory = Callable[..., Fault]
_FAULTS: dict[str, FaultFactory] = {}


def register_fault(mode: str) -> Callable[[FaultType], FaultType]:
    def register(fault_type: FaultType) -> FaultType:
        if not issubclass(fault_type, Fault):
            raise TypeError("Registered fault plugins must implement Fault")
        if mode in _FAULTS:
            raise ValueError(f"A fault is already registered for mode {mode!r}")
        _FAULTS[mode] = fault_type
        return fault_type

    return register


def create_fault(
    mode: str,
    options: Mapping[str, Any] | None = None,
) -> Fault:
    try:
        fault_factory = _FAULTS[mode]
    except KeyError as error:
        supported_modes = ", ".join(sorted(("normal", *_FAULTS)))
        raise ValueError(
            f"Unknown fault mode {mode!r}; supported modes: "
            f"{supported_modes}"
        ) from error
    return fault_factory(**dict(options or {}))


def registered_faults() -> tuple[str, ...]:
    return tuple(sorted(_FAULTS))
