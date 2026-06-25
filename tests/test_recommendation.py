import os
import json
import pytest
from unittest.mock import MagicMock
from src.models.restaurant import Restaurant
from src.models.preferences import UserPreferences
from src.services.recommendation import ResponseParser, RecommendationEnricher, RecommendationService
from src.services.llm_client import LLMClient

@pytest.fixture
def mock_candidates() -> list[Restaurant]:
    return [
        Restaurant(
            id="1",
            name="Jalsa",
            location="Banashankari",
            cuisines=["North Indian", "Mughlai", "Chinese"],
            cost_for_two=800,
            rating=4.1,
            votes=775,
            rest_type="Casual Dining",
            budget_tier="medium"
        ),
        Restaurant(
            id="2",
            name="Cafe Down The Alley",
            location="Banashankari",
            cuisines=["Cafe", "Fast Food"],
            cost_for_two=450,
            rating=3.8,
            votes=120,
            rest_type="Cafe",
            budget_tier="low"
        )
    ]


def test_response_parser_valid():
    raw = '{"summary": "Test summary", "recommendations": [{"id": "1", "rank": 1, "explanation": "test"}]}'
    parsed = ResponseParser.parse_response(raw)
    assert parsed["summary"] == "Test summary"
    assert len(parsed["recommendations"]) == 1


def test_response_parser_markdown():
    raw = '```json\n{"summary": "Test summary", "recommendations": [{"id": "1", "rank": 1, "explanation": "test"}]}\n```'
    parsed = ResponseParser.parse_response(raw)
    assert parsed["summary"] == "Test summary"
    assert len(parsed["recommendations"]) == 1


def test_response_parser_invalid():
    raw_invalid = '{"summary": "Test summary", "recommendations": ' # broken json
    with pytest.raises(json.JSONDecodeError):
        ResponseParser.parse_response(raw_invalid)

    raw_missing_key = '{"summary": "Test summary"}'
    with pytest.raises(ValueError) as exc:
        ResponseParser.parse_response(raw_missing_key)
    assert "missing 'recommendations' key" in str(exc.value)


def test_recommendation_enricher(mock_candidates):
    llm_recs = [
        {"id": "1", "rank": 1, "explanation": "Great choice"},
        {"id": "99", "rank": 2, "explanation": "Hallucinated id"} # should be discarded
    ]
    
    enriched = RecommendationEnricher.enrich(llm_recs, mock_candidates)
    assert len(enriched) == 1
    assert enriched[0].name == "Jalsa"
    assert enriched[0].rating == 4.1
    assert enriched[0].estimated_cost == 800
    assert enriched[0].cuisine == "North Indian, Mughlai, Chinese"
    assert enriched[0].explanation == "Great choice"


def test_recommendation_service_mocked_success(mock_candidates):
    # Load mock response from fixture file
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "mock_llm_response.json")
    with open(fixture_path, "r") as f:
        mock_raw_json = f.read()

    # Mock LLM Client
    mock_client = MagicMock(spec=LLMClient)
    mock_client.api_key = "mock_key"
    mock_client.generate_recommendations.return_value = mock_raw_json

    # Override candidate budgets to both be 'medium' to match user preference without filtering
    test_candidates = [
        Restaurant(
            id="1",
            name="Jalsa",
            location="Banashankari",
            cuisines=["North Indian", "Mughlai", "Chinese"],
            cost_for_two=800,
            rating=4.1,
            votes=775,
            rest_type="Casual Dining",
            budget_tier="medium"
        ),
        Restaurant(
            id="2",
            name="Cafe Down The Alley",
            location="Banashankari",
            cuisines=["Cafe", "Fast Food"],
            cost_for_two=450,
            rating=3.8,
            votes=120,
            rest_type="Cafe",
            budget_tier="medium"
        )
    ]

    # Mock repository
    mock_repo = MagicMock()
    mock_repo.get_locations.return_value = ["Banashankari"]
    mock_repo.get_all.return_value = test_candidates
    
    # Inject mock repository
    import src.data.repository as repo_module
    original_load = repo_module.RestaurantRepository.load
    repo_module.RestaurantRepository.load = MagicMock(return_value=mock_repo)

    try:
        svc = RecommendationService(llm_client=mock_client)
        prefs = UserPreferences(location="Banashankari", budget="medium")
        res = svc.recommend(prefs)
        
        assert res.metadata.fallback_applied is False
        assert len(res.recommendations) == 2
        assert res.recommendations[0].name == "Jalsa"
        assert res.recommendations[1].name == "Cafe Down The Alley"
        assert "Jalsa offers" in res.recommendations[0].explanation
    finally:
        # Restore repository
        repo_module.RestaurantRepository.load = original_load


