import logging
from fastapi import HTTPException
from openai import OpenAI
import os

logger = logging.getLogger(__name__)

# API key and model configuration
CHAT_MODEL_NAME = "grok-beta"
XAI_API_KEY = os.getenv("XAI_API_KEY")

client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")

def process_document_with_text_model(aggregated_results: list) -> dict:
    document_context = " ".join([str(result) for result in aggregated_results])

    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL_NAME,
            messages=[
                {"role": "system", "content": "Analyze form data and guide users."},
                {"role": "user", "content": document_context},
            ],
        )
        return response.choices[0].message
    except Exception as e:
        logger.error("Error processing with Grok Text model: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

def generate_response(request):
    base_messages = [
        {"role": "system", "content": "Friendly DMV assistant."},
        {"role": "user", "content": request.question}
    ]

    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL_NAME,
            messages=base_messages,
        )
        return response.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")
