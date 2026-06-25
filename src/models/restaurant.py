from typing import List, Optional
from pydantic import BaseModel, Field

class Restaurant(BaseModel):
    id: str
    name: str
    location: str
    cuisines: List[str] = Field(default_factory=list)
    cost_for_two: int
    rating: float
    votes: int = 0
    rest_type: Optional[str] = None
    budget_tier: str  # "low" | "medium" | "high"
