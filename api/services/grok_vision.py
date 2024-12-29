import logging
from fastapi import HTTPException
from openai import OpenAI
import os

logger = logging.getLogger(__name__)

# API key and model configuration
XAI_API_KEY = os.getenv("XAI_API_KEY")
VISION_MODEL_NAME = "grok-vision-beta"

client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")

def process_image_with_grok(base64_image: str) -> dict:
    try:
        logger.debug("Sending request to Grok Vision model.")
        response = client.chat.completions.create(
            model=VISION_MODEL_NAME,
            messages=[
                {"role": "user", "content": f"Analyze this document: {base64_image}"}
            ],
        )
        logger.debug("Received response from Grok Vision model: %s", response)
        return response.choices[0].message
    except Exception as e:
        logger.error("Error while processing image with Grok Vision model: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")
