"""Main FastAPI application entry point with security middleware and routers."""
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import (
    AppException,
    app_exception_handler,
    unhandled_exception_handler,
)
from app.core.logging import logger, setup_logging
from app.db.init_db import create_tables_and_seed


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject security headers on all outbound HTTP responses."""

    async def dispatch(self, request: Request, call_next):
        # Generate and attach request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        response: Response = await call_next(request)

        # Standard enterprise security headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data: https:; "
            "script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
            "connect-src 'self' http://localhost:8000 http://localhost:3000 ws:;"
        )
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown hooks."""
    setup_logging()
    logger.info("Initializing Multi-Agent AI Blog Generation Platform API...")
    try:
        await create_tables_and_seed()
    except Exception as e:
        logger.warning(f"Database bootstrap notice: {e}")
    yield
    logger.info("Shutting down API server...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Middlewares
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health"])
async def health_check():
    """System health check endpoint."""
    return {
        "status": "HEALTHY",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
    }
