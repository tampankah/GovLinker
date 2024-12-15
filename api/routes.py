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

@router.post("/validate-document", response_model=DocumentCheckResult)
async def validate_document(file: UploadFile):
    """
    Validates the document uploaded by the user (JPEG, PNG, or PDF).
    """
    # Validate the file type
    if file.content_type not in ["image/jpeg", "image/png", "application/pdf"]:
        raise HTTPException(status_code=400, detail="Unsupported file type. Only JPEG, PNG, and PDF are allowed.")

    base64_images = []

    try:
        if file.content_type == "application/pdf":
            # Save the uploaded PDF to a temporary file
            with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as temp_pdf:
                temp_pdf.write(file.file.read())
                temp_pdf.flush()  # Ensure all data is written to disk
                images = convert_pdf_to_images(temp_pdf.name)  # Convert PDF to images
                base64_images = [pil_image_to_base64(image) for image in images]
        else:
            # Encode image to base64 directly
            base64_image = encode_image_to_base64(file.file)
            base64_images = [base64_image]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing the document: {str(e)}")

    # Process each image with the vision model
    results = []
    for image in base64_images:
        result = process_image_with_grok(image) 
        results.append(result)

    # Analyze the aggregated results
    aggregated_result = analyze_document_results(results)
    return aggregated_result

def process_image_with_grok(base64_image: str) -> dict:
    """
    Sends the base64-encoded image to the Grok Vision model for analysis.
    """
    try:
        # Send the image to the vision model
        logger.debug("Sending request to Grok Vision model.")
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
                            "text": "Extract and validate the fields in this document. Identify required fields and their statuses.",
                        },
                    ],
                }
            ],
        )

        # Log the raw response for debugging purposes
        logger.debug("Received response from Grok Vision model: %s", response)

        # Return the relevant part of the response
        return response.choices[0].message
    except Exception as e:
        # Log any errors that occur during the request
        logger.error("Error while processing image with Grok Vision model: %s", str(e))
        raise

def analyze_document_results(results: List[str]) -> DocumentCheckResult:
    """
    Analyzes the results from the vision model, extracting and categorizing required fields.
    Classifies them into required fields, missing fields, filling fields, and provides guidance to fill them.

    Args:
        results (List[str]): A list of base64-encoded images to analyze.

    Returns:
        DocumentCheckResult: The analysis results indicating validity, missing fields, errors, and guidance.
    """
    missing_fields = []
    filling_fields = []
    filled_fields = []
    required_fields = []  # Grok will decide this

    errors = []
    field_guidance = []

    # Ensure that the input results are a list of base64-encoded images
    if not isinstance(results, list) or not all(isinstance(image, str) for image in results):
        errors.append("Invalid input: 'results' must be a list of base64-encoded image strings.")
        return DocumentCheckResult(is_valid=False, missing_fields=missing_fields, errors=errors)

    extracted_fields = []  # Store extracted fields from all images

    try:
        for image in results:
            # Send image to Grok Vision model for analysis
            response = client.chat.completions.create(
                model=VISION_MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image}",
                                    "detail": "high",
                                },
                            },
                            {
                                "type": "text",
                                "text": "Identify required fields in the document and their current status. Return required, filled, missing, and partially filled fields.",
                            },
                        ],
                    }
                ],
            )

            # Extract the response content and validate
            vision_output = response.choices[0].message.get("content", {})
            if isinstance(vision_output, dict):
                if "required_fields" in vision_output:
                    required_fields.extend(vision_output["required_fields"])
                if "fields" in vision_output:
                    extracted_fields.extend(vision_output["fields"])
            else:
                errors.append("Invalid response from vision model for one of the images.")
    except Exception as e:
        errors.append(f"Error during vision model processing: {str(e)}")
        return DocumentCheckResult(is_valid=False, missing_fields=missing_fields, errors=errors)

    # Categorize the extracted fields
    for field in required_fields:
        matching_field = next(
            (extracted_field for extracted_field in extracted_fields if field.lower() in extracted_field.lower()), 
            None
        )

        if matching_field:
            if 'incomplete' in matching_field.lower():  # If the field is partially filled
                filling_fields.append(field)
            else:  # If the field is completely filled
                filled_fields.append(field)
        else:
            missing_fields.append(field)

    # Now we will pass missing and filling fields to the text generation model for guidance
    if missing_fields or filling_fields:
        try:
            # Prepare the question for the chat model to generate assistance text
            missing_or_filling_fields_text = ", ".join(missing_fields + filling_fields)
            question = f"The following required fields are missing or partially filled: {missing_or_filling_fields_text}. " \
                       "Can you provide fun and easy ways for the user to fill these fields correctly?"

            # Create a new agent (text generation model) to assist the user
            response = client.chat.completions.create(
                model=CHAT_MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a fun and helpful assistant guiding users to complete their documents in an easy way."},
                    {"role": "user", "content": question},
                ],
            )

            # Extract the generated guidance from the response
            guidance_message = response.choices[0].message['content']
            field_guidance.append(guidance_message)  # Add the generated guidance for the user

        except Exception as e:
            errors.append(f"Error processing with chat model: {str(e)}")

    # Determine if the document is valid (no missing fields)
    is_valid = len(missing_fields) == 0

    # Return the results with field statuses, errors, and any additional guidance
    return DocumentCheckResult(
        is_valid=is_valid,
        required_fields=required_fields,  # Return the dynamically determined required fields
        missing_fields=missing_fields,
        filled_fields=filled_fields,
        filling_fields=filling_fields,
        errors=errors,
        field_guidance=field_guidance  # Guidance generated by the text model for filling fields
    )

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
