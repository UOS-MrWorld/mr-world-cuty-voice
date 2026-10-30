import logging
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("voice")

STATUS_CODES = {
    400: "INVALID_INPUT",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "RESOURCE_NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    500: "INTERNAL_SERVER_ERROR",
    503: "VOICE_SERVICE_UNAVAILABLE",
}


class ApiError(Exception):

    def __init__(self, status: int, message: str, code: str | None = None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.code = code or STATUS_CODES.get(status, "INTERNAL_SERVER_ERROR")


def _body(request: Request, status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={
        "status": status,
        "code": code,
        "message": message,
        "path": request.url.path,
        "timestamp": datetime.now().replace(microsecond=0).isoformat(),
    })


def register(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error(request: Request, exc: ApiError):
        return _body(request, exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        fields = ", ".join(".".join(str(p) for p in e["loc"] if p != "body") for e in exc.errors())
        return _body(request, 400, "INVALID_INPUT", f"요청 값이 올바르지 않습니다. ({fields})")

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        message = exc.detail if isinstance(exc.detail, str) else "요청을 처리할 수 없습니다."
        if exc.status_code == 404:
            message = "요청한 경로를 찾을 수 없습니다."
        return _body(request, exc.status_code, STATUS_CODES.get(exc.status_code, "INTERNAL_SERVER_ERROR"), message)

    @app.middleware("http")
    async def unknown_error(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception:
            log.exception("처리 중 예상하지 못한 오류")
            return _body(request, 500, "INTERNAL_SERVER_ERROR", "음성 처리 중 서버 오류가 발생했습니다.")
