import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import auth, dashboard, drafts, emails, reviews
from app.api.routes import settings as settings_routes
from app.config import CREDENTIALS_DIR, get_settings
from app.db import database
from app.db.schemas import HealthResponse
from app.errors import AppError
from app.services.account_service import get_or_create_settings, get_or_create_user
from app.services.demo_seed import seed_demo_data
from app.utils.security import scrub
from app.workers.email_worker import start_worker, stop_worker

logger = logging.getLogger("email_assistant")


def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
    database.init_db()
    assert database.SessionLocal is not None
    db = database.SessionLocal()
    try:
        user = get_or_create_user(db)
        get_or_create_settings(db, user)
        if get_settings().demo_mode:
            seed_demo_data(db)
        else:
            db.commit()
        logger.info("startup_complete demo_mode=%s", get_settings().demo_mode)
    finally:
        db.close()
    start_worker()
    yield
    await stop_worker()


def create_app() -> FastAPI:
    env = get_settings()
    app = FastAPI(title="Sable", version="1.0.0", lifespan=lifespan)
    origins = {env.frontend_url, "http://localhost:5173", "http://127.0.0.1:5173"}
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router)
    app.include_router(emails.router)
    app.include_router(drafts.router)
    app.include_router(reviews.router)
    app.include_router(settings_routes.router)
    app.include_router(dashboard.router)

    @app.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        database_status = "ok"
        try:
            from sqlalchemy import text

            assert database.SessionLocal is not None
            db = database.SessionLocal()
            db.execute(text("SELECT 1"))
            db.close()
        except Exception:
            logger.exception("health_database_failed")
            database_status = "unavailable"
        return HealthResponse(
            status="ok" if database_status == "ok" else "degraded",
            demo_mode=get_settings().demo_mode,
            database=database_status,
        )

    @app.exception_handler(AppError)
    async def app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        message = "Check the information you entered and try again."
        errors = exc.errors()
        if errors:
            raw = str(errors[0].get("msg") or message)
            message = raw.removeprefix("Value error, ")
        return JSONResponse(status_code=422, content={"detail": message})

    @app.exception_handler(Exception)
    async def unhandled(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error detail=%s", scrub(str(exc)))
        return JSONResponse(status_code=500, content={"detail": "Something went wrong. Please try again."})

    return app


app = create_app()

# Imported so tests and scripts can open a session the same way routes do.
__all__ = ["app"]
