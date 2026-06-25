from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator

class UserPreferences(BaseModel):
    location: str
    budget: Optional[str] = None  # "low" | "medium" | "high"
    min_budget: Optional[int] = None
    max_budget: Optional[int] = None
    cuisine: Optional[str] = None
    min_rating: float = Field(default=0.0, ge=0.0, le=5.0)
    additional: Optional[str] = None

    @field_validator("location")
    @classmethod
    def validate_location(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Location must not be empty.")
        return v

    @field_validator("budget")
    @classmethod
    def validate_budget(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip().lower()
        valid_budgets = {"low", "medium", "high"}
        if v not in valid_budgets:
            raise ValueError(f"Budget must be one of {valid_budgets}")
        return v

    @model_validator(mode="after")
    def validate_budget_range(self) -> "UserPreferences":
        if self.min_budget is not None and self.max_budget is not None:
            if self.min_budget > self.max_budget:
                raise ValueError("min_budget must be less than or equal to max_budget")
        return self

    @field_validator("cuisine")
    @classmethod
    def normalize_cuisine(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().lower()
            if not v:
                return None
        return v

    @field_validator("additional")
    @classmethod
    def normalize_additional(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v
