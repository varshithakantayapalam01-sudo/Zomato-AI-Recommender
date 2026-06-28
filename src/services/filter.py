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
    Implements progressive constraint relaxation and location expansion to guarantee
    a minimum number of results (TOP_K_RECOMMENDATIONS).
    """
    @staticmethod
    def filter_candidates(
        repo: RestaurantRepository, 
        prefs: UserPreferences
    ) -> Tuple[List[Restaurant], Optional[str]]:
        """
        Filters the restaurant repository based on user preferences.
        Applies progressive constraint relaxation if too few candidates:
        cuisine -> budget -> min_rating -> location expansion.
        
        Returns a tuple of (candidate_list, warning_message).
        """
        # Validate and get normalized location name
        normalized_location = PreferenceValidator.validate_location(prefs.location, repo)

        # Get all restaurants for that location
        all_restaurants = repo.get_all()
        loc_restaurants = [r for r in all_restaurants if r.location.lower() == normalized_location.lower()]
        
        if not loc_restaurants:
            # Even if the exact location has 0 restaurants, try expanding
            return RestaurantFilter._expand_to_other_locations(
                all_restaurants, [], prefs, normalized_location
            )

        def apply_filters(
            pool: List[Restaurant],
            use_cuisine: bool,
            use_budget: bool,
            use_rating: bool,
        ) -> List[Restaurant]:
            res = pool
            
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

        warning_parts: List[str] = []
        min_needed = settings.TOP_K_RECOMMENDATIONS

        # Attempt 1: All constraints active
        candidates = apply_filters(loc_restaurants, use_cuisine=True, use_budget=True, use_rating=True)
        if len(candidates) >= min_needed:
            return RestaurantFilter.rank_and_cap(candidates), None

        # Attempt 2: Relax cuisine (if provided)
        if prefs.cuisine:
            relaxed = apply_filters(loc_restaurants, use_cuisine=False, use_budget=True, use_rating=True)
            if len(relaxed) >= min_needed:
                msg = f"Few restaurants matching cuisine '{prefs.cuisine}' in {normalized_location}. Showing other cuisines too."
                return RestaurantFilter.rank_and_cap(relaxed), msg
            if len(relaxed) > len(candidates):
                warning_parts.append(f"cuisine '{prefs.cuisine}' relaxed")
                candidates = relaxed

        # Attempt 3: Relax budget tier/range
        relaxed = apply_filters(loc_restaurants, use_cuisine=False, use_budget=False, use_rating=True)
        if len(relaxed) >= min_needed:
            if prefs.min_budget is not None or prefs.max_budget is not None:
                min_b = prefs.min_budget if prefs.min_budget is not None else 0
                max_b = prefs.max_budget if prefs.max_budget is not None else 9999999
                msg = f"Few restaurants matching budget range ₹{min_b} – ₹{max_b} in {normalized_location}. Showing all budgets."
            else:
                msg = f"Few restaurants matching budget tier '{prefs.budget}' in {normalized_location}. Showing all budgets."
            return RestaurantFilter.rank_and_cap(relaxed), msg
        if len(relaxed) > len(candidates):
            warning_parts.append("budget relaxed")
            candidates = relaxed

        # Attempt 4: Relax rating threshold
        relaxed = apply_filters(loc_restaurants, use_cuisine=False, use_budget=False, use_rating=False)
        if len(relaxed) >= min_needed:
            msg = f"Few restaurants matching rating ≥ {prefs.min_rating} in {normalized_location}. Showing lower-rated options too."
            return RestaurantFilter.rank_and_cap(relaxed), msg
        if len(relaxed) > len(candidates):
            warning_parts.append(f"rating ≥ {prefs.min_rating} relaxed")
            candidates = relaxed

        # Attempt 5: Location expansion — pull from other locations to reach min_needed
        if len(candidates) < min_needed:
            return RestaurantFilter._expand_to_other_locations(
                all_restaurants, candidates, prefs, normalized_location
            )

        # We have some candidates from the target location (< min_needed but > 0)
        msg = " | ".join(warning_parts) if warning_parts else None
        return RestaurantFilter.rank_and_cap(candidates), msg

    @staticmethod
    def _expand_to_other_locations(
        all_restaurants: List[Restaurant],
        local_candidates: List[Restaurant],
        prefs: UserPreferences,
        normalized_location: str,
    ) -> Tuple[List[Restaurant], Optional[str]]:
        """
        When local results are insufficient, expand search to other locations.
        Applies cuisine and budget filters first, then relaxes progressively.
        """
        min_needed = settings.TOP_K_RECOMMENDATIONS
        local_ids = {c.id for c in local_candidates}

        # Pool of restaurants NOT in the target location
        other_restaurants = [
            r for r in all_restaurants
            if r.location.lower() != normalized_location.lower()
        ]

        def apply_other_filters(
            pool: List[Restaurant],
            use_cuisine: bool,
            use_budget: bool,
        ) -> List[Restaurant]:
            res = pool
            if use_budget:
                if prefs.min_budget is not None or prefs.max_budget is not None:
                    min_b = prefs.min_budget if prefs.min_budget is not None else 0
                    max_b = prefs.max_budget if prefs.max_budget is not None else 9999999
                    res = [r for r in res if min_b <= r.cost_for_two <= max_b]
                elif prefs.budget:
                    res = [r for r in res if r.budget_tier == prefs.budget]
            if use_cuisine and prefs.cuisine:
                c_clean = prefs.cuisine.lower()
                res = [r for r in res if any(c_clean in c.lower() for c in r.cuisines)]
            return res

        # Try with cuisine + budget from other locations
        extras = apply_other_filters(other_restaurants, use_cuisine=True, use_budget=True)
        if len(extras) + len(local_candidates) < min_needed:
            # Relax cuisine
            extras = apply_other_filters(other_restaurants, use_cuisine=False, use_budget=True)
        if len(extras) + len(local_candidates) < min_needed:
            # Relax budget too
            extras = apply_other_filters(other_restaurants, use_cuisine=False, use_budget=False)

        # Remove duplicates with local candidates
        extras = [r for r in extras if r.id not in local_ids]

        # Rank extras by rating/votes and take only what we need
        extras_sorted = sorted(extras, key=lambda r: (r.rating, r.votes), reverse=True)
        needed = min_needed - len(local_candidates)
        extras_top = extras_sorted[:max(needed, min_needed)]

        combined = list(local_candidates) + extras_top
        ranked = RestaurantFilter.rank_and_cap(combined)

        if local_candidates:
            msg = (
                f"Only {len(local_candidates)} restaurant(s) found in {normalized_location}. "
                f"Also showing top-rated restaurants from other areas to give you more options."
            )
        else:
            msg = (
                f"No restaurants found in {normalized_location} matching your criteria. "
                f"Showing top-rated restaurants from other areas instead."
            )

        return ranked, msg

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
