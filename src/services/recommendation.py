import json
import re
from typing import Dict, Any, List, Optional
from src.models.restaurant import Restaurant
from src.models.preferences import UserPreferences
from src.models.recommendation import Recommendation, RecommendationResponse, ResponseMetadata
from src.data.repository import RestaurantRepository
from src.services.filter import RestaurantFilter
from src.services.prompt_builder import PromptBuilder
from src.services.llm_client import LLMClient
from src.config import settings

class ResponseParser:
    """
    Parses and cleans the raw JSON response from the LLM.
    """
    @staticmethod
    def parse_response(raw_text: str) -> Dict[str, Any]:
        clean_text = raw_text.strip()
        
        # Remove markdown code block wrappers if they exist
        if clean_text.startswith("```"):
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", clean_text, re.DOTALL)
            if match:
                clean_text = match.group(1).strip()
                
        parsed = json.loads(clean_text)
        if not isinstance(parsed, dict):
            raise ValueError("LLM response is not a JSON object")
        if "recommendations" not in parsed:
            raise ValueError("LLM response is missing 'recommendations' key")
            
        return parsed


class RecommendationEnricher:
    """
    Combines LLM-generated recommendations with local repository factual records.
    """
    @staticmethod
    def enrich(
        llm_recommendations: List[Dict[str, Any]], 
        candidates: List[Restaurant]
    ) -> List[Recommendation]:
        candidate_map = {c.id: c for c in candidates}
        enriched = []
        seen_names = set()
        
        for rec in llm_recommendations:
            rec_id = str(rec.get("id", "")).strip()
            # Reject hallucinated IDs
            if rec_id not in candidate_map:
                print(f"Warning: Discarding hallucinated restaurant ID '{rec_id}' from LLM output.")
                continue
                
            orig = candidate_map[rec_id]
            name_lower = orig.name.lower().strip()
            if name_lower in seen_names:
                print(f"Warning: Discarding duplicate recommendation for '{orig.name}' (case-insensitive duplicate).")
                continue
            seen_names.add(name_lower)
            
            explanation = rec.get("explanation", "Recommended spot matching your preferences.")
            rank = rec.get("rank", len(enriched) + 1)
            
            cuisine_str = ", ".join(orig.cuisines)
            
            enriched.append(
                Recommendation(
                    rank=int(rank),
                    name=orig.name,
                    cuisine=cuisine_str,
                    rating=orig.rating,
                    estimated_cost=orig.cost_for_two,
                    explanation=str(explanation)
                )
            )
            
        # Guarantee rank sorting and re-assign sequence to avoid gaps
        enriched.sort(key=lambda r: r.rank)
        for i, rec in enumerate(enriched):
            rec.rank = i + 1
        return enriched


