from fastapi import APIRouter, UploadFile, HTTPException
from .models import QuestionRequest
from .services.document_processing import validate_document
from .services.grok_text import generate_response

router = APIRouter()

@router.post("/validate-document")
async def validate_document_endpoint(file: UploadFile):
    """
    Endpoint do walidacji dokumentów.
    """
    try:
        return await validate_document(file)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-response")
def generate_response_endpoint(request: QuestionRequest):
    """
    Endpoint do generowania odpowiedzi na pytania użytkownika.
    """
    try:
        return generate_response(request)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
