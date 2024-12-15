from fastapi import APIRouter, UploadFile, HTTPException
from pydantic import BaseModel
from typing import List
import tempfile
import logging
from utils.image_utils import encode_image_to_base64, convert_pdf_to_images, pil_image_to_base64
import os
from openai import OpenAI

# API key and model names for OpenAI integration
XAI_API_KEY = os.getenv("XAI_API_KEY")  # Retrieve API key from environment variable
VISION_MODEL_NAME = "grok-vision-beta"  # Vision model name
CHAT_MODEL_NAME = "grok-beta"  # Chat model name

# Initialize OpenAI client
client = OpenAI(
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1", 
)

# Define FastAPI router
router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Mock database containing document information
DOCUMENTS_DB = {
    "driver_license_application": {
        "document_name": "Driver's License Application Form",
        "url": "https://www.dps.texas.gov/internetforms/forms/dl-14a.pdf"
    },
    "id_card_application": {
        "document_name": "State ID Application Form",
        "url": "https://www.honolulu.gov/rep/site/csd/onlineforms/csd-stateidapplicationform.pdf"
    },
    "vehicle_registration": {
        "document_name": "Vehicle Registration Form",
        "url": "https://www.nj.gov/mvc/pdf/vehicles/BA-49.pdf"
    },
}

# Pydantic models for request and response validation
class DocumentCheckResult(BaseModel):
    """
    Model representing the result of document validation.
    """
    is_valid: bool 
    missing_fields: List[str]  # List of missing fields in the document
    errors: List[str]  # List of validation errors

class QuestionRequest(BaseModel):
    """
    Model representing the user question in the /generate-response endpoint.
    """
    question: str  # User's question

class DocumentRequest(BaseModel):
    """
    Model for specifying the type of document in the /validate-document endpoint.
    """
    document_type: str  # Document type identifier

class DocumentResponse(BaseModel):
    """
    Model representing the response containing document details.
    """
    document_name: str  # Name of the document
    url: str  # URL for downloading the document

class FunctionCallResultMessage(BaseModel):
    """
    Model for embedding a tool call result message with HTML content.
    """
    role: str
    content: str
    tool_call_id: str

# Function to handle sending image data to Grok Vision model
def process_image_with_grok(base64_image: str) -> dict:
    """
    Sends a base64-encoded image to the Grok Vision model for analysis.
    """
    try:
        logger.debug("Sending request to Grok Vision model.")
        response = client.chat.completions.create(
            model=VISION_MODEL_NAME,  # Vision model name
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
                            "text": "Extract and validate the fields in this document. Identify required fields and their statuses.",
                        },
                    ],
                }
            ],
        )
        logger.debug("Received response from Grok Vision model: %s", response)
        return response.choices[0].message  # Return the structured result
    except Exception as e:
        logger.error("Error while processing image with Grok Vision model: %s", str(e))
        if "404" in str(e):
            raise HTTPException(status_code=404, detail="The requested Grok Vision model does not exist or is inaccessible.")
        raise HTTPException(status_code=500, detail=f"Error while processing image: {str(e)}")


# Main API endpoint for document validation
@router.post("/validate-document")
async def validate_document(file: UploadFile):
    """
    Validates the document uploaded by the user (JPEG, PNG, or PDF).
    """
    # Validate the file type
    if file.content_type not in ["image/jpeg", "image/png", "application/pdf"]:
        raise HTTPException(status_code=400, detail="Unsupported file type. Only JPEG, PNG, and PDF are allowed.")

    try:
        base64_images = []

        if file.content_type == "application/pdf":
            # Convert PDF pages to images
            with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as temp_pdf:
                temp_pdf.write(file.file.read())
                temp_pdf.flush()
                images = convert_pdf_to_images(temp_pdf.name)
                base64_images = [pil_image_to_base64(image) for image in images]
        else:
            # Encode the single image file to base64
            base64_image = encode_image_to_base64(file.file)
            base64_images = [base64_image]

        # Process each image using Grok Vision model
        aggregated_results = []
        for base64_image in base64_images:
            result = process_image_with_grok(base64_image)
            aggregated_results.append(result)

        # Pass the aggregated result to the Grok Text model for further processing
        response = process_document_with_text_model(aggregated_results)
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing the document: {str(e)}")


# Function to process aggregated results with the Grok Text model
def process_document_with_text_model(aggregated_results: list) -> dict:
    """
    Processes the aggregated results using the Grok Text model for final response.
    """
    document_context = " ".join([str(result) for result in aggregated_results])

    try:
        # Send the aggregated document context to the Grok Text model for processing
        response = client.chat.completions.create(
            model=CHAT_MODEL_NAME,  # Chat model name
            messages=[
                {"role": "system", "content": "You are a helpful assistant guiding users to complete their documents."},
                {"role": "user", "content": document_context},
            ],
        )
        logger.debug("Received response from Grok Text model: %s", response)

        return response.choices[0].message  # Return the generated message as response

    except Exception as e:
        logger.error("Error processing with Grok Text model: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Error processing with Grok Text model: {str(e)}")
        
@router.post("/generate-response", response_model=List[str])
def ask_question(request: QuestionRequest):
    """
    Responds to the user's question and includes tool-generated HTML content in the response.
    """
    # Define the base message sequence
    base_messages = [
        {"role": "system", "content": "You are a funny and helpful assistant with DMV expertise."},
        {"role": "user", "content": f"Question: {request.question}"}
    ]

    try:
        # Initial API call to the chat model
        response = client.chat.completions.create(
            model=CHAT_MODEL_NAME,
            messages=base_messages,
        )

        # Extract the first response from the chat model
        message = response.choices[0].message

        # Generate HTML content with links to documents
        document_links_html = ""
        for doc_key, doc_info in DOCUMENTS_DB.items():
            document_links_html += f'<p><a href="{doc_info["url"]}" download="{doc_info["document_name"]}">{doc_info["document_name"]}</a></p>'

        # Define the tool-generated HTML message with document links
        function_call_result_message = {
            "role": "tool",
            "content": f"<html><body><h1>DMV Assistance Page</h1><p>This is the generated HTML content for the user's query.</p>{document_links_html}</body></html>",
            "tool_call_id": None,
        }

        # Prepare a follow-up chat completion request with the tool call result
        follow_up_messages = base_messages + [response.choices[0].message, function_call_result_message]

        # Make the second API call with the tool result embedded
        final_response = client.chat.completions.create(
            model=CHAT_MODEL_NAME,
            messages=follow_up_messages,
        )

        # Extract the final response content
        answer = final_response.choices[0].message.content
        utf8_response = answer.encode("utf-8").decode("utf-8")  # Ensure UTF-8 compatibility

        return [utf8_response]

    except Exception as e:
        # Handle exceptions and raise HTTP errors
        raise HTTPException(status_code=500, detail=f"Error processing the request: {str(e)}")