class RecommendationService:
    """
    Orchestrates the restaurant recommendation workflow:
    filters candidates, invokes LLM with retry logic, parses, and enriches.
    """
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.repo = RestaurantRepository.load()
        self.llm_client = llm_client or LLMClient()

    def recommend(self, prefs: UserPreferences) -> RecommendationResponse:
        # 1. Filter candidates
        candidates, warning_msg = RestaurantFilter.filter_candidates(self.repo, prefs)
        
        # 2. Check for empty candidate pool
        if not candidates:
            filters_applied = {
                "location": prefs.location,
                "budget": prefs.budget,
                "cuisine": prefs.cuisine,
                "min_rating": prefs.min_rating
            }
            metadata = ResponseMetadata(
                candidates_considered=0,
                filters_applied=filters_applied,
                model="none",
                fallback_applied=False
            )
            summary = f"No restaurants found matching your criteria in '{prefs.location}'."
            if warning_msg:
                summary = warning_msg
                
            return RecommendationResponse(
                summary=summary,
                recommendations=[],
                metadata=metadata
            )

        # 3. Handle missing Groq API Key by falling back immediately
        if not self.llm_client.api_key:
            print("Warning: GROQ_API_KEY is missing. Activating heuristic fallback...")
            return self.generate_heuristic_fallback(candidates, prefs, warning_msg)

        # 4. Build prompt
        sys_prompt = PromptBuilder.build_system_prompt()
        user_prompt = PromptBuilder.build_user_prompt(prefs, candidates, settings.TOP_K_RECOMMENDATIONS)
        
        # 5. Invoke LLM and parse response (with retry)
        raw_response = None
        try:
            raw_response = self.llm_client.generate_recommendations(sys_prompt, user_prompt)
            parsed = ResponseParser.parse_response(raw_response)
        except Exception as e:
            print(f"LLM call/parsing failed: {e}.")
            if raw_response is not None:
                # Retry once with low temperature
                print("Retrying once with temperature 0.1...")
                try:
                    raw_response = self.llm_client.generate_recommendations(sys_prompt, user_prompt, temperature=0.1)
                    parsed = ResponseParser.parse_response(raw_response)
                except Exception as retry_err:
                    print(f"Retry failed: {retry_err}. Falling back to heuristics.")
                    return self.generate_heuristic_fallback(candidates, prefs, warning_msg)
            else:
                # Direct API failure/Rate Limit, skip retry and fall back
                return self.generate_heuristic_fallback(candidates, prefs, warning_msg)

        # 6. Enrich suggestions and package response
        try:
            llm_recs = parsed.get("recommendations", [])
            summary = parsed.get("summary", "")
            if warning_msg:
                summary = f"{warning_msg} | {summary}"
                
            enriched = RecommendationEnricher.enrich(llm_recs, candidates)
            
            # Handle case where all LLM results were filtered out as hallucinations
            if not enriched:
                print("Warning: All recommended IDs were hallucinated. Activating heuristic fallback...")
                return self.generate_heuristic_fallback(candidates, prefs, warning_msg)
                
            filters_applied = {
                "location": prefs.location,
                "budget": prefs.budget,
                "cuisine": prefs.cuisine,
                "min_rating": prefs.min_rating
            }
            
            metadata = ResponseMetadata(
                candidates_considered=len(candidates),
                filters_applied=filters_applied,
                model=settings.GROQ_MODEL,
                fallback_applied=False
            )
            
            return RecommendationResponse(
                summary=summary,
                recommendations=enriched,
                metadata=metadata
            )
        except Exception as enrich_err:
            print(f"Enrichment processing failed: {enrich_err}. Falling back...")
            return self.generate_heuristic_fallback(candidates, prefs, warning_msg)

    def generate_heuristic_fallback(
        self, 
        candidates: List[Restaurant], 
        prefs: UserPreferences,
        warning_msg: Optional[str] = None
    ) -> RecommendationResponse:
        """
        Fallback heuristic ranking mechanism if the Groq LLM API is unavailable.
        """
        # Deduplicate candidates case-insensitively by name
        unique_candidates = []
        seen_names = set()
        for c in candidates:
            name_lower = c.name.lower().strip()
            if name_lower not in seen_names:
                seen_names.add(name_lower)
                unique_candidates.append(c)

        # Sort is pre-applied by RestaurantFilter, take top K
        top_candidates = unique_candidates[:settings.TOP_K_RECOMMENDATIONS]
        
        recommendations = []
        for i, c in enumerate(top_candidates):
            explanation = f"Recommended based on an average rating of {c.rating} and {c.votes} votes (AI service currently unavailable)."
            recommendations.append(
                Recommendation(
                    rank=i + 1,
                    name=c.name,
                    cuisine=", ".join(c.cuisines),
                    rating=c.rating,
                    estimated_cost=c.cost_for_two,
                    explanation=explanation
                )
            )
            
        summary = "AI Recommendation service is currently offline. Displaying top-rated options."
        if warning_msg:
            summary = f"{warning_msg} (Note: displaying top-rated fallback options)."
            
        filters_applied = {
            "location": prefs.location,
            "budget": prefs.budget,
            "cuisine": prefs.cuisine,
            "min_rating": prefs.min_rating
        }
        
        metadata = ResponseMetadata(
            candidates_considered=len(candidates),
            filters_applied=filters_applied,
            model="heuristic-fallback",
            fallback_applied=True
        )
        
        return RecommendationResponse(
            summary=summary,
            recommendations=recommendations,
            metadata=metadata
        )
