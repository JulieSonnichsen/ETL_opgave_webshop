import json
import math
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from fastapi import Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response


def validate_probability(probability: float) -> None:
    if not math.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("Fault probability must be between 0 and 1")


async def response_body(response: Response) -> bytes:
    return b"".join([chunk async for chunk in response.body_iterator])


def body_iterator(body: bytes) -> AsyncIterator[bytes]:
    async def iterator() -> AsyncIterator[bytes]:
        yield body

    return iterator()


async def coerce_scalar_json_response(response: Response) -> Response:
    body = await response_body(response)

    try:
        payload = json.loads(body)
    except (TypeError, ValueError):
        response.body_iterator = body_iterator(body)
        return response

    if isinstance(payload, (dict, list)):
        response.body_iterator = body_iterator(body)
        return response

    if isinstance(payload, str):
        text = payload
    elif payload is None:
        text = "null"
    elif isinstance(payload, bool):
        text = "true" if payload else "false"
    else:
        text = json.dumps(payload, separators=(",", ":"))

    headers = {
        key: value
        for key, value in response.headers.items()
        if key.lower() not in {"content-type", "content-length"}
    }
    return Response(
        content=text,
        status_code=response.status_code,
        headers=headers,
        media_type="text/plain",
    )


class Fault(ABC):
    @abstractmethod
    async def apply(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Apply this fault to a request and its response."""


class ResponseBodyFault(Fault):
    json_only = True
    update_content_length = True

    @abstractmethod
    def transform_body(self, body: bytes) -> bytes:
        """Transform the response body."""

    async def apply(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)
        response = await coerce_scalar_json_response(response)
        content_type = response.headers.get("content-type", "")
        if self.json_only and not content_type.startswith("application/json"):
            return response

        transformed_body = self.transform_body(await response_body(response))
        response.body_iterator = body_iterator(transformed_body)
        if self.update_content_length:
            response.headers["content-length"] = str(len(transformed_body))
        return response
