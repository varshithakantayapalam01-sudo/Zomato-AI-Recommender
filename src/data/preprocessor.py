import pandas as pd
from typing import List
from src.config import settings

class DataPreprocessor:
    @staticmethod
    def parse_rating(rate_val) -> float:
        """
        Parses rating string (e.g. '4.1/5', 'NEW', '-') to float.
        """
        if pd.isna(rate_val):
            return 0.0
        rate_str = str(rate_val).strip()
        if rate_str in ("NEW", "-", ""):
            return 0.0
        if "/" in rate_str:
            rate_str = rate_str.split("/")[0].strip()
        try:
            return float(rate_str)
        except ValueError:
            return 0.0

    @staticmethod
    def parse_cost(cost_val) -> int:
        """
        Parses approximate cost string (e.g. '800', '1,200') to integer.
        """
        if pd.isna(cost_val):
            return 0
        cost_str = str(cost_val).replace(",", "").strip()
        try:
            return int(cost_str)
        except ValueError:
            return 0

    @staticmethod
    def parse_cuisines(cuisines_val) -> List[str]:
        """
        Splits comma-separated cuisines string into a clean list of strings.
        """
        if pd.isna(cuisines_val):
            return []
        cuisines_str = str(cuisines_val).strip()
        return [c.strip() for c in cuisines_str.split(",") if c.strip()]

    @staticmethod
    def get_budget_tier(cost: int) -> str:
        """
        Derives budget tier (low, medium, high) based on configured thresholds.
        """
        if cost <= settings.BUDGET_THRESHOLDS_LOW_MAX:
            return "low"
        elif cost <= settings.BUDGET_THRESHOLDS_MEDIUM_MAX:
            return "medium"
        else:
            return "high"

    @staticmethod
    def preprocess(df: pd.DataFrame) -> pd.DataFrame:
        """
        Processes raw Zomato dataframe into the canonical schema.
        """
        # Create a copy to avoid mutating original
        df = df.copy()

        # Fill missing names/locations with empty to drop them cleanly
        df["name"] = df["name"].fillna("").astype(str).str.strip()
        df["location"] = df["location"].fillna("").astype(str).str.strip()

        # Drop rows with empty name or location
        df = df[(df["name"] != "") & (df["location"] != "")]

        # Parse ratings, costs, and cuisines
        df["rating"] = df["rate"].apply(DataPreprocessor.parse_rating)
        df["cost_for_two"] = df["approx_cost(for two people)"].apply(DataPreprocessor.parse_cost)
        df["cuisines"] = df["cuisines"].apply(DataPreprocessor.parse_cuisines)
        
        # Coerce votes to integer
        df["votes"] = pd.to_numeric(df["votes"], errors="coerce").fillna(0).astype(int)

        # rest_type handling
        df["rest_type"] = df["rest_type"].fillna("").astype(str).str.strip()
        df.loc[df["rest_type"] == "", "rest_type"] = None

        # Derive budget tier
        df["budget_tier"] = df["cost_for_two"].apply(DataPreprocessor.get_budget_tier)

        # Generate stable string ID (use DataFrame index)
        df["id"] = df.index.astype(str)

        # Select only canonical columns
        canonical_cols = [
            "id", "name", "location", "cuisines", "cost_for_two", 
            "rating", "votes", "rest_type", "budget_tier"
        ]
        df_processed = df[canonical_cols].copy()

        # Sort by rating and votes descending to keep the best records during deduplication
        df_processed = df_processed.sort_values(by=["rating", "votes"], ascending=False)
        # Deduplicate case-insensitively based on name and location (keeping the first, which is the highest-rated/voted)
        df_processed["name_lower"] = df_processed["name"].str.lower().str.strip()
        df_processed["location_lower"] = df_processed["location"].str.lower().str.strip()
        df_processed = df_processed.drop_duplicates(subset=["name_lower", "location_lower"], keep="first")
        df_processed = df_processed.drop(columns=["name_lower", "location_lower"])
        
        print(f"Preprocessed dataset: narrowed from {len(df)} to {len(df_processed)} clean records.")
        return df_processed
