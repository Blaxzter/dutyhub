# pyright: reportPrivateUsage=false, reportUnusedFunction=false
"""Tests for app.core.errors problem+json handlers and helpers."""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core import errors
from app.core.config import settings
from app.core.errors import (
    PROBLEM_JSON_MEDIA_TYPE,
    URN_PREFIX,
    _infer_problem_type,
    _parse_problem_detail,
    _slugify_resource,
    http_exception_handler,
    problem_detail,
    raise_problem,
    starlette_http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)


def _fake_request(path: str = "/api/v1/thing") -> Request:
    scope: dict[str, Any] = {
        "type": "http",
        "method": "GET",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [],
    }
    return Request(scope)


def _body(response: JSONResponse) -> dict[str, Any]:
    return json.loads(bytes(response.body))


class TestSlugifyResource:
    def test_slugifies_mixed_case(self):
        assert _slugify_resource("Event Manager") == "event_manager"

    def test_strips_punctuation(self):
        assert _slugify_resource("User--Profile!!") == "user_profile"

    def test_empty_falls_back(self):
        assert _slugify_resource("!!!") == "resource"


class TestInferProblemType:
    def test_404_with_resource_detail(self):
        assert (
            _infer_problem_type(404, "Event manager not found")
            == f"{URN_PREFIX}event_manager.not_found"
        )

    def test_404_without_detail(self):
        assert _infer_problem_type(404, None) == f"{URN_PREFIX}not_found"

    def test_404_unparseable_detail(self):
        assert _infer_problem_type(404, "something else") == f"{URN_PREFIX}not_found"

    @pytest.mark.parametrize(
        "status,suffix",
        [
            (401, "unauthorized"),
            (403, "forbidden"),
            (422, "validation_error"),
            (429, "rate_limited"),
            (400, "bad_request"),
            (500, "internal_server_error"),
            (503, "internal_server_error"),
        ],
    )
    def test_status_mapping(self, status: int, suffix: str):
        assert _infer_problem_type(status, None) == f"{URN_PREFIX}{suffix}"

    def test_unmapped_status_returns_none(self):
        assert _infer_problem_type(418, None) is None


class TestParseProblemDetail:
    def test_string_detail(self):
        detail, type_url, code = _parse_problem_detail("plain message")
        assert detail == "plain message"
        assert type_url is None
        assert code is None

    def test_dict_with_code_infers_type(self):
        detail, type_url, code = _parse_problem_detail(
            {"code": "user.not_found", "detail": "msg"}
        )
        assert detail == "msg"
        assert type_url == "urn:problem:user.not_found"
        assert code == "user.not_found"

    def test_dict_with_explicit_type(self):
        detail, type_url, code = _parse_problem_detail(
            {"type": "urn:problem:custom", "code": "x", "detail": "d"}
        )
        assert type_url == "urn:problem:custom"
        assert code == "x"
        assert detail == "d"

    def test_dict_with_message_fallback(self):
        detail, _, _ = _parse_problem_detail({"message": "fallback"})
        assert detail == "fallback"

    def test_dict_without_code_or_type(self):
        detail, type_url, code = _parse_problem_detail({"detail": "x"})
        assert detail == "x"
        assert type_url is None
        assert code is None

    def test_none_detail(self):
        detail, type_url, code = _parse_problem_detail(None)
        assert detail is None
        assert type_url is None
        assert code is None


class TestProblemDetailHelper:
    def test_includes_detail_when_provided(self):
        payload = problem_detail(code="x.y", detail="oops")
        assert payload == {
            "code": "x.y",
            "type": "urn:problem:x.y",
            "detail": "oops",
        }

    def test_custom_type_url(self):
        payload = problem_detail(code="x", type_url="https://example.com/e")
        assert payload["type"] == "https://example.com/e"
        assert "detail" not in payload


class TestRaiseProblem:
    def test_raises_http_exception(self):
        with pytest.raises(HTTPException) as exc_info:
            raise_problem(404, code="user.not_found", detail="missing")
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == {
            "code": "user.not_found",
            "type": "urn:problem:user.not_found",
            "detail": "missing",
        }

    def test_includes_headers(self):
        with pytest.raises(HTTPException) as exc_info:
            raise_problem(
                401,
                code="unauthorized",
                headers={"WWW-Authenticate": "Bearer"},
            )
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


