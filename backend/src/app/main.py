import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from uvicorn import Server, Config

from logger import setup_logging
from config import CORS_ALLOWED_ORIGINS
from src.app.modules import api_router
from src.app.observability import RequestLoggingMiddleware, get_request_id, get_request_payload, log_error, log_exception, log_info, log_warning
from src.app.services import audio_cleanup_runner, beeline_sync_runner, daily_report_runner, transcription_job_runner

setup_logging()

logger = logging.getLogger("app")

@asynccontextmanager
async def lifespan(_: FastAPI):
    log_info(logger, "app.lifespan.start")
    await transcription_job_runner.start()
    await beeline_sync_runner.start()
    await daily_report_runner.start()
    await audio_cleanup_runner.start()
    try: yield
    finally:
        await audio_cleanup_runner.stop()
        await daily_report_runner.stop()
        await beeline_sync_runner.stop()
        await transcription_job_runner.stop()
        log_info(logger, "app.lifespan.stop")


app = FastAPI(title="Call Analyzer Api", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(api_router)


def build_exception_fields(request: Request) -> dict:
    return {
        "request_id": get_request_id(request.scope),
        "method": request.method,
        "path": request.url.path,
        "query_string": request.url.query,
        "request_payload": get_request_payload(request.scope),
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    fields = build_exception_fields(request)
    fields["status_code"] = exc.status_code
    fields["detail"] = exc.detail
    if exc.status_code >= 500: log_error(logger, "http.exception", **fields)
    else: log_warning(logger, "http.exception", **fields)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = build_exception_fields(request)
    fields["status_code"] = 422
    fields["errors"] = exc.errors()
    log_warning(logger, "http.validation_error", **fields)
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(exc.errors())})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    fields = build_exception_fields(request)
    fields["status_code"] = 500
    fields["exception_type"] = type(exc).__name__
    fields["detail"] = str(exc)
    log_exception(logger, "http.unhandled_exception", **fields)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

@app.get("/")
async def read_root() -> dict[str, str]:
    log_info(logger, "app.read_root")
    return {"message": f"{app.title} version={app.version} is running"}

@app.get("/health")
async def healthcheck() -> dict[str, str]:
    log_info(logger, "app.healthcheck")
    return {"status": "ok"}

async def run_app():
    log_info(logger, "app.server.start", reload=False)
    server = Server(Config(app, host="0.0.0.0", reload=False, log_config=None))
    await server.serve()
    log_warning(logger, "app.server.stop")
