"""
Pydantic request/response schemas for the Recommendation API.

These models decouple the API contract from the internal domain models
(src.models.*), allowing the API surface to evolve independently.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
#  Request schemas
# ──────────────────────────────────────────────

class RecommendRequest(BaseModel):
    """Body for POST /api/v1/recommend."""
    location: str = Field(..., min_length=1, description="City or locality name")
    budget: Optional[str] = Field(None, description="Budget tier: low | medium | high")
    min_budget: Optional[int] = Field(None, ge=0, description="Minimum budget for two")
    max_budget: Optional[int] = Field(None, ge=0, description="Maximum budget for two")
    cuisine: Optional[str] = Field(None, description="Optional preferred cuisine")
    min_rating: float = Field(default=0.0, ge=0.0, le=5.0, description="Minimum restaurant rating")
    additional: Optional[str] = Field(None, description="Free-text soft preferences (e.g. family-friendly)")


# ──────────────────────────────────────────────
#  Response schemas
# ──────────────────────────────────────────────

class RecommendationItem(BaseModel):
    """A single restaurant recommendation in the API response."""
    rank: int
    name: str
    cuisine: str
    rating: float
    estimated_cost: int
    explanation: str


class RecommendMetadata(BaseModel):
    """Metadata about the recommendation request."""
    candidates_considered: int
    filters_applied: Dict[str, Any]
    model: str
    fallback_applied: bool = False


class RecommendResponse(BaseModel):
    """Full response for POST /api/v1/recommend."""
    summary: Optional[str] = None
    recommendations: List[RecommendationItem] = Field(default_factory=list)
    metadata: RecommendMetadata


class LocationsResponse(BaseModel):
    """Response for GET /api/v1/locations."""
    locations: List[str]


class CuisinesResponse(BaseModel):
    """Response for GET /api/v1/cuisines."""
    cuisines: List[str]


class HealthResponse(BaseModel):
    """Response for GET /api/v1/health."""
    status: str
    dataset_loaded: bool
    record_count: int


class ErrorDetail(BaseModel):
    """Structured error detail returned in error responses."""
    message: str
    field: Optional[str] = None
    suggestions: Optional[List[str]] = None


class ErrorResponse(BaseModel):
    """Standard error response wrapper."""
    error: str
    details: List[ErrorDetail] = Field(default_factory=list)
