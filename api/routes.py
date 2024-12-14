from fastapi import APIRouter, HTTPException, Request, Depends, UploadFile
from pydantic import BaseModel
from typing import Optional, List
from utils.image_utils import encode_image_to_base64, convert_pdf_to_images, pil_image_to_base64
import os
from openai import OpenAI

# Configuration
XAI_API_KEY = os.getenv("XAI_API_KEY")
VISION_MODEL_NAME = "grok-vision-beta"
CHAT_MODEL_NAME = "grok-beta"

# Initialize OpenAI client
client = OpenAI(
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1",
)

router = APIRouter()

# Mock document database
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

# Models
class Location(BaseModel):
    country: str
    region: Optional[str] = None

class UserRequest(BaseModel):
    data: str
    location: Location

class LocationResponse(BaseModel):
    message: str
    location: Location

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

# Dependency to extract location from request headers
async def get_user_location(request: Request) -> Location:
    country = request.headers.get("X-User-Country")
    region = request.headers.get("X-User-Region")

    if not country:
        raise HTTPException(
            status_code=400,
            detail="Missing 'X-User-Country' header."
        )

    return Location(country=country, region=region)

# Document store for managing text documents
class DocumentStore:
    def __init__(self, txt_folder_path: str):
        self.documents = []
        self.load_documents(txt_folder_path)

    def load_documents(self, folder_path: str):
        # Load all text documents from the specified folder
        for file_name in os.listdir(folder_path):
            if file_name.endswith(".txt"):
                file_path = os.path.join(folder_path, file_name)
                text = self.extract_text_from_txt(file_path)
                if text.strip():
                    self.documents.append(text)
                else:
                    print(f"File {file_name} is empty or contains only whitespace.")
        if not self.documents:
            raise ValueError("No data to process; all files are empty.")

    def extract_text_from_txt(self, txt_path: str) -> str:
        # Extract text content from a TXT file
        with open(txt_path, "r", encoding="utf-8") as file:
            return file.read()

rag_store = None

# Initialize document store during application startup
@router.on_event("startup")
def initialize_rag():
    global rag_store
    txt_folder_path = "./documents"  # Folder containing text documents
    rag_store = DocumentStore(txt_folder_path)

# Endpoint to validate documents
@router.post("/validate-document", response_model=DocumentCheckResult)
async def validate_document(file: UploadFile):
    # Check if the file type is supported
    if file.content_type not in ["image/jpeg", "image/png", "application/pdf"]:
        raise HTTPException(status_code=400, detail="Unsupported file type. Only JPEG, PNG, and PDF are allowed.")

    # Convert PDF to images or encode image file as Base64
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

    # Analyze aggregated results
    aggregated_result = analyze_document_results(results)
    return aggregated_result

# Process an image using Grok Vision model
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

# Analyze the results of document validation
def analyze_document_results(results: List[dict]) -> DocumentCheckResult:
    required_fields = ["Name", "Date of Birth", "Document Number", "Expiration Date"]
    missing_fields = []
    errors = []
    for field in required_fields:
        if not any(field in result["content"] for result in results if "content" in result):
            missing_fields.append(field)
    is_valid = len(missing_fields) == 0
    return DocumentCheckResult(is_valid=is_valid, missing_fields=missing_fields, errors=errors)

# Endpoint for generating AI-assisted responses based on user location
@router.post("/generate-response", response_model=List[str])
async def ask_question(request: QuestionRequest, location: Location = Depends(get_user_location)):
    # Customize response based on location
    region_message = f" in {location.region}" if location.region else ""
    question_with_location = f"Question: {request.question}{region_message}"
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant for DMV-related processes and documents."},
        {"role": "user", "content": question_with_location}
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

# Endpoint to handle location-based requests
@router.post("/process-user-data", response_model=LocationResponse)
async def process_user_data(
    user_request: UserRequest, 
    location: Location = Depends(get_user_location)
):
    # Log the user location
    print(f"Processing data for user in {location.country}, {location.region}")

    # Simulate some processing
    return LocationResponse(
        message=f"Data processed successfully for user in {location.country}, {location.region}",
        location=location
    )

# Endpoint to fetch location without requiring additional data
@router.get("/get-location", response_model=Location)
async def get_location(location: Location = Depends(get_user_location)):
    return location
