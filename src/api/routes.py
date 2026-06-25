"""
Route handlers for the Recommendation API (v1).

All routes are mounted under the ``/api/v1`` prefix by the FastAPI
application factory in ``main.py``.
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError as PydanticValidationError

from src.api.schemas import (
    CuisinesResponse,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    LocationsResponse,
    RecommendationItem,
    RecommendMetadata,
    RecommendRequest,
    RecommendResponse,
)
from src.data.repository import RestaurantRepository
from src.models.preferences import UserPreferences
from src.services.filter import LocationValidationError
from src.services.recommendation import RecommendationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["v1"])

# ──────────────────────────────────────────────
#  Module-level state (populated by lifespan)
# ──────────────────────────────────────────────

_repo: Optional[RestaurantRepository] = None
_recommendation_service: Optional[RecommendationService] = None


def set_dependencies(repo: RestaurantRepository, svc: RecommendationService) -> None:
    """Called once during app startup to inject shared instances."""
    global _repo, _recommendation_service
    _repo = repo
    _recommendation_service = svc


def _get_repo() -> RestaurantRepository:
    if _repo is None:
        raise HTTPException(status_code=503, detail="Dataset not loaded yet")
    return _repo


def _get_service() -> RecommendationService:
    if _recommendation_service is None:
        raise HTTPException(status_code=503, detail="Recommendation service not ready")
    return _recommendation_service


# ──────────────────────────────────────────────
#  GET /api/v1/health
# ──────────────────────────────────────────────

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns the service status and dataset information.",
)
def health() -> HealthResponse:
    repo = _repo
    if repo is None:
        return HealthResponse(status="starting", dataset_loaded=False, record_count=0)
    return HealthResponse(
        status="healthy",
        dataset_loaded=True,
        record_count=len(repo.get_all()),
    )


# ──────────────────────────────────────────────
#  GET /api/v1/locations
# ──────────────────────────────────────────────

@router.get(
    "/locations",
    response_model=LocationsResponse,
    summary="List available locations",
    description="Returns all distinct restaurant locations from the dataset.",
)
def list_locations() -> LocationsResponse:
    repo = _get_repo()
    return LocationsResponse(locations=repo.get_locations())


# ──────────────────────────────────────────────
#  GET /api/v1/cuisines
# ──────────────────────────────────────────────

@router.get(
    "/cuisines",
    response_model=CuisinesResponse,
    summary="List available cuisines",
    description="Returns all distinct cuisines extracted from the dataset.",
)
def list_cuisines() -> CuisinesResponse:
    repo = _get_repo()
    return CuisinesResponse(cuisines=repo.get_cuisines())


# ──────────────────────────────────────────────
#  POST /api/v1/recommend
# ──────────────────────────────────────────────

@router.post(
    "/recommend",
    response_model=RecommendResponse,
    responses={
        422: {"model": ErrorResponse, "description": "Validation error"},
        503: {"model": ErrorResponse, "description": "Service unavailable (LLM failure with fallback)"},
    },
    summary="Get restaurant recommendations",
    description="Accepts user preferences, filters the dataset, invokes the LLM, and returns ranked recommendations.",
)
def recommend(body: RecommendRequest) -> Any:
    svc = _get_service()

    # Convert API schema → domain model
    try:
        prefs = UserPreferences(
            location=body.location,
            budget=body.budget,
            min_budget=body.min_budget,
            max_budget=body.max_budget,
            cuisine=body.cuisine,
            min_rating=body.min_rating,
            additional=body.additional,
        )
    except PydanticValidationError as e:
        details = []
        for err in e.errors():
            loc = err.get("loc", ())
            field_name = str(loc[-1]) if loc else "preferences"
            details.append(ErrorDetail(message=err["msg"], field=field_name))
        raise HTTPException(status_code=422, detail=ErrorResponse(error="Validation error", details=details).model_dump())

    # Run the recommendation pipeline
    try:
        result = svc.recommend(prefs)
    except LocationValidationError as e:
        logger.warning("Location validation failed: %s", e)
        details = [ErrorDetail(message=str(e), field="location", suggestions=e.suggestions)]
        raise HTTPException(
            status_code=422,
            detail=ErrorResponse(error="Invalid location", details=details).model_dump(),
        )
    except Exception as e:
        logger.exception("Unexpected error during recommendation")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Internal server error",
                details=[ErrorDetail(message=str(e))],
            ).model_dump(),
        )

    # Map internal RecommendationResponse → API RecommendResponse
    recommendations = [
        RecommendationItem(
            rank=r.rank,
            name=r.name,
            cuisine=r.cuisine,
            rating=r.rating,
            estimated_cost=r.estimated_cost,
            explanation=r.explanation,
        )
        for r in result.recommendations
    ]

    metadata = RecommendMetadata(
        candidates_considered=result.metadata.candidates_considered,
        filters_applied=result.metadata.filters_applied,
        model=result.metadata.model,
        fallback_applied=result.metadata.fallback_applied,
    )

    return RecommendResponse(
        summary=result.summary,
        recommendations=recommendations,
        metadata=metadata,
    )
