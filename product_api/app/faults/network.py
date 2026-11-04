from abc import abstractmethod
import random

from fastapi import Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from .base import Fault, validate_probability
from .registry import register_fault


class ProbabilisticNetworkFault(Fault):
    def __init__(self, probability: float = 1.0) -> None:
        validate_probability(probability)
        self.probability = probability

    async def apply(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if random.random() >= self.probability:
            return await call_next(request)
        return self.error_response()

    @abstractmethod
    def error_response(self) -> Response:
        """Build the simulated network error response."""


@register_fault("service_unavailable")
class ServiceUnavailableFault(ProbabilisticNetworkFault):
    def error_response(self) -> Response:
        return JSONResponse(
            {"detail": "Service temporarily unavailable"},
            status_code=503,
        )


@register_fault("rate_limit")
class RateLimitFault(ProbabilisticNetworkFault):
    def error_response(self) -> Response:
        retry_after = random.randint(1, 5)
        return JSONResponse(
            {"detail": "Rate limit exceeded"},
            status_code=429,
            headers={"Retry-After": str(retry_after)},
        )


@register_fault("gateway_error")
class GatewayErrorFault(ProbabilisticNetworkFault):
    def error_response(self) -> Response:
        status_code = random.choice((502, 503, 504))
        return JSONResponse(
            {"detail": "Simulated gateway error"},
            status_code=status_code,
        )
