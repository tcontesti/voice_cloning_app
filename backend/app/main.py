from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

from app.api import audit as audit_router
from app.api import auth as auth_router
from app.api import consent as consent_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

settings = get_settings()
configure_logging(settings.app_log_level)
log = get_logger("app.main")

REQUESTS = Counter("vcapp_requests_total", "Total HTTP requests", ["path"])


@asynccontextmanager
async def lifespan(_: FastAPI):
    log.info("app.start", env=settings.app_env)
    yield
    log.info("app.stop")


app = FastAPI(
    title="Voice Cloning App",
    version="0.1.0",
    description="Clinical voice cloning — Hospital Son Llatzer",
    lifespan=lifespan,
)

if settings.cors_origins_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


app.include_router(auth_router.router)
app.include_router(consent_router.router)
app.include_router(audit_router.router)


@app.get("/health")
async def health() -> dict[str, Any]:
    REQUESTS.labels(path="/health").inc()
    return {"status": "ok", "env": settings.app_env, "version": app.version}


@app.get("/metrics")
async def metrics() -> PlainTextResponse:
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
