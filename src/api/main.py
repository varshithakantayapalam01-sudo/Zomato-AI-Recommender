"""
FastAPI application factory for the Restaurant Recommendation API.

Responsibilities:
- Configure CORS middleware for frontend consumption.
- Load the dataset once during the lifespan in a background thread so the
  server starts accepting requests (and passing health checks) immediately.
- Mount the v1 API router.
- Serve the frontend SPA via StaticFiles.
"""

import logging
import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.routes import router as v1_router, set_dependencies
from src.config import settings
from src.data.repository import RestaurantRepository
from src.services.recommendation import RecommendationService

logger = logging.getLogger(__name__)

# Resolve the absolute path to the frontend directory
_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "ui", "frontend")
_FRONTEND_DIR = os.path.abspath(_FRONTEND_DIR)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """
    Startup / shutdown lifecycle.

    Dataset loading is offloaded to a daemon background thread so that
    uvicorn begins serving immediately. The health endpoint returns
    ``status: "starting"`` while the data is still loading, and transitions
    to ``status: "healthy"`` once the thread completes.

    This prevents Railway's health-check from timing out during the
    first-boot HuggingFace dataset download (which can take 60-120 s).
    """
    def _load_data() -> None:
        logger.info("Background thread: loading dataset...")
        try:
            repo = RestaurantRepository.load()
            svc = RecommendationService()
            set_dependencies(repo, svc)
            logger.info(
                "Background thread: dataset ready — %d restaurants, "
                "%d locations, %d cuisines",
                len(repo.get_all()),
                len(repo.get_locations()),
                len(repo.get_cuisines()),
            )
        except Exception:
            logger.exception("Background thread: failed to load dataset")

    thread = threading.Thread(target=_load_data, daemon=True, name="dataset-loader")
    thread.start()
    logger.info("Startup: dataset loading started in background thread.")

    yield

    logger.info("Shutting down.")


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    application = FastAPI(
        title="AI Restaurant Recommender API",
        description="Groq LLM-powered restaurant recommendation service backed by the Zomato dataset.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # ── CORS ────────────────────────────────────
    # Origins are read from the ALLOWED_ORIGINS env var (comma-separated).
    # Set it on Railway to include your Vercel domain(s).
    # Defaults to localhost origins for local development.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_allowed_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── API Routers ─────────────────────────────
    application.include_router(v1_router)

    # ── Static Frontend Assets ──────────────────
    if os.path.isdir(_FRONTEND_DIR):
        application.mount("/css", StaticFiles(directory=os.path.join(_FRONTEND_DIR, "css")), name="css")
        application.mount("/js", StaticFiles(directory=os.path.join(_FRONTEND_DIR, "js")), name="js")

        @application.get("/config.js", include_in_schema=False)
        async def serve_config():
            """Serve the runtime API URL config used by app.js."""
            return FileResponse(
                os.path.join(_FRONTEND_DIR, "config.js"),
                media_type="application/javascript",
            )

        @application.get("/", include_in_schema=False)
        async def serve_frontend():
            """Serve the SPA index.html at the root path."""
            return FileResponse(os.path.join(_FRONTEND_DIR, "index.html"))

    return application


app = create_app()

