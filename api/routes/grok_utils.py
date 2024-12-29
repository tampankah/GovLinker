import logging
from openai import OpenAI
import os
from fastapi import HTTPException

logger = logging.getLogger(__name__)
XAI_API_KEY = os.getenv("XAI_API_KEY")
VISION_MODEL_NAME = "grok-vision-beta"
CHAT_MODEL_NAME = "grok-beta"
client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")

def process_image_with_grok(base64_image: str) -> dict:
    try:
        response = client.chat.completions.create(
            model=VISION_MODEL_NAME,
            messages=[{"role": "user", "content": base64_image}]
        )
        return response.choices[0].message
    except Exception as e:
        logger.error("Error processing image: %s", e)
        raise HTTPException(status_code=500, detail=f"Image processing error: {e}")

def process_document_with_text_model(aggregated_results: list) -> dict:
    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL_NAME,
            messages=[{"role": "user", "content": " ".join(str(result) for result in aggregated_results)}]
        )
        return response.choices[0].message
    except Exception as e:
        logger.error("Error processing document: %s", e)
        raise HTTPException(status_code=500, detail=f"Document processing error: {e}")
