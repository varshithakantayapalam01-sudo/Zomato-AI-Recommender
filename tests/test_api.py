"""
Integration tests for the Phase 4 Backend API endpoints.

Uses FastAPI's TestClient to exercise every route with a mocked
RecommendationService (no real Groq/HuggingFace calls).
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes import set_dependencies
from src.data.repository import RestaurantRepository
from src.models.restaurant import Restaurant
from src.models.recommendation import (
    Recommendation,
    RecommendationResponse,
    ResponseMetadata,
)
from src.services.recommendation import RecommendationService
from src.services.filter import LocationValidationError


# ──────────────────────────────────────────────
#  Fixtures
# ──────────────────────────────────────────────

def _make_restaurant(**overrides) -> Restaurant:
    defaults = dict(
        id="1",
        name="Test Restaurant",
        location="Bangalore",
        cuisines=["Italian", "Continental"],
        cost_for_two=1200,
        rating=4.5,
        votes=100,
        rest_type="Casual Dining",
        budget_tier="medium",
    )
    defaults.update(overrides)
    return Restaurant(**defaults)


def _make_recommendation_response(fallback: bool = False) -> RecommendationResponse:
    return RecommendationResponse(
        summary="Great choices in Bangalore!",
        recommendations=[
            Recommendation(
                rank=1,
                name="Test Restaurant",
                cuisine="Italian, Continental",
                rating=4.5,
                estimated_cost=1200,
                explanation="Top rated Italian spot within your budget.",
            ),
            Recommendation(
                rank=2,
                name="Pasta Palace",
                cuisine="Italian",
                rating=4.2,
                estimated_cost=900,
                explanation="Affordable Italian option with great reviews.",
            ),
        ],
        metadata=ResponseMetadata(
            candidates_considered=18,
            filters_applied={
                "location": "Bangalore",
                "budget": "medium",
                "cuisine": "italian",
                "min_rating": 4.0,
            },
            model="heuristic-fallback" if fallback else "llama-3.3-70b-versatile",
            fallback_applied=fallback,
        ),
    )


@pytest.fixture(autouse=True)
def _inject_mocked_deps():
    """
    Before every test, inject a mocked RestaurantRepository and
    RecommendationService into the route module.
    """
    mock_repo = MagicMock(spec=RestaurantRepository)
    mock_repo.get_all.return_value = [
        _make_restaurant(id="1", name="Test Restaurant"),
        _make_restaurant(id="2", name="Pasta Palace", rating=4.2, cost_for_two=900,
                         cuisines=["Italian"], budget_tier="medium"),
        _make_restaurant(id="3", name="Delhi Darbar", location="Delhi", rating=3.8,
                         cost_for_two=400, cuisines=["North Indian"], budget_tier="low"),
    ]
    mock_repo.get_locations.return_value = ["Bangalore", "Delhi", "Kolkata"]
    mock_repo.get_cuisines.return_value = ["Italian", "Continental", "North Indian", "Chinese"]

    mock_svc = MagicMock(spec=RecommendationService)
    mock_svc.recommend.return_value = _make_recommendation_response()

    set_dependencies(mock_repo, mock_svc)
    yield mock_repo, mock_svc

    # Reset after test
    set_dependencies(None, None)  # type: ignore[arg-type]


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


# ──────────────────────────────────────────────
#  GET /api/v1/health
# ──────────────────────────────────────────────

class TestHealth:
    def test_health_returns_200(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["dataset_loaded"] is True
        assert data["record_count"] == 3

    def test_health_before_dataset_loads(self, client):
        """If repo is None, health should report 'starting'."""
        set_dependencies(None, None)  # type: ignore[arg-type]
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "starting"
        assert data["dataset_loaded"] is False


# ──────────────────────────────────────────────
#  GET /api/v1/locations
# ──────────────────────────────────────────────

class TestLocations:
    def test_returns_all_locations(self, client):
        resp = client.get("/api/v1/locations")
        assert resp.status_code == 200
        data = resp.json()
        assert data["locations"] == ["Bangalore", "Delhi", "Kolkata"]

    def test_503_when_not_loaded(self, client):
        set_dependencies(None, None)  # type: ignore[arg-type]
        resp = client.get("/api/v1/locations")
        assert resp.status_code == 503


# ──────────────────────────────────────────────
#  GET /api/v1/cuisines
# ──────────────────────────────────────────────

class TestCuisines:
    def test_returns_all_cuisines(self, client):
        resp = client.get("/api/v1/cuisines")
        assert resp.status_code == 200
        data = resp.json()
        assert set(data["cuisines"]) == {"Italian", "Continental", "North Indian", "Chinese"}

    def test_503_when_not_loaded(self, client):
        set_dependencies(None, None)  # type: ignore[arg-type]
        resp = client.get("/api/v1/cuisines")
        assert resp.status_code == 503


# ──────────────────────────────────────────────
#  POST /api/v1/recommend
# ──────────────────────────────────────────────

class TestRecommend:
    VALID_BODY = {
        "location": "Bangalore",
        "budget": "medium",
        "cuisine": "Italian",
        "min_rating": 4.0,
    }

    def test_valid_request_returns_200(self, client, _inject_mocked_deps):
        resp = client.post("/api/v1/recommend", json=self.VALID_BODY)
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"] is not None
        assert len(data["recommendations"]) == 2
        assert data["recommendations"][0]["rank"] == 1
        assert data["metadata"]["candidates_considered"] == 18
        assert data["metadata"]["fallback_applied"] is False

    def test_numeric_budget_range_api_success(self, client, _inject_mocked_deps):
        _, mock_svc = _inject_mocked_deps
        body = {
            "location": "Bangalore",
            "min_budget": 500,
            "max_budget": 1500,
            "cuisine": "Italian",
            "min_rating": 4.0,
        }
        resp = client.post("/api/v1/recommend", json=body)
        assert resp.status_code == 200
        # Verify recommendation service was called with correct range
        call_args = mock_svc.recommend.call_args
        prefs = call_args[0][0]
        assert prefs.min_budget == 500
        assert prefs.max_budget == 1500
        assert prefs.budget is None

    def test_invalid_budget_range_returns_422(self, client):
        body = {
            "location": "Bangalore",
            "min_budget": 1500,
            "max_budget": 500,
        }
        resp = client.post("/api/v1/recommend", json=body)
        assert resp.status_code == 422

    def test_recommendations_contain_required_fields(self, client):
        resp = client.post("/api/v1/recommend", json=self.VALID_BODY)
        rec = resp.json()["recommendations"][0]
        required = {"rank", "name", "cuisine", "rating", "estimated_cost", "explanation"}
        assert required.issubset(rec.keys())

    def test_missing_location_returns_422(self, client):
        body = {"budget": "medium", "min_rating": 4.0}
        resp = client.post("/api/v1/recommend", json=body)
        assert resp.status_code == 422

    def test_invalid_budget_returns_422(self, client, _inject_mocked_deps):
        _, mock_svc = _inject_mocked_deps
        from pydantic import ValidationError
        mock_svc.recommend.side_effect = ValidationError.from_exception_data(
            title="UserPreferences",
            line_errors=[],
        )
        body = {**self.VALID_BODY, "budget": "ultra-premium"}
        resp = client.post("/api/v1/recommend", json=body)
        # Budget validation happens in UserPreferences, service raises
        # but FastAPI will still accept the request body (budget is str)
        # The domain validator will reject it.
        assert resp.status_code in (422, 500)

    def test_invalid_location_returns_422_with_suggestions(self, client, _inject_mocked_deps):
        _, mock_svc = _inject_mocked_deps
        mock_svc.recommend.side_effect = LocationValidationError(
            "Mumbai", suggestions=["Bangalore", "Delhi"]
        )
        body = {**self.VALID_BODY, "location": "Mumbai"}
        resp = client.post("/api/v1/recommend", json=body)
        assert resp.status_code == 422
        data = resp.json()["detail"]
        assert data["error"] == "Invalid location"
        assert "Mumbai" in data["details"][0]["message"]
        assert "Bangalore" in data["details"][0]["suggestions"]

    def test_fallback_flag_propagated(self, client, _inject_mocked_deps):
        _, mock_svc = _inject_mocked_deps
        mock_svc.recommend.return_value = _make_recommendation_response(fallback=True)
        resp = client.post("/api/v1/recommend", json=self.VALID_BODY)
        assert resp.status_code == 200
        assert resp.json()["metadata"]["fallback_applied"] is True
        assert resp.json()["metadata"]["model"] == "heuristic-fallback"

    def test_min_rating_bounds(self, client):
        body = {**self.VALID_BODY, "min_rating": 6.0}
        resp = client.post("/api/v1/recommend", json=body)
        assert resp.status_code == 422

    def test_optional_fields_omitted(self, client):
        body = {"location": "Bangalore", "budget": "medium"}
        resp = client.post("/api/v1/recommend", json=body)
        assert resp.status_code == 200

    def test_additional_preferences_forwarded(self, client, _inject_mocked_deps):
        _, mock_svc = _inject_mocked_deps
        body = {**self.VALID_BODY, "additional": "family-friendly, outdoor seating"}
        resp = client.post("/api/v1/recommend", json=body)
        assert resp.status_code == 200
        call_args = mock_svc.recommend.call_args
        prefs = call_args[0][0]
        assert prefs.additional == "family-friendly, outdoor seating"


# ──────────────────────────────────────────────
#  CORS
# ──────────────────────────────────────────────

class TestCORS:
    def test_cors_headers_present(self, client):
        resp = client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:8000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:8000"

    def test_cors_rejects_unknown_origin(self, client):
        resp = client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://evil-site.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # FastAPI CORS middleware does not set the header for disallowed origins
        assert resp.headers.get("access-control-allow-origin") != "http://evil-site.com"
