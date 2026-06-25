import os
import pandas as pd
from datasets import load_dataset
from src.config import settings

class DatasetLoader:
    @staticmethod
    def load_raw_dataset() -> pd.DataFrame:
        """
        Loads the raw Zomato dataset from Hugging Face.
        """
        print(f"Fetching dataset '{settings.HF_DATASET_NAME}' from Hugging Face...")
        dataset = load_dataset(settings.HF_DATASET_NAME, split="train")
        df = dataset.to_pandas()
        print(f"Successfully loaded {len(df)} raw records from Hugging Face.")
        return df

    @staticmethod
    def get_dataset() -> pd.DataFrame:
        """
        Retrieves the dataset. If a local cache exists, it loads from cache.
        Otherwise, it downloads, preprocesses, and caches the dataset.
        """
        cache_path = settings.DATA_CACHE_PATH
        if os.path.exists(cache_path):
            print(f"Loading preprocessed dataset from local cache: {cache_path}")
            try:
                # Read parquet
                return pd.read_parquet(cache_path)
            except Exception as e:
                print(f"Error reading cache at {cache_path}: {e}. Rebuilding cache...")
                # If reading cache fails, fall back to downloading and rebuilding
        
        # Load, preprocess, and save to cache
        df_raw = DatasetLoader.load_raw_dataset()
        from src.data.preprocessor import DataPreprocessor
        df_clean = DataPreprocessor.preprocess(df_raw)
        
        # Ensure directories exist
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        print(f"Saving preprocessed dataset to cache: {cache_path}")
        df_clean.to_parquet(cache_path, index=False)
        return df_clean
