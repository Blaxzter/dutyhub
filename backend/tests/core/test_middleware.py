# pyright: reportPrivateUsage=false, reportUnusedFunction=false
"""Tests for RequestLoggingMiddleware."""

from __future__ import annotations

import logging
from typing import Any

import pytest
from fastapi import FastAPI, HTTPException, Request
from httpx import ASGITransport, AsyncClient

from app.core.middleware import IGNORE_PATHS, RequestLoggingMiddleware


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/thing")
    async def thing():
        return {"ok": True}

    @app.get("/boom")
    async def boom():
        raise RuntimeError("kaboom")

    @app.get("/notfound")
    async def notfound():
        raise HTTPException(status_code=404, detail="nope")

    @app.get("/api/v1/health")
    async def health():
        return {"ok": True}

    return app


class TestRequestLoggingMiddleware:
    async def test_logs_success(self, caplog: pytest.LogCaptureFixture):
        app = _build_app()
        transport = ASGITransport(app=app)
        with caplog.at_level(logging.INFO, logger="request"):
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                r = await c.get("/thing")
        assert r.status_code == 200
        assert any("/thing" in rec.message for rec in caplog.records)

    async def test_skips_ignored_paths(self, caplog: pytest.LogCaptureFixture):
        app = _build_app()
        transport = ASGITransport(app=app)
        with caplog.at_level(logging.INFO, logger="request"):
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                r = await c.get("/api/v1/health")
        assert r.status_code == 200
        assert not any("/api/v1/health" in rec.message for rec in caplog.records)

    async def test_skips_options(self, caplog: pytest.LogCaptureFixture):
        app = _build_app()
        transport = ASGITransport(app=app)
        with caplog.at_level(logging.INFO, logger="request"):
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                r = await c.request("OPTIONS", "/thing")
        # Not logged
        assert not any("/thing" in rec.message for rec in caplog.records)
        assert r.status_code in (200, 405)

    async def test_logs_client_error_status(self, caplog: pytest.LogCaptureFixture):
        app = _build_app()
        transport = ASGITransport(app=app)
        with caplog.at_level(logging.INFO, logger="request"):
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                r = await c.get("/notfound")
        assert r.status_code == 404
        assert any("/notfound" in rec.message for rec in caplog.records)

    async def test_logs_exception_path_when_middleware_reraises(
        self, caplog: pytest.LogCaptureFixture
    ):
        """Call middleware.dispatch directly so we hit the except branch."""
        mw = RequestLoggingMiddleware(app=_build_app())

        scope: dict[str, Any] = {
            "type": "http",
            "method": "GET",
            "path": "/boom",
            "raw_path": b"/boom",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)

        async def call_next(_req: Request) -> Any:
            raise RuntimeError("kaboom")

        with caplog.at_level(logging.ERROR, logger="request"):
            with pytest.raises(RuntimeError, match="kaboom"):
                await mw.dispatch(request, call_next)  # type: ignore[arg-type]

        assert any(
            "/boom" in rec.message and rec.levelno >= logging.ERROR
            for rec in caplog.records
        )

    async def test_debug_level_logs_traceback(
        self, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
    ):
        """When request_logger is at DEBUG, the traceback is also logged."""
        from app.core import middleware as mw_module

        mw = RequestLoggingMiddleware(app=_build_app())
        monkeypatch.setattr(mw_module.request_logger, "level", logging.DEBUG)

        scope: dict[str, Any] = {
            "type": "http",
            "method": "GET",
            "path": "/boom",
            "raw_path": b"/boom",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)

        async def call_next(_req: Request) -> Any:
            raise RuntimeError("kaboom")

        with caplog.at_level(logging.DEBUG, logger="request"):
            with pytest.raises(RuntimeError):
                await mw.dispatch(request, call_next)  # type: ignore[arg-type]

        assert any("Traceback" in rec.message for rec in caplog.records)

    def test_colored_method_returns_ansi(self):
        mw = RequestLoggingMiddleware(app=_build_app())
        out = mw._get_colored_method("GET")
        assert "GET" in out
        assert "\033[" in out

    def test_colored_method_default_for_unknown(self):
        mw = RequestLoggingMiddleware(app=_build_app())
        out = mw._get_colored_method("FOO")
        assert "FOO" in out

    @pytest.mark.parametrize(
        "code",
        [200, 302, 404, 500],
    )
    def test_colored_status_covers_ranges(self, code: int):
        mw = RequestLoggingMiddleware(app=_build_app())
        out = mw._get_colored_status(code)
        assert str(code) in out

    def test_colored_status_unknown_phrase(self):
        mw = RequestLoggingMiddleware(app=_build_app())
        out = mw._get_colored_status(799)
        assert "799" in out
        assert "Unknown" in out

    def test_ignore_paths_constant(self):
        assert "/api/v1/health" in IGNORE_PATHS
