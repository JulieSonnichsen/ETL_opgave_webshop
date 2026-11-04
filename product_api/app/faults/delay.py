import asyncio
import math
import random

from fastapi import Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from .base import Fault, coerce_scalar_json_response
from .registry import register_fault


@register_fault("delay")
class DelayFault(Fault):
    def __init__(
        self,
        delay_min_seconds: float = 0.1,
        delay_max_seconds: float = 2.0,
    ) -> None:
        if (
            not math.isfinite(delay_min_seconds)
            or not math.isfinite(delay_max_seconds)
            or delay_min_seconds < 0
            or delay_max_seconds < delay_min_seconds
        ):
            raise ValueError(
                "Delay bounds must be finite, non-negative, and ordered "
                "from minimum to maximum"
            )
        self.delay_min_seconds = delay_min_seconds
        self.delay_max_seconds = delay_max_seconds

    async def apply(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)
        response = await coerce_scalar_json_response(response)
        delay_seconds = random.uniform(
            self.delay_min_seconds,
            self.delay_max_seconds,
        )
        await asyncio.sleep(delay_seconds)
        return response
