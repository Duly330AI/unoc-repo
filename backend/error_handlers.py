"""Global error response wrapper (TASK-043)."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):  # type: ignore
        # Let FastAPI built-ins handle HTTPException separately; here only unexpected
        from fastapi import HTTPException

        if isinstance(exc, HTTPException):  # pragma: no cover - fallback
            raise exc
        code = "INTERNAL_ERROR"
        return JSONResponse(
            status_code=500,
            content={
                "code": code,
                "message": f"{type(exc).__name__}: {exc}",
                "detail": str(exc),
            },
        )
