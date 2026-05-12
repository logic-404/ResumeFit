from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from app.config import settings
from app.logging import configure_logging, log


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging("DEBUG" if settings.app_env == "development" else "INFO")
    log.info("startup", env=settings.app_env, port=settings.app_port)
    yield
    log.info("shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="ResumeFit",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limit_handler(request, exc):
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "RATE_LIMITED",
                    "message": str(exc.detail),
                    "details": None,
                }
            },
        )

    @app.get("/healthz")
    async def healthz():
        return {"ok": True}

    from app.api import analyse as analyse_api
    from app.api import applications as applications_api
    from app.api import dashboard as dashboard_api
    from app.api import jd_preview as jd_preview_api
    from app.api import profile as profile_api

    app.include_router(profile_api.router, prefix="/api/v1")
    app.include_router(analyse_api.router, prefix="/api/v1")
    app.include_router(applications_api.router, prefix="/api/v1")
    app.include_router(dashboard_api.router, prefix="/api/v1")
    app.include_router(jd_preview_api.router, prefix="/api/v1")

    return app


app = create_app()
