from fastapi import Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from .base import Fault
from .registry import register_fault


@register_fault("normal")
class NormalFault(Fault):
    async def apply(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        return await call_next(request)
