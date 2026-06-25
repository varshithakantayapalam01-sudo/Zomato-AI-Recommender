"""
FastAPI application factory for the Restaurant Recommendation API.

Responsibilities:
- Configure CORS middleware for frontend consumption.
- Load the dataset once during the lifespan (not per-request).
- Mount the v1 API router.
- Serve the frontend SPA via StaticFiles.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.routes import router as v1_router, set_dependencies
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

    On startup:
      1. Load the RestaurantRepository (downloads + caches dataset on first run).
      2. Create a shared RecommendationService instance.
      3. Inject both into the route module.
    """
    logger.info("Starting up: loading dataset...")
    repo = RestaurantRepository.load()
    svc = RecommendationService()
    set_dependencies(repo, svc)
    logger.info(
        "Dataset loaded: %d restaurants, %d locations, %d cuisines",
        len(repo.get_all()),
        len(repo.get_locations()),
        len(repo.get_cuisines()),
    )
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
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
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

        @application.get("/", include_in_schema=False)
        async def serve_frontend():
            """Serve the SPA index.html at the root path."""
            return FileResponse(os.path.join(_FRONTEND_DIR, "index.html"))

    return application


app = create_app()

