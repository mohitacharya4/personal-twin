"""HTTP middleware: correlation ids and request logging.

The transport layer — it adapts HTTP to the framework-agnostic primitives in
``twin_observability`` (shared packages know nothing of FastAPI).
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from twin_observability import CORRELATION_ID_HEADER, correlation_scope, get_logger

log = get_logger(__name__)

RequestHandler = Callable[[Request], Awaitable[Response]]

#: Health scrapes would drown the logs; they still get a correlation id.
_UNLOGGED_PATHS = frozenset({"/health"})


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Bind a correlation id for the request and echo it back on the response.

    Honours an inbound ``X-Correlation-ID`` so a trace spans the whole call chain.
    """

    async def dispatch(self, request: Request, call_next: RequestHandler) -> Response:
        inbound = request.headers.get(CORRELATION_ID_HEADER)
        with correlation_scope(inbound) as correlation_id:
            response = await call_next(request)
            response.headers[CORRELATION_ID_HEADER] = correlation_id
            return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log latency + outcome once each request completes."""

    async def dispatch(self, request: Request, call_next: RequestHandler) -> Response:
        path = _route_template(request)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            log.exception("http.request.failed", method=request.method, path=path)
            raise

        if path not in _UNLOGGED_PATHS:
            log.info(
                "http.request",
                method=request.method,
                path=path,
                status=response.status_code,
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
            )
        return response


def _route_template(request: Request) -> str:
    """The matched route pattern (``/threads/{id}``), falling back to the raw path."""
    route = request.scope.get("route")
    template = getattr(route, "path", None)
    return template if isinstance(template, str) else request.url.path
