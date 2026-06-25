import json
from typing import List, Dict, Any
from src.models.preferences import UserPreferences
from src.models.restaurant import Restaurant

class PromptBuilder:
    @staticmethod
    def build_system_prompt() -> str:
        """
        Builds the system instructions instructing the LLM on its role, constraints, 
        no-hallucination policy, and output JSON schema.
        """
        return (
            "You are a helpful, Zomato-inspired AI restaurant recommendation assistant.\n\n"
            "Your task is to rank the candidate restaurants and provide a personalized explanation "
            "for why each selected restaurant is a good fit based on the user's preferences.\n\n"
            "CRITICAL CONSTRAINTS:\n"
            "1. ONLY recommend restaurants that are present in the provided CANDIDATES list. Do NOT fabricate, invent, or recommend any restaurant not in the candidates list.\n"
            "2. Do NOT change or invent any factual details (ratings, costs, cuisines, name). Use the restaurant's ID to reference them.\n"
            "3. You must respond with a single valid JSON object containing exactly the keys 'summary' and 'recommendations'. Do not include markdown code block wrappers (like ```json) in your raw response, only output the JSON object itself.\n\n"
            "JSON SCHEMA:\n"
            "{\n"
            "  \"summary\": \"A short, human-friendly summary sentence explaining the overall choices (e.g. 'Based on your request, I found some great Italian spots in Banashankari.')\",\n"
            "  \"recommendations\": [\n"
            "    {\n"
            "      \"id\": \"string matching the candidate's ID\",\n"
            "      \"rank\": 1,\n"
            "      \"explanation\": \"A tailored, personalized explanation linking the restaurant features (rating, cost, cuisine, rest_type) and user's additional soft preferences (e.g., family-friendly, quick service) to explain why it fits. Be specific and concise.\"\n"
            "    }\n"
            "  ]\n"
            "}"
        )

    @staticmethod
    def build_user_prompt(prefs: UserPreferences, candidates: List[Restaurant], top_k: int = 5) -> str:
        """
        Constructs the user prompt embedding preferences and serialized candidates.
        """
        # Serialize only the necessary fields of candidate restaurants to conserve tokens
        candidates_data = [
            {
                "id": r.id,
                "name": r.name,
                "location": r.location,
                "cuisines": r.cuisines,
                "cost_for_two": r.cost_for_two,
                "rating": r.rating,
                "votes": r.votes,
                "rest_type": r.rest_type,
                "budget_tier": r.budget_tier
            }
            for r in candidates
        ]
        
        budget_str = None
        if prefs.budget:
            budget_str = prefs.budget
        elif prefs.min_budget is not None or prefs.max_budget is not None:
            min_val = prefs.min_budget if prefs.min_budget is not None else 0
            max_val = prefs.max_budget if prefs.max_budget is not None else "unlimited"
            budget_str = f"₹{min_val} - ₹{max_val}"

        user_prefs_data = {
            "location": prefs.location,
            "budget": budget_str,
            "cuisine": prefs.cuisine,
            "min_rating": prefs.min_rating,
            "additional_notes": prefs.additional
        }

        prompt_dict = {
            "user_preferences": user_prefs_data,
            "max_recommendations": top_k,
            "candidates": candidates_data
        }
        
        return json.dumps(prompt_dict, indent=2)
