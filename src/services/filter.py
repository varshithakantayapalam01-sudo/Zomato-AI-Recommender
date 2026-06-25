import difflib
from typing import List, Tuple, Optional
from src.models.restaurant import Restaurant
from src.models.preferences import UserPreferences
from src.data.repository import RestaurantRepository
from src.config import settings

class LocationValidationError(ValueError):
    """
    Exception raised when a requested location is not found in the dataset.
    Provides fuzzy matching suggestions if available.
    """
    def __init__(self, location: str, suggestions: List[str]):
        self.location = location
        self.suggestions = suggestions
        message = f"Location '{location}' not found in dataset."
        if suggestions:
            message += f" Did you mean one of: {', '.join(suggestions)}?"
        super().__init__(message)


class PreferenceNormalizer:
    """
    Normalizes inputs, such as mapping neighborhood aliases to canonical names.
    """
    ALIAS_MAP = {
        "btm layout": "BTM",
        "jp nagar phase 1": "JP Nagar",
        "jp nagar phase 2": "JP Nagar",
        "jp nagar phase 3": "JP Nagar",
        "jp nagar phase 4": "JP Nagar",
        "jp nagar phase 5": "JP Nagar",
        "jp nagar phase 6": "JP Nagar",
        "jp nagar phase 7": "JP Nagar",
        "jp nagar phase 8": "JP Nagar",
        "hbr layout": "HBR Layout",
        "hrbr layout": "HRBR Layout",
        "electronic city phase 1": "Electronic City",
        "electronic city phase 2": "Electronic City",
    }

    @classmethod
    def normalize_location_input(cls, location: str) -> str:
        loc_clean = location.strip().lower()
        if loc_clean in cls.ALIAS_MAP:
            return cls.ALIAS_MAP[loc_clean]
        return location.strip()


class PreferenceValidator:
    """
    Validates user preferences against database-level constraints.
    """
    @staticmethod
    def validate_location(location: str, repo: RestaurantRepository) -> str:
        """
        Validates location against the repository's known locations.
        Matches case-insensitively and checks for close suggestions.
        Returns the normalized casing of the location.
        """
        normalized_name = PreferenceNormalizer.normalize_location_input(location)
        loc_clean = normalized_name.lower()
        known_locations = repo.get_locations()
        
        # Check exact (case-insensitive) match
        for known in known_locations:
            if known.lower() == loc_clean:
                return known
                
        # If no exact match, look for close fuzzy suggestions
        close_matches = difflib.get_close_matches(normalized_name, known_locations, n=5, cutoff=0.5)
        raise LocationValidationError(location, close_matches)


class RestaurantFilter:
    """
    Applies deterministic filters and ranking criteria to select candidates for the LLM.
    """
    @staticmethod
    def filter_candidates(
        repo: RestaurantRepository, 
        prefs: UserPreferences
    ) -> Tuple[List[Restaurant], Optional[str]]:
        """
        Filters the restaurant repository based on user preferences.
        Applies progressive constraint relaxation if 0 candidates are returned:
        cuisine -> budget -> min_rating.
        
        Returns a tuple of (candidate_list, warning_message).
        """
        # Validate and get normalized location name
        normalized_location = PreferenceValidator.validate_location(prefs.location, repo)

        # Get all restaurants for that location
        all_restaurants = repo.get_all()
        loc_restaurants = [r for r in all_restaurants if r.location.lower() == normalized_location.lower()]
        
        if not loc_restaurants:
            return [], f"No restaurants found in location '{normalized_location}'."

        def apply_filters(use_cuisine: bool, use_budget: bool, use_rating: bool) -> List[Restaurant]:
            res = loc_restaurants
            
            # Apply budget filter (range or tier)
            if use_budget:
                if prefs.min_budget is not None or prefs.max_budget is not None:
                    min_b = prefs.min_budget if prefs.min_budget is not None else 0
                    max_b = prefs.max_budget if prefs.max_budget is not None else 9999999
                    res = [r for r in res if min_b <= r.cost_for_two <= max_b]
                elif prefs.budget:
                    res = [r for r in res if r.budget_tier == prefs.budget]
                
            # Apply min rating filter
            if use_rating:
                res = [r for r in res if r.rating >= prefs.min_rating]
                
            # Apply cuisine filter
            if use_cuisine and prefs.cuisine:
                c_clean = prefs.cuisine.lower()
                res = [r for r in res if any(c_clean in c.lower() for c in r.cuisines)]
                
            return res

        # Attempt 1: All constraints active
        candidates = apply_filters(use_cuisine=True, use_budget=True, use_rating=True)
        if candidates:
            return RestaurantFilter.rank_and_cap(candidates), None

        # Attempt 2: Relax cuisine (if provided)
        if prefs.cuisine:
            candidates = apply_filters(use_cuisine=False, use_budget=True, use_rating=True)
            if candidates:
                msg = f"No restaurants matching cuisine '{prefs.cuisine}' found in {normalized_location}. Showing other cuisines."
                return RestaurantFilter.rank_and_cap(candidates), msg

        # Attempt 3: Relax budget tier/range
        candidates = apply_filters(use_cuisine=False, use_budget=False, use_rating=True)
        if candidates:
            if prefs.min_budget is not None or prefs.max_budget is not None:
                min_b = prefs.min_budget if prefs.min_budget is not None else 0
                max_b = prefs.max_budget if prefs.max_budget is not None else 9999999
                msg = f"No restaurants matching budget range ₹{min_b} – ₹{max_b} found in {normalized_location}. Showing all budgets."
            else:
                msg = f"No restaurants matching budget tier '{prefs.budget}' found in {normalized_location}. Showing all budgets."
            return RestaurantFilter.rank_and_cap(candidates), msg

        # Attempt 4: Relax rating threshold
        candidates = apply_filters(use_cuisine=False, use_budget=False, use_rating=False)
        if candidates:
            msg = f"No restaurants matching rating threshold >= {prefs.min_rating} found in {normalized_location}. Showing lower-rated options."
            return RestaurantFilter.rank_and_cap(candidates), msg

        return [], f"No restaurants found in location '{normalized_location}'."

    @staticmethod
    def rank_and_cap(restaurants: List[Restaurant]) -> List[Restaurant]:
        """
        Sorts candidates by rating DESC, then votes DESC.
        Caps output list length at MAX_CANDIDATES_FOR_LLM.
        """
        sorted_res = sorted(
            restaurants,
            key=lambda r: (r.rating, r.votes),
            reverse=True
        )
        return sorted_res[:settings.MAX_CANDIDATES_FOR_LLM]
