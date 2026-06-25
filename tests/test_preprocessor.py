import os
import json
import pandas as pd
from src.data.preprocessor import DataPreprocessor

def test_parse_rating():
    assert DataPreprocessor.parse_rating("4.1/5") == 4.1
    assert DataPreprocessor.parse_rating("NEW") == 0.0
    assert DataPreprocessor.parse_rating("-") == 0.0
    assert DataPreprocessor.parse_rating(None) == 0.0
    assert DataPreprocessor.parse_rating("") == 0.0
    assert DataPreprocessor.parse_rating("3.5") == 3.5

def test_parse_cost():
    assert DataPreprocessor.parse_cost("800") == 800
    assert DataPreprocessor.parse_cost("1,600") == 1600
    assert DataPreprocessor.parse_cost(None) == 0
    assert DataPreprocessor.parse_cost("") == 0
    assert DataPreprocessor.parse_cost("invalid") == 0

def test_parse_cuisines():
    assert DataPreprocessor.parse_cuisines("North Indian, Mughlai, Chinese") == ["North Indian", "Mughlai", "Chinese"]
    assert DataPreprocessor.parse_cuisines("South Indian") == ["South Indian"]
    assert DataPreprocessor.parse_cuisines(None) == []
    assert DataPreprocessor.parse_cuisines("") == []

def test_get_budget_tier():
    # threshold low_max is 500, medium_max is 1500
    assert DataPreprocessor.get_budget_tier(300) == "low"
    assert DataPreprocessor.get_budget_tier(500) == "low"
    assert DataPreprocessor.get_budget_tier(800) == "medium"
    assert DataPreprocessor.get_budget_tier(1500) == "medium"
    assert DataPreprocessor.get_budget_tier(1600) == "high"

def test_preprocess_pipeline():
    # Load raw sample restaurants
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "sample_restaurants.json")
    with open(fixture_path, "r") as f:
        raw_data = json.load(f)
        
    df_raw = pd.DataFrame(raw_data)
    
    # Process
    df_clean = DataPreprocessor.preprocess(df_raw)
    
    # Two invalid rows (empty name and null location) should have been dropped
    # Output length should be 5 (Jalsa, Spice Bazaar, Cafe Down The Alley, Grand Pavilion, Expensive Fine Dine)
    assert len(df_clean) == 5
    
    # Check that canonical columns exist
    expected_cols = {
        "id", "name", "location", "cuisines", "cost_for_two", 
        "rating", "votes", "rest_type", "budget_tier"
    }
    assert set(df_clean.columns) == expected_cols
    
    # Verify specific parsing outputs
    jalsa = df_clean[df_clean["name"] == "Jalsa"].iloc[0]
    assert jalsa["rating"] == 4.1
    assert jalsa["cost_for_two"] == 800
    assert jalsa["cuisines"] == ["North Indian", "Mughlai", "Chinese"]
    assert jalsa["budget_tier"] == "medium"
    
    grand = df_clean[df_clean["name"] == "Grand Pavilion"].iloc[0]
    assert grand["rating"] == 0.0
    assert grand["cost_for_two"] == 1600
    assert grand["budget_tier"] == "high"
