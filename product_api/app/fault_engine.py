from collections.abc import Mapping
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.types import ASGIApp

from app.faults import create_fault


class FaultEngine(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        mode: str = "normal",
        fault_options: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> None:
        super().__init__(app)
        options = dict((fault_options or {}).get(mode, {}))
        if mode == "random":
            options["fault_options"] = fault_options or {}
        self.fault = create_fault(mode, options)

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        return await self.fault.apply(request, call_next)
