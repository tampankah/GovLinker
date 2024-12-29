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
    missing_fields: List[str]  
    errors: List[str]  

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
        # Log the request before sending
        logger.debug("Sending request to Grok Vision model.")

        # Call the Grok Vision model with the provided base64 image and analysis instructions
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
                                "detail": "high",  # Image detail level
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "Analyze this document and extract all fields. Split the output into two categories: "
                                "'completed_fields' and 'empty_fields'. For 'completed_fields', include the "
                                "'field_name' and the 'field_value'. For 'empty_fields', include only the 'field_name'. "
                                "Additionally, identify and validate required fields, and include their statuses (e.g., "
                                "'filled' or 'missing') in the response. Return the results in a clear JSON format "
                                "structured as follows:\n{\n  \"completed_fields\": [\n    { \"field_name\": \"<field_label>\", "
                                "\"field_value\": \"<value_entered>\" }\n  ],\n  \"empty_fields\": [\n    { \"field_name\": "
                                "\"<field_label>\" }\n  ],\n  \"required_field_statuses\": [\n    { \"field_name\": "
                                "\"<field_label>\", \"status\": \"filled\" or \"missing\" }\n  ]\n}\n\nPlease note that the "
                                "'X' next to the 'Signature of Applicant' label indicates the location where the applicant is "
                                "required to sign. It does not mean that the signature has already been provided or that any "
                                "information has been marked. The applicant must place their signature in the designated area "
                                "to complete the form."
                            )
                        }
                    ]
                }
            ],
        )

        # Log the response from the Grok Vision model
        logger.debug("Received response from Grok Vision model: %s", response)

        # Return the structured response from the model
        return response.choices[0].message

    except Exception as e:
        # Log the error if something goes wrong
        logger.error("Error while processing image with Grok Vision model: %s", str(e))
        
        # Handle specific error cases
        if "404" in str(e):
            raise HTTPException(status_code=404, detail="The requested Grok Vision model does not exist or is inaccessible.")
        
        # General error handling
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
                {
                    "role": "system",
                    "content": """You are a helpful, friendly, and clear assistant with expertise in analyzing and solving form-related issues. 
                                Provide personalized guidance based on the extracted form data:

                    1. **Completed Fields**:
                       - Acknowledge the user's effort.
                       - Verify if the values provided are logical and valid.
                       ``` 
                       {completed_fields}
                       ```

                    2. **Empty Fields**:
                       - Explain the importance of each missing field.
                       - Provide instructions and examples to help complete it.
                       ``` 
                       {empty_fields}
                       ```

                    3. **Required Field Statuses**:
                       - Identify required fields that are incomplete.
                       - Prioritize missing required fields and guide the user to address them.
                       ``` 
                       {required_field_statuses}
                       ```

                    ### Output Structure:
                    - Start with an acknowledgment of the user's effort.
                    - Highlight completed fields and confirm their validity.
                    - Provide step-by-step guidance for each missing field, prioritizing required ones.
                    - Use a supportive tone with examples where relevant.
                    - End with encouragement to finish the form.

                    ### Example Output:
                    "Great work so far! Here's what I noticed:

                    ✅ **Completed Fields**:
                    - **Full Name**: John Doe
                    - **Date of Birth**: 1990-01-01
                       These look good!

                    ⚠️ **Fields That Need Attention**:
                    - **Email Address**: Missing. Please enter your email, e.g., john.doe@example.com.

                    🚨 **Required Fields Missing**:
                    - **Address**: Enter your full address, e.g., '123 Main St, Springfield, IL 12345'.

                    Keep going, you're almost there! 📝"

                    Generate helpful, supportive text based on the provided data."""
                },
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
    Responds to the user's question, facilitating a longer, intelligent conversation and providing document links when needed.
    """
    # Define the base message sequence
    base_messages = [
        {
            "role": "system",
            "content": "You are a funny, friendly, and incredibly knowledgeable assistant who works at the DMV (Department of Motor Vehicles). "
                       "You are an expert in all DMV processes, forms, regulations, and problem-solving scenarios. "
                       "Your job is to help users in a lighthearted, easy-to-understand, and supportive way. "
                       "Explain complex processes in simple terms, use relatable analogies, and add a touch of humor to make DMV topics less stressful. "
                       "Always stay polite, positive, and provide clear, actionable solutions to any DMV-related questions or issues."
        }
    ]

    # Append the user query to the message sequence
    base_messages.append({"role": "user", "content": request.question})

    try:
        # Initial API call to the chat model
        response = client.chat.completions.create(
            model=CHAT_MODEL_NAME,
            messages=base_messages,
        )

        # Extract the first response from the chat model
        initial_message = response.choices[0].message

        # Check if the user's query involves document-related topics
        requires_document = any(keyword in request.question.lower() for keyword in ["form", "document", "application", "download"])

        # If documents are relevant, prepare document links HTML
        document_links_html = ""
        if requires_document:
            for doc_key, doc_info in DOCUMENTS_DB.items():
                document_links_html += f'<p><a href="{doc_info["url"]}" download="{doc_info["document_name"]}">{doc_info["document_name"]}</a></p>'

        # Create an interactive response depending on the context
        if requires_document:
            grok_response = (
                f"Sure thing! It sounds like you need some official documents. Here are the ones I think will help you: "
                f"{document_links_html} Let me know if you'd like help filling them out or understanding what to do next!"
            )
        else:
            grok_response = (
                f"Great question! {initial_message.content} "
                f"If at any point you think a DMV document might help, just let me know!"
            )

        # Prepare follow-up messages for continued conversation
        follow_up_messages = base_messages + [initial_message, {"role": "assistant", "content": grok_response}]

        # Make the second API call to refine or extend the response
        final_response = client.chat.completions.create(
            model=CHAT_MODEL_NAME,
            messages=follow_up_messages,
        )

        # Extract and process the final response content
        final_answer = final_response.choices[0].message.content
        utf8_response = final_answer.encode("utf-8").decode("utf-8")  # Ensure UTF-8 compatibility

        return [utf8_response]

    except Exception as e:
        # Handle exceptions and raise HTTP errors
        raise HTTPException(status_code=500, detail=f"Error processing the request: {str(e)}")