class TestHttpExceptionHandler:
    def test_string_detail(self):
        exc = HTTPException(status_code=404, detail="User not found")
        response = http_exception_handler(_fake_request("/api/v1/users/1"), exc)
        body = _body(response)
        assert response.status_code == 404
        assert response.media_type == PROBLEM_JSON_MEDIA_TYPE
        assert body["status"] == 404
        assert body["detail"] == "User not found"
        assert body["type"] == f"{URN_PREFIX}user.not_found"
        assert body["instance"] == "/api/v1/users/1"

    def test_dict_detail_with_code(self):
        exc = HTTPException(
            status_code=400,
            detail={"code": "bad.input", "detail": "nope"},
        )
        response = http_exception_handler(_fake_request(), exc)
        body = _body(response)
        assert body["code"] == "bad.input"
        assert body["type"] == "urn:problem:bad.input"

    def test_blank_detail_uses_status_title(self):
        exc = HTTPException(status_code=401, detail="")
        response = http_exception_handler(_fake_request(), exc)
        body = _body(response)
        assert body["detail"] == "Unauthorized"
        assert body["type"] == f"{URN_PREFIX}unauthorized"

    def test_preserves_headers(self):
        exc = HTTPException(
            status_code=401,
            detail="Nope",
            headers={"WWW-Authenticate": "Bearer"},
        )
        response = http_exception_handler(_fake_request(), exc)
        assert response.headers.get("www-authenticate") == "Bearer"


class TestStarletteHttpExceptionHandler:
    def test_basic(self):
        exc = StarletteHTTPException(status_code=403, detail="nope")
        response = starlette_http_exception_handler(_fake_request(), exc)
        body = _body(response)
        assert body["status"] == 403
        assert body["detail"] == "nope"
        assert body["type"] == f"{URN_PREFIX}forbidden"

    def test_blank_detail(self):
        exc = StarletteHTTPException(status_code=500, detail="")
        response = starlette_http_exception_handler(_fake_request(), exc)
        body = _body(response)
        assert body["detail"] == "Internal Server Error"


class TestValidationExceptionHandler:
    def test_normalizes_errors(self):
        errs = [
            {
                "loc": ("body", "name"),
                "msg": "field required",
                "type": "missing",
            },
            {
                "loc": ("body", 0, "value"),
                "msg": "wrong",
                "type": "value_error",
            },
        ]
        exc = RequestValidationError(errs)
        response = validation_exception_handler(_fake_request(), exc)
        body = _body(response)
        assert response.status_code == 422
        assert body["type"] == f"{URN_PREFIX}validation_error"
        assert body["title"] == "Validation Error"
        assert len(body["errors"]) == 2
        assert body["errors"][0]["loc"] == ["body", "name"]
        assert body["errors"][1]["loc"] == ["body", 0, "value"]


class TestUnhandledExceptionHandler:
    def test_local_env_shows_exception_detail(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(settings, "ENVIRONMENT", "local")
        response = unhandled_exception_handler(_fake_request(), ValueError("boom"))
        body = _body(response)
        assert response.status_code == 500
        assert "ValueError" in body["detail"]
        assert "boom" in body["detail"]
        assert body["type"] == f"{URN_PREFIX}internal_server_error"

    def test_non_local_env_hides_detail(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        response = unhandled_exception_handler(_fake_request(), ValueError("boom"))
        body = _body(response)
        assert body["detail"] == "Unexpected error occurred."
        assert "boom" not in body["detail"]


@pytest.mark.asyncio
class TestHandlersIntegration:
    """Exercise handlers through a real FastAPI app to cover the async path."""

    async def test_app_wide_problem_details(self):
        app = FastAPI()
        app.add_exception_handler(HTTPException, errors.http_exception_handler)  # type: ignore[arg-type]
        app.add_exception_handler(
            StarletteHTTPException,
            errors.starlette_http_exception_handler,  # type: ignore[arg-type]
        )
        app.add_exception_handler(
            RequestValidationError,
            errors.validation_exception_handler,  # type: ignore[arg-type]
        )

        @app.get("/raise")
        async def raise_route():
            raise HTTPException(status_code=404, detail="Thing not found")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/raise")

        assert r.status_code == 404
        assert r.headers["content-type"].startswith(PROBLEM_JSON_MEDIA_TYPE)
        body = r.json()
        assert body["type"] == f"{URN_PREFIX}thing.not_found"
        assert body["instance"] == "/raise"
