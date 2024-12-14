from fastapi import APIRouter, UploadFile, HTTPException
from pydantic import BaseModel
from typing import List
from utils.image_utils import encode_image_to_base64, convert_pdf_to_images, pil_image_to_base64
import os
from openai import OpenAI

XAI_API_KEY = os.getenv("XAI_API_KEY")  
VISION_MODEL_NAME = "grok-vision-beta" 
CHAT_MODEL_NAME = "grok-beta"  


client = OpenAI(
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1", 
)

router = APIRouter()

class DocumentCheckResult(BaseModel):
    """
    Model to represent the result of document validation.
    """
    is_valid: bool 
    missing_fields: List[str]  
    errors: List[str] 

class QuestionRequest(BaseModel):
    """
    Model for the user question in the /generate-response endpoint.
    """
    question: str  

class DocumentRequest(BaseModel):
    """
    Model for specifying the type of document in the /validate-document endpoint.
    """
    document_type: str  

class DocumentResponse(BaseModel):
    """
    Model for the response that contains document details.
    """
    document_name: str 
    url: str 

@router.post("/validate-document", response_model=DocumentCheckResult)
async def validate_document(file: UploadFile):
    """
    Validates the document uploaded by the user (JPEG, PNG, or PDF).
    """
    if file.content_type not in ["image/jpeg", "image/png", "application/pdf"]:
        raise HTTPException(status_code=400, detail="Unsupported file type. Only JPEG, PNG, and PDF are allowed.")

    if file.content_type == "application/pdf":
        images = convert_pdf_to_images(file.file)
        base64_images = [pil_image_to_base64(image) for image in images]
    else:
        base64_image = encode_image_to_base64(file.file)
        base64_images = [base64_image]

    results = []
    for image in base64_images:
        result = process_image_with_grok(image) 
        results.append(result)

    aggregated_result = analyze_document_results(results)
    return aggregated_result

def process_image_with_grok(base64_image: str) -> dict:
    """
    Sends the base64-encoded image to Grok's vision model for analysis.
    """
    response = client.chat.completions.create(
        model=VISION_MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "high",
                        },
                    },
                    {
                        "type": "text",
                        "text": "Extract and validate all fields in this document match to headlines?",
                    },
                ],
            }
        ],
    )
    return response.choices[0].message

def analyze_document_results(results: List[dict]) -> DocumentCheckResult:
    """
    Analyzes the results from the vision model and checks for missing required fields.
    """
    required_fields = ["Name", "Date of Birth", "Document Number", "Expiration Date"]
    missing_fields = []
    errors = []
    
    for field in required_fields:
        if not any(field in result["content"] for result in results if "content" in result):
            missing_fields.append(field)

    is_valid = len(missing_fields) == 0
    return DocumentCheckResult(is_valid=is_valid, missing_fields=missing_fields, errors=errors)

@router.post("/generate-response", response_model=List[str])
def ask_question(request: QuestionRequest):
    """
    Responds to the user's question related to DMV processes using the Grok chat model.
    """
    messages = [
        {"role": "system", "content": "You are fuuny a helpful assistant for DMV-related processes and documents a short message with 2/10 knowledge the most relevant."},
        {"role": "user", "content": f"Question: {request.question}"}
    ]
    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL_NAME,
            messages=messages
        )
        answer = response.choices[0].message.content
        return [answer]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error processing the request with Grok")