def test_recommendation_service_retry_on_parse_error(mock_candidates):
    mock_client = MagicMock(spec=LLMClient)
    mock_client.api_key = "mock_key"
    
    # Return broken json first, then valid json on retry
    mock_client.generate_recommendations.side_effect = [
        '{"summary": "broken...", "recommendations": ', # broken
        '{"summary": "success on retry", "recommendations": [{"id": "1", "rank": 1, "explanation": "fixed"}]}' # success
    ]

    mock_repo = MagicMock()
    mock_repo.get_locations.return_value = ["Banashankari"]
    mock_repo.get_all.return_value = mock_candidates
    
    import src.data.repository as repo_module
    original_load = repo_module.RestaurantRepository.load
    repo_module.RestaurantRepository.load = MagicMock(return_value=mock_repo)

    try:
        svc = RecommendationService(llm_client=mock_client)
        prefs = UserPreferences(location="Banashankari", budget="medium")
        res = svc.recommend(prefs)
        
        # Verify it called generate_recommendations twice
        assert mock_client.generate_recommendations.call_count == 2
        assert res.metadata.fallback_applied is False
        assert len(res.recommendations) == 1
        assert res.recommendations[0].name == "Jalsa"
        assert res.summary == "success on retry"
    finally:
        repo_module.RestaurantRepository.load = original_load


def test_recommendation_service_fallback_on_failure(mock_candidates):
    mock_client = MagicMock(spec=LLMClient)
    mock_client.api_key = "mock_key"
    # Throw an exception during API call
    mock_client.generate_recommendations.side_effect = Exception("API rate limited / network timeout")

    mock_repo = MagicMock()
    mock_repo.get_locations.return_value = ["Banashankari"]
    mock_repo.get_all.return_value = mock_candidates
    
    import src.data.repository as repo_module
    original_load = repo_module.RestaurantRepository.load
    repo_module.RestaurantRepository.load = MagicMock(return_value=mock_repo)

    try:
        svc = RecommendationService(llm_client=mock_client)
        prefs = UserPreferences(location="Banashankari", budget="medium")
        res = svc.recommend(prefs)
        
        # Verify fallback is applied
        assert res.metadata.fallback_applied is True
        assert res.metadata.model == "heuristic-fallback"
        # Should return top candidates based on ratings from filter shortlist
        assert len(res.recommendations) == 1 # only 1 matching medium budget (Jalsa)
        assert res.recommendations[0].name == "Jalsa"
        assert "AI service currently unavailable" in res.recommendations[0].explanation
    finally:
        repo_module.RestaurantRepository.load = original_load


def test_recommendation_enricher_deduplication():
    # Make candidate restaurants with the same name (case-insensitive) but different IDs
    candidates = [
        Restaurant(
            id="1",
            name="Truffles",
            location="MG Road",
            cuisines=["Cafe"],
            cost_for_two=900,
            rating=4.5,
            votes=100,
            budget_tier="medium"
        ),
        Restaurant(
            id="2",
            name="truffles", # duplicate name
            location="MG Road",
            cuisines=["Cafe"],
            cost_for_two=950,
            rating=4.3,
            votes=50,
            budget_tier="medium"
        )
    ]
    llm_recs = [
        {"id": "1", "rank": 1, "explanation": "Top rated Truffles"},
        {"id": "2", "rank": 2, "explanation": "Another Truffles entry"}
    ]
    enriched = RecommendationEnricher.enrich(llm_recs, candidates)
    # The duplicate should be discarded
    assert len(enriched) == 1
    assert enriched[0].name == "Truffles"
    assert enriched[0].rank == 1

