from fastapi import APIRouter, UploadFile, HTTPException
from pydantic import BaseModel
from typing import List
from api.services.openai_service import process_image_with_grok, process_document_with_text_model, generate_response
from api.utils.image_utils import encode_image_to_base64, convert_pdf_to_images, pil_image_to_base64
from api.models.document_models import DocumentCheckResult, QuestionRequest, DocumentRequest, DocumentResponse, FunctionCallResultMessage
import tempfile
import logging
import os

router = APIRouter()

# Mock database containing document information
DOCUMENTS_DB = {
    "driver_license_application": {
        "document_name": "Driver's License Application Form",
        "url": "https://www.dps.texas.gov/internetforms/forms/dl-14a.pdf"
    },
}

# API endpoint for document validation
@router.post("/validate-document")
async def validate_document(file: UploadFile):
    if file.content_type not in ["image/jpeg", "image/png", "application/pdf"]:
        raise HTTPException(status_code=400, detail="Unsupported file type. Only JPEG, PNG, and PDF are allowed.")

    try:
        base64_images = []

        if file.content_type == "application/pdf":
            with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as temp_pdf:
                temp_pdf.write(file.file.read())
                temp_pdf.flush()
                images = convert_pdf_to_images(temp_pdf.name)
                base64_images = [pil_image_to_base64(image) for image in images]
        else:
            base64_image = encode_image_to_base64(file.file)
            base64_images = [base64_image]

        # Process image with Grok Vision Model
        aggregated_results = [process_image_with_grok(base64_image) for base64_image in base64_images]

        # Further processing with the Grok Text model
        response = process_document_with_text_model(aggregated_results)
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing the document: {str(e)}")

# API endpoint for generating responses
@router.post("/generate-response", response_model=List[str])
def ask_question(request: QuestionRequest):
    """
    Responds to user's question, potentially including document links.
    """
    try:
        response = generate_response(request.dict())
        return [response]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing the request: {str(e)}")
