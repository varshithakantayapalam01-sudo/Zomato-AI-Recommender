from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Dataset config
    HF_DATASET_NAME: str = "ManikaSaini/zomato-restaurant-recommendation"
    DATA_CACHE_PATH: str = "data/restaurants.parquet"
    
    # Budget config
    BUDGET_THRESHOLDS_LOW_MAX: int = 500
    BUDGET_THRESHOLDS_MEDIUM_MAX: int = 1500
    
    # Filtering / Ranking config
    MAX_CANDIDATES_FOR_LLM: int = 20
    TOP_K_RECOMMENDATIONS: int = 5
    
    # Groq API config
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_TEMPERATURE: float = 0.3
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
