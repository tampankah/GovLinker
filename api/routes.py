from fastapi import APIRouter, UploadFile, HTTPException
from pydantic import BaseModel
from typing import List
from utils.image_utils import encode_image_to_base64, convert_pdf_to_images, pil_image_to_base64
import os
from openai import OpenAI

# Konfiguracja
XAI_API_KEY = os.getenv("XAI_API_KEY")
VISION_MODEL_NAME = "grok-vision-beta"
CHAT_MODEL_NAME = "grok-beta"

# Inicjalizacja klienta OpenAI
client = OpenAI(
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1",
)

router = APIRouter()

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

@router.on_event("startup")
def initialize_rag():
    global rag_store
    txt_folder_path = "./documents"  # Folder z dokumentami TXT
    rag_store = DocumentStore(txt_folder_path)

class DocumentStore:
    def __init__(self, txt_folder_path: str):
        self.documents = []
        self.load_documents(txt_folder_path)

    def load_documents(self, folder_path: str):
        for file_name in os.listdir(folder_path):
            if file_name.endswith(".txt"):  # Filtrujemy tylko pliki tekstowe
                file_path = os.path.join(folder_path, file_name)
                text = self.extract_text_from_txt(file_path)
                if text.strip():  # Sprawdzamy, czy plik nie jest pusty
                    self.documents.append(text)
                else:
                    print(f"Plik {file_name} jest pusty lub zawiera tylko białe znaki.")
        if not self.documents:
            raise ValueError("Brak danych do przetworzenia, wszystkie pliki są puste.")

    def extract_text_from_txt(self, txt_path: str) -> str:
        with open(txt_path, "r", encoding="utf-8") as file:
            return file.read()

rag_store = None

@router.post("/validate-document", response_model=DocumentCheckResult)
async def validate_document(file: UploadFile):
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
    messages = [
        {"role": "system", "content": "You are a helpful assistant for DMV-related processes and documents."},
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

