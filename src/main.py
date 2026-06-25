import sys
from src.config import settings
from src.data.repository import RestaurantRepository

def main():
    print("Zomato AI-Powered Restaurant Recommendation System")
    print("==================================================")
    print("Configuration loaded successfully:")
    print(f"  Dataset Name: {settings.HF_DATASET_NAME}")
    print(f"  Data Cache Path: {settings.DATA_CACHE_PATH}")
    print(f"  Groq Model: {settings.GROQ_MODEL}")
    print(f"  Max Candidates for LLM: {settings.MAX_CANDIDATES_FOR_LLM}")
    print(f"  Top K Recommendations: {settings.TOP_K_RECOMMENDATIONS}")
    print("\nInitializing Restaurant Repository (this might take a few seconds on first run)...")
    
    try:
        repo = RestaurantRepository.load()
        restaurants = repo.get_all()
        locations = repo.get_locations()
        cuisines = repo.get_cuisines()
        
        print("\nStartup Check Successful:")
        print(f"  Total Clean Restaurants Loaded: {len(restaurants)}")
        print(f"  Unique Locations Found: {len(locations)} (e.g., {', '.join(locations[:5])}...)")
        print(f"  Unique Cuisines Found: {len(cuisines)} (e.g., {', '.join(cuisines[:5])}...)")
    except Exception as e:
        print(f"\nError initializing repository: {e}", file=sys.stderr)
        return 1
        
    return 0


def run_api(host: str = "0.0.0.0", port: int = 8000):
    """Launch the FastAPI server via uvicorn."""
    import uvicorn
    print(f"Starting API server on {host}:{port}...")
    uvicorn.run("src.api.main:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "api":
        # Parse optional --port flag
        port = 8000
        if "--port" in sys.argv:
            idx = sys.argv.index("--port")
            if idx + 1 < len(sys.argv):
                port = int(sys.argv[idx + 1])
        run_api(port=port)
    else:
        sys.exit(main())
