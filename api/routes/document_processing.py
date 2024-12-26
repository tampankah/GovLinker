from fastapi import APIRouter, UploadFile, HTTPException
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
                            "text": "Analyze this document and extract all fields. Split the output into two categories: 'completed_fields' and 'empty_fields'. For 'completed_fields', include the 'field_name' and the 'field_value'. For 'empty_fields', include only the 'field_name'. Additionally, identify and validate required fields, and include their statuses (e.g., 'filled' or 'missing') in the response. Return the results in a clear JSON format structured as follows:\n{\n  \"completed_fields\": [\n    { \"field_name\": \"<field_label>\", \"field_value\": \"<value_entered>\" }\n  ],\n  \"empty_fields\": [\n    { \"field_name\": \"<field_label>\" }\n  ],\n  \"required_field_statuses\": [\n    { \"field_name\": \"<field_label>\", \"status\": \"filled\" or \"missing\" }\n  ]\n}"
                        }

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
@router.post("/validate")
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
                {"role": "system", "content": "You are a helpful, friendly, and clear assistant with expertise in analyzing and solving form-related issues. Your task is to provide users with personalized guidance based on the following extracted form data:\n\n1. **Completed Fields**:\n   These are the fields that the user has already filled out:\n   ```\n   {completed_fields}\n   ```\n   - Acknowledge the user's effort in completing these fields.\n   - Verify if the values provided are logical or valid based on common form standards.\n\n2. **Empty Fields**:\n   These are the fields that the user has not yet filled out:\n   ```\n   {empty_fields}\n   ```\n   - For each empty field, explain why this field is important and what information is required.\n   - Provide clear instructions on how to complete each field.\n   - If applicable, include examples or tips to help the user fill out the field accurately.\n\n3. **Required Field Statuses**:\n   Validation results of required fields:\n   ```\n   {required_field_statuses}\n   ```\n   - Identify required fields that are still missing or incomplete.\n   - Prioritize missing required fields and provide step-by-step guidance to address these issues.\n\n### **Output Structure**:\n- Start with a friendly acknowledgment of the user's effort.\n- Highlight the completed fields and confirm their validity (if relevant).\n- Provide a detailed step-by-step guide for each empty field, prioritizing required fields marked as 'missing'.\n- Use a helpful, supportive tone and add examples where appropriate.\n- End with a motivational statement encouraging the user to complete the remaining fields.\n\n### Example Output:\n\"Great work filling out the form so far! Here's what I noticed:\n\n✅ **Completed Fields**:\n- **Full Name**: John Doe\n- **Date of Birth**: 1990-01-01\n   These fields look good!\n\n⚠️ **Fields That Need Your Attention**:\n- **Email Address**: This is missing. Please enter your email address, e.g., john.doe@example.com, so we can contact you if needed.\n- **Phone Number**: This is empty. Add a phone number in this format: (123) 456-7890.\n\n🚨 **Required Fields Missing**:\n- **Address**: This field is critical for processing your request. Enter your full mailing address, such as '123 Main St, Springfield, IL 12345'.\n\nKeep going! You're almost there—let's finish strong! 📝\"\n\nNow generate tailored and supportive help text for the user based on the provided data."},
                {"role": "user", "content": document_context},
            ],
        )
        logger.debug("Received response from Grok Text model: %s", response)

        return response.choices[0].message  # Return the generated message as response

    except Exception as e:
        logger.error("Error processing with Grok Text model: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Error processing with Grok Text model: {str(e)}")