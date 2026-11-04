import random
from collections.abc import Mapping
from typing import Any

from fastapi import Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from .base import Fault, validate_probability
from .registry import create_fault, register_fault, registered_faults


@register_fault("random")
class RandomFault(Fault):
    def __init__(
        self,
        fault_probability: float = 0.5,
        fault_options: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> None:
        validate_probability(fault_probability)
        self.fault_probability = fault_probability
        options_by_mode = fault_options or {}
        self.normal_fault = create_fault("normal", options_by_mode.get("normal"))
        self.other_faults = {
            mode: create_fault(mode, options_by_mode.get(mode))
            for mode in registered_faults()
            if mode not in {"normal", "random"}
        }
        if not self.other_faults:
            raise ValueError("Random fault mode requires at least one other fault")

    async def apply(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if random.random() >= self.fault_probability:
            return await self.normal_fault.apply(request, call_next)

        mode = random.choice(tuple(self.other_faults))
        return await self.other_faults[mode].apply(request, call_next)
