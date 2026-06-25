from typing import List, Optional
import pandas as pd
from src.models.restaurant import Restaurant
from src.data.loader import DatasetLoader

class RestaurantRepository:
    _instance = None

    def __init__(self, df: pd.DataFrame):
        self.df = df
        
        print("Converting dataframe to Restaurant models...")
        records = df.to_dict("records")
        # Ensure cuisines is a list (pandas read_parquet might parse list columns as ndarrays or lists)
        self.restaurants = [
            Restaurant(
                id=str(r["id"]),
                name=str(r["name"]),
                location=str(r["location"]),
                cuisines=list(r["cuisines"]) if r["cuisines"] is not None else [],
                cost_for_two=int(r["cost_for_two"]),
                rating=float(r["rating"]),
                votes=int(r["votes"]),
                rest_type=str(r["rest_type"]) if r["rest_type"] is not None else None,
                budget_tier=str(r["budget_tier"])
            )
            for r in records
        ]
        
        self.restaurant_map = {r.id: r for r in self.restaurants}
        
        # Precompute locations
        self.unique_locations = sorted(list(df["location"].unique()))
        
        # Flatten cuisines
        cuisines_set = set()
        for c_list in df["cuisines"]:
            if hasattr(c_list, "__iter__") and not isinstance(c_list, str):
                for c in c_list:
                    cuisines_set.add(c)
            elif isinstance(c_list, str):
                cuisines_set.add(c_list)
        self.unique_cuisines = sorted(list(cuisines_set))
        
        print(f"Repository initialized with {len(self.restaurants)} restaurants, "
              f"{len(self.unique_locations)} locations, and {len(self.unique_cuisines)} cuisines.")

    @classmethod
    def load(cls) -> "RestaurantRepository":
        if cls._instance is None:
            df = DatasetLoader.get_dataset()
            cls._instance = cls(df)
        return cls._instance

    def get_all(self) -> List[Restaurant]:
        return self.restaurants

    def get_locations(self) -> List[str]:
        return self.unique_locations

    def get_cuisines(self) -> List[str]:
        return self.unique_cuisines

    def get_by_id(self, id: str) -> Optional[Restaurant]:
        return self.restaurant_map.get(id)
