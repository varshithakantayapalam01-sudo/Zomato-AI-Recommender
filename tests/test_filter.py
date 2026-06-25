import pytest
import pandas as pd
from src.models.restaurant import Restaurant
from src.models.preferences import UserPreferences
from src.data.repository import RestaurantRepository
from src.services.filter import RestaurantFilter, PreferenceValidator, LocationValidationError, PreferenceNormalizer

@pytest.fixture
def mock_repo() -> RestaurantRepository:
    """
    Returns a small RestaurantRepository loaded with mock records.
    """
    mock_data = [
        {
            "id": "1",
            "name": "Jalsa",
            "location": "Banashankari",
            "cuisines": ["North Indian", "Mughlai", "Chinese"],
            "cost_for_two": 800,
            "rating": 4.1,
            "votes": 775,
            "rest_type": "Casual Dining",
            "budget_tier": "medium"
        },
        {
            "id": "2",
            "name": "Cafe Down The Alley",
            "location": "Banashankari",
            "cuisines": ["Cafe", "Fast Food"],
            "cost_for_two": 450,
            "rating": 3.8,
            "votes": 120,
            "rest_type": "Cafe",
            "budget_tier": "low"
        },
        {
            "id": "3",
            "name": "Jayanagar Palace",
            "location": "Jayanagar",
            "cuisines": ["South Indian", "North Indian"],
            "cost_for_two": 600,
            "rating": 4.5,
            "votes": 50,
            "rest_type": "Casual Dining",
            "budget_tier": "medium"
        },
        {
            "id": "4",
            "name": "Indiranagar Bistro",
            "location": "Indiranagar",
            "cuisines": ["Italian", "Continental"],
            "cost_for_two": 1800,
            "rating": 4.2,
            "votes": 900,
            "rest_type": "Casual Dining",
            "budget_tier": "high"
        },
        {
            "id": "5",
            "name": "Indiranagar Pizza",
            "location": "Indiranagar",
            "cuisines": ["Italian", "Pizza"],
            "cost_for_two": 1200,
            "rating": 4.2,
            "votes": 100,
            "rest_type": "Quick Service",
            "budget_tier": "medium"
        }
    ]
    df = pd.DataFrame(mock_data)
    return RestaurantRepository(df)


def test_preference_normalization():
    # Alias mapping
    assert PreferenceNormalizer.normalize_location_input("btm layout") == "BTM"
    assert PreferenceNormalizer.normalize_location_input("electronic city phase 1") == "Electronic City"
    # Unknown location trims and passes through
    assert PreferenceNormalizer.normalize_location_input("  koramangala  ") == "koramangala"


def test_location_validation_success(mock_repo):
    # Exact case match
    assert PreferenceValidator.validate_location("Banashankari", mock_repo) == "Banashankari"
    # Case insensitive match
    assert PreferenceValidator.validate_location("jayanagar", mock_repo) == "Jayanagar"
    # Alias lookup normalization
    assert PreferenceNormalizer.normalize_location_input("electronic city phase 1") == "Electronic City"


def test_location_validation_failure(mock_repo):
    # Unknown city
    with pytest.raises(LocationValidationError) as excinfo:
        PreferenceValidator.validate_location("Mumbai", mock_repo)
    assert "Mumbai" in str(excinfo.value)
    
    # Fuzzy suggestion verification
    with pytest.raises(LocationValidationError) as excinfo:
        PreferenceValidator.validate_location("Jaynagar", mock_repo) # misspelled
    assert "Jayanagar" in excinfo.value.suggestions


def test_restaurant_filter_exact_match(mock_repo):
    # Find Jalsa: Banashankari, medium budget, North Indian cuisine, rating >= 4.0
    prefs = UserPreferences(
        location="Banashankari",
        budget="medium",
        cuisine="North Indian",
        min_rating=4.0
    )
    candidates, warning = RestaurantFilter.filter_candidates(mock_repo, prefs)
    assert warning is None
    assert len(candidates) == 1
    assert candidates[0].name == "Jalsa"


def test_restaurant_filter_cuisine_relaxation(mock_repo):
    # Find Italian in Banashankari (none exist, should relax cuisine)
    prefs = UserPreferences(
        location="Banashankari",
        budget="medium",
        cuisine="Italian",
        min_rating=4.0
    )
    candidates, warning = RestaurantFilter.filter_candidates(mock_repo, prefs)
    assert warning is not None
    assert "cuisine" in warning.lower()
    # Should fall back to Jalsa (medium budget, >= 4.0 in Banashankari)
    assert len(candidates) == 1
    assert candidates[0].name == "Jalsa"


def test_restaurant_filter_budget_relaxation(mock_repo):
    # Find low budget, rating >= 4.0 in Indiranagar (none exist, high is 1800, medium is 1200)
    prefs = UserPreferences(
        location="Indiranagar",
        budget="low",
        min_rating=4.0
    )
    candidates, warning = RestaurantFilter.filter_candidates(mock_repo, prefs)
    assert warning is not None
    assert "budget" in warning.lower()
    # Should fall back to showing all budgets (Indiranagar Bistro and Indiranagar Pizza)
    assert len(candidates) == 2
    # Verify rating/votes sorting order
    assert candidates[0].name == "Indiranagar Bistro" # 900 votes vs 100 votes
    assert candidates[1].name == "Indiranagar Pizza"


def test_restaurant_filter_rating_relaxation(mock_repo):
    # Find high rating (5.0) in Banashankari (highest is Jalsa at 4.1)
    prefs = UserPreferences(
        location="Banashankari",
        budget="medium",
        min_rating=5.0
    )
    candidates, warning = RestaurantFilter.filter_candidates(mock_repo, prefs)
    assert warning is not None
    assert "rating" in warning.lower()
    assert len(candidates) == 2
    assert candidates[0].name == "Jalsa"
    assert candidates[1].name == "Cafe Down The Alley"


def test_restaurant_filter_numeric_budget(mock_repo):
    # Filter with actual price range where matching restaurants exist
    # Jalsa is 800, Cafe Down The Alley is 450
    prefs = UserPreferences(
        location="Banashankari",
        min_budget=500,
        max_budget=1000
    )
    candidates, warning = RestaurantFilter.filter_candidates(mock_repo, prefs)
    assert warning is None
    assert len(candidates) == 1
    assert candidates[0].name == "Jalsa"


def test_restaurant_filter_numeric_budget_relaxation(mock_repo):
    # Filter with actual price range where no restaurants match
    # Indiranagar has 1800 and 1200. Filter for range 500-1000.
    prefs = UserPreferences(
        location="Indiranagar",
        min_budget=500,
        max_budget=1000
    )
    candidates, warning = RestaurantFilter.filter_candidates(mock_repo, prefs)
    assert warning is not None
    assert "budget range" in warning.lower()
    # Should relax and show all budgets for that location
    assert len(candidates) == 2
    assert candidates[0].name == "Indiranagar Bistro"
    assert candidates[1].name == "Indiranagar Pizza"



