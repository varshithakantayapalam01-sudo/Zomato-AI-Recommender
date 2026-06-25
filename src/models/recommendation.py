from typing import List, Optional
from pydantic import BaseModel, Field

class Recommendation(BaseModel):
    rank: int
    name: str
    cuisine: str  # Joined cuisine string for display
    rating: float
    estimated_cost: int  # cost_for_two
    explanation: str  # LLM-generated rationale

class ResponseMetadata(BaseModel):
    candidates_considered: int
    filters_applied: dict
    model: str
    fallback_applied: bool = False

class RecommendationResponse(BaseModel):
    summary: Optional[str] = None
    recommendations: List[Recommendation] = Field(default_factory=list)
    metadata: ResponseMetadata
