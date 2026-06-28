from typing import List, Optional
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

    # CORS — comma-separated list of allowed origins.
    # Defaults cover local dev. In production (Railway), set this env var to
    # include your Vercel domain(s), e.g.:
    #   ALLOWED_ORIGINS=https://zomato-ai-recommender.vercel.app,https://yourdomain.com
    ALLOWED_ORIGINS: str = (
        "http://localhost:8000,"
        "http://127.0.0.1:8000,"
        "http://localhost:3000,"
        "http://127.0.0.1:3000,"
        "https://zomato-ai-recommender-u7jj.vercel.app,"
        "https://zomato-ai-recommender.vercel.app,"
        "https://zomato-ai-recommender-three.vercel.app"
    )

    def get_allowed_origins(self) -> List[str]:
        """Parse the comma-separated ALLOWED_ORIGINS string into a list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

