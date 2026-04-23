"""RFC 7807 problem details middleware.

Converts FastAPI validation errors and HTTP exceptions to the
``application/problem+json`` format so all error responses are consistent.
Error messages and titles use German for user-facing detail text.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


def _problem_response(
    status: int,
    type_uri: str,
    title: str,
    detail: str,
    instance: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "type": f"urn:solalex:{type_uri}",
            "title": title,
            "status": status,
            "detail": detail,
            "instance": instance,
        },
        headers={"Content-Type": "application/problem+json"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach RFC-7807-compliant exception handlers to *app*."""

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = exc.errors()
        # Build a human-readable German summary of the first error.
        if errors:
            first = errors[0]
            loc = " → ".join(str(p) for p in first.get("loc", []))
            msg = first.get("msg", "Ungültiger Wert")
            detail = f"Feld '{loc}': {msg}. Bitte Eingaben prüfen und korrigieren."
        else:
            detail = "Ungültige Anfrage — bitte Eingaben prüfen."
        return _problem_response(
            status=422,
            type_uri="validation-error",
            title="Validierungsfehler",
            detail=detail,
            instance=str(request.url.path),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        status = exc.status_code
        type_map: dict[int, tuple[str, str]] = {
            400: ("bad-request", "Ungültige Anfrage"),
            404: ("not-found", "Nicht gefunden"),
            409: ("conflict", "Konflikt"),
            412: ("precondition-failed", "Vorbedingung nicht erfüllt"),
            422: ("validation-error", "Validierungsfehler"),
            500: ("internal-error", "Interner Fehler"),
            502: ("upstream-error", "Upstream-Fehler"),
            503: ("service-unavailable", "Dienst nicht verfügbar"),
            504: ("gateway-timeout", "Gateway-Timeout"),
        }
        type_uri, title = type_map.get(status, ("error", "Fehler"))
        detail = str(exc.detail) if exc.detail else title
        return _problem_response(
            status=status,
            type_uri=type_uri,
            title=title,
            detail=detail,
            instance=str(request.url.path),
        )
