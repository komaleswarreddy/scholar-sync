"""
DALL-E Image Generation Client

Generates images using OpenAI's DALL-E API.
"""

from typing import Optional, Dict, Any
import openai
import asyncio
from config.settings import settings


class DALLEClient:
    """Client for generating images using OpenAI's DALL-E API."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        if not self.api_key or self.api_key == "your-openai-api-key":
            raise ValueError("OpenAI API key not configured. Please set OPENAI_API_KEY in .env")
        self._client = None
    
    @property
    def client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            self._client = openai.OpenAI(api_key=self.api_key)
        return self._client
    
    async def generate_image(
        self,
        prompt: str,
        model: str = "dall-e-3",
        size: str = "1024x1024",
        quality: str = "standard",
        n: int = 1,
        response_format: str = "url"
    ) -> Dict[str, Any]:
        """
        Generate an image using DALL-E.
        
        Args:
            prompt: Text description of the image to generate
            model: Model to use (dall-e-2 or dall-e-3)
            size: Image size (dall-e-3: "1024x1024", "1792x1024", "1024x1792")
            quality: Image quality (dall-e-3: "standard" or "hd")
            n: Number of images to generate (dall-e-3: always 1)
            response_format: "url" or "b64_json"
            
        Returns:
            Dictionary with image URL or base64 data
        """
        try:
            # DALL-E 3 only supports n=1
            if model == "dall-e-3":
                n = 1
            
            # Run the synchronous OpenAI call in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.images.generate(
                    model=model,
                    prompt=prompt,
                    n=n,
                    size=size,
                    quality=quality,
                    response_format=response_format
                )
            )
            
            if response_format == "url":
                return {
                    "url": response.data[0].url,
                    "revised_prompt": getattr(response.data[0], 'revised_prompt', None),
                    "model": model
                }
            else:
                return {
                    "b64_json": response.data[0].b64_json,
                    "revised_prompt": getattr(response.data[0], 'revised_prompt', None),
                    "model": model
                }
        except Exception as e:
            raise ValueError(f"Failed to generate image: {str(e)}")
