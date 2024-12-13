from fastapi import APIRouter, UploadFile, HTTPException
from pydantic import BaseModel
from typing import List
from utils.image_utils import encode_image_to_base64, convert_pdf_to_images, pil_image_to_base64
import os
from openai import OpenAI
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter

# Konfiguracja
XAI_API_KEY = os.getenv("XAI_API_KEY")
OPEN_AI_API_KEY = os.getenv("OPEN_AI_API_KEY")
VISION_MODEL_NAME = "grok-vision-beta"
CHAT_MODEL_NAME = "grok-beta"

# Inicjalizacja klienta OpenAI
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
        if not any(field in result.get("content", "") for result in results):
            missing_fields.append(field)
    is_valid = len(missing_fields) == 0
    return DocumentCheckResult(is_valid=is_valid, missing_fields=missing_fields, errors=errors)

# Funkcja do ładowania dokumentów PDF jako RAG
rag_store = None

@router.on_event("startup")
def initialize_rag():
    global rag_store
    embeddings = OpenAIEmbeddings(api_key=OPEN_AI_API_KEY)
    pdf_folder_path = "./pdf_documents"  # Folder z dokumentami PDF
    pdf_files = [os.path.join(pdf_folder_path, f) for f in os.listdir(pdf_folder_path) if f.endswith(".pdf")]

    documents = []
    for pdf_file in pdf_files:
        loader = PyPDFLoader(pdf_file)
        raw_documents = loader.load()
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        documents.extend(text_splitter.split_documents(raw_documents))

    rag_store = FAISS.from_documents(documents, embeddings)

@router.post("/generate-response", response_model=List[str])
def ask_question(request: QuestionRequest):
    if not rag_store:
        raise HTTPException(status_code=500, detail="RAG store is not initialized.")

    # Wyszukiwanie w dokumentach
    related_docs = rag_store.similarity_search(request.question, k=3)
    context = "\n".join([doc.page_content for doc in related_docs])

    messages = [
        {"role": "system", "content": "You are a helpful assistant for DMV-related processes and documents."},
        {"role": "user", "content": f"Using the following documents as context, answer the question: \n{context}\n\nQuestion: {request.question}"}
    ]

    response = process_chat_with_grok(messages)
    return [response]

def process_chat_with_grok(messages: List[dict]) -> str:
    response = client.chat.completions.create(
        model=CHAT_MODEL_NAME,
        messages=messages
    )
    return response.choices[0].message["content"]

@router.post("/get-document", response_model=DocumentResponse)
def get_document_endpoint(request: DocumentRequest):
    document = DOCUMENTS_DB.get(request.document_type)
    if not document:
        raise HTTPException(status_code=404, detail="Document type not found")
    return DocumentResponse(**document)
