import os
from typing import Dict, Any, Optional
from groq import Groq
from src.config import settings

class LLMClient:
    """
    Client adapter for Groq API inferences.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self._client = None

    @property
    def client(self) -> Groq:
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not configured.")
        if self._client is None:
            self._client = Groq(api_key=self.api_key)
        return self._client

    def generate_recommendations(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        temperature: Optional[float] = None
    ) -> str:
        """
        Sends system and user prompt to Groq API and returns the raw response text.
        """
        model = settings.GROQ_MODEL
        temp = temperature if temperature is not None else settings.GROQ_TEMPERATURE
        
        print(f"Invoking Groq API model '{model}' (temp={temp})...")
        
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temp,
            response_format={"type": "json_object"},
            timeout=10.0  # connection/read timeout
        )
        
        return response.choices[0].message.content
