import os
from fastapi import APIRouter, UploadFile, HTTPException
from pydantic import BaseModel
from typing import List
from utils.image_utils import encode_image_to_base64, convert_pdf_to_images, pil_image_to_base64
from openai import OpenAI
import requests

# Konfiguracja
XAI_API_KEY = os.getenv("XAI_API_KEY")
VISION_MODEL_NAME = "grok-vision-beta"
CHAT_MODEL_NAME = "grok-beta"

# Inicjalizacja klienta XAI API
client = OpenAI(
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1",
)

router = APIRouter()

# Mockowane dokumenty
DOCUMENTS_DB = {
    "driver_license_application": {
        "document_name": "Driver's License Application Form",
        "url": "https://dmv.example.com/forms/driver_license_application.pdf"
    },
    "id_card_application": {
        "document_name": "State ID Application Form",
        "url": "https://dmv.example.com/forms/id_card_application.pdf"
    },
    "vehicle_registration": {
        "document_name": "Vehicle Registration Form",
        "url": "https://dmv.example.com/forms/vehicle_registration.pdf"
    },
}

class DocumentCheckResult(BaseModel):
    is_valid: bool
    missing_fields: List[str]
    errors: List[str]

class QuestionRequest(BaseModel):
    question: str

class DocumentRequest(BaseModel):
    document_type: str

class DocumentResponse(BaseModel):
    document_name: str
    url: str

@router.post("/validate-document", response_model=DocumentCheckResult)
async def validate_document(file: UploadFile):
    if file.content_type not in ["image/jpeg", "image/png", "application/pdf"]:
        raise HTTPException(status_code=400, detail="Unsupported file type. Only JPEG, PNG, and PDF are allowed.")

    # Przetwarzanie pliku obrazu lub PDF do base64
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
    # Przesyłanie zapytania do modelu Grok
    response = requests.post(
        f"https://api.x.ai/v1/models/{VISION_MODEL_NAME}/predict",
        headers={"Authorization": f"Bearer {XAI_API_KEY}"},
        json={
            "inputs": {
                "image": base64_image,
                "text": "Extract and validate all fields in this document match to headlines?",
            }
        }
    )
    response.raise_for_status()
    return response.json()

def analyze_document_results(results: List[dict]) -> DocumentCheckResult:
    # Walidacja danych w wynikach
    required_fields = ["Name", "Date of Birth", "Document Number", "Expiration Date"]
    missing_fields = []
    errors = []
    
    for field in required_fields:
        if not any(field in result.get("content", "") for result in results):
            missing_fields.append(field)
    
    is_valid = len(missing_fields) == 0
    return DocumentCheckResult(is_valid=is_valid, missing_fields=missing_fields, errors=errors)

# Funkcja do ładowania dokumentów PDF do modelu
@router.on_event("startup")
def initialize_rag():
    # Można zaimplementować logikę, która załaduje dokumenty z folderu i przygotuje je do użycia w modelu.
    pass

@router.post("/generate-response", response_model=List[str])
def ask_question(request: QuestionRequest):
    # Przygotowanie dokumentów i zapytania dla modelu Grok
    documents = get_documents_from_folder()  # Funkcja do pobierania dokumentów z folderu lub bazy
    context = "\n".join(documents)

    # Zapytanie do modelu Grok na podstawie dokumentów
    response = process_chat_with_grok(context, request.question)
    return [response]

def process_chat_with_grok(context: str, question: str) -> str:
    response = requests.post(
        f"https://api.x.ai/v1/models/{CHAT_MODEL_NAME}/chat",
        headers={"Authorization": f"Bearer {XAI_API_KEY}"},
        json={
            "messages": [
                {"role": "system", "content": "You are a helpful assistant for DMV-related processes and documents."},
                {"role": "user", "content": f"Using the following documents as context, answer the question: \n{context}\n\nQuestion: {question}"}
            ]
        }
    )
    response.raise_for_status()
    return response.json().get("choices", [{}])[0].get("message", {}).get("content", "")

@router.post("/get-document", response_model=DocumentResponse)
def get_document_endpoint(request: DocumentRequest):
    document = DOCUMENTS_DB.get(request.document_type)
    if not document:
        raise HTTPException(status_code=404, detail="Document type not found")
    return DocumentResponse(**document)

def get_documents_from_folder():
    return ["Document 1 content...", "Document 2 content..."]
