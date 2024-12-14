from fastapi import APIRouter, UploadFile, HTTPException
from pydantic import BaseModel
from typing import List
from utils.image_utils import encode_image_to_base64, convert_pdf_to_images, pil_image_to_base64
import os
from openai import OpenAI

XAI_API_KEY = os.getenv("XAI_API_KEY")  
VISION_MODEL_NAME = "grok-vision-beta" 
CHAT_MODEL_NAME = "grok-beta"  

client = OpenAI(
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1", 
)

router = APIRouter()


# Mocked documents
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


class DocumentCheckResult(BaseModel):
    """
    Model to represent the result of document validation.
    """
    is_valid: bool 
    missing_fields: List[str]  
    errors: List[str] 

class QuestionRequest(BaseModel):
    """
    Model for the user question in the /generate-response endpoint.
    """
    question: str  

class DocumentRequest(BaseModel):
    """
    Model for specifying the type of document in the /validate-document endpoint.
    """
    document_type: str  

class DocumentResponse(BaseModel):
    """
    Model for the response that contains document details.
    """
    document_name: str 
    url: str 

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
    """
    Sends the base64-encoded image to Grok's vision model for analysis.
    """
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
    """
    Analyzes the results from the vision model and checks for missing required fields.
    """
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
    """
    Responds to the user's question and includes tool-generated HTML content in the response.
    """
    # Define the base message sequence
    base_messages = [
        {"role": "system", "content": "You are a funny and helpful assistant with DMV expertise."},
        {"role": "user", "content": f"Question: {request.question}"}
    ]

    try:
        print(f"Base messages: {base_messages}")  # Debug print 1: Check base messages structure

        # Initial API call to the chat model
        response = client.chat.completions.create(
            model=CHAT_MODEL_NAME,
            messages=base_messages,
        )
        print(f"API response: {response}")  # Debug print 2: Check the response from the chat model

        # Extract the first response from the chat model using the correct attribute
        message = response.choices[0].message
        print(f"Message content: {message.content}")  # Debug print 3: Check the message content

        # Check if tool_calls exist, in case the response involves using tools (no tool calls in the current example)
        tool_call_id = None
        if hasattr(message, 'tool_calls') and message.tool_calls:
            tool_call_id = message.tool_calls[0].get('id', None)
        print(f"Extracted tool call ID: {tool_call_id}")  # Debug print 4: Check if tool call ID is extracted properly

        if tool_call_id is None:
            print("No tool call ID found in the response.")  # Debug print 5: If no tool call ID is found

        # Generate HTML content with links to documents
        document_links_html = ""
        for doc_key, doc_info in DOCUMENTS_DB.items():
            document_links_html += f'<p><a href="{doc_info["url"]}" download="{doc_info["document_name"]}">{doc_info["document_name"]}</a></p>'
        print(f"Generated HTML document links: {document_links_html}")  # Debug print 6: Check the generated HTML links

        # Define the tool-generated HTML message with document links
        function_call_result_message = {
            "role": "tool",
            "content": f"<html><body><h1>DMV Assistance Page</h1><p>This is the generated HTML content for the user's query.</p>{document_links_html}</body></html>",
            "tool_call_id": tool_call_id,
        }
        print(f"Function call result message: {function_call_result_message}")  # Debug print 7: Check the generated tool call result message

        # Prepare a follow-up chat completion request with the tool call result
        follow_up_messages = base_messages + [response.choices[0].message, function_call_result_message]
        print(f"Follow-up messages: {follow_up_messages}")  # Debug print 8: Check the follow-up messages sent to the chat model

        # Make the second API call with the tool result embedded
        final_response = client.chat.completions.create(
            model=CHAT_MODEL_NAME,
            messages=follow_up_messages,
        )
        print(f"Final response: {final_response}")  # Debug print 9: Check the final response from the chat model

        # Extract the final response content
        answer = final_response.choices[0].message.content
        utf8_response = answer.encode("utf-8").decode("utf-8")  # Ensure UTF-8 compatibility
        print(f"Final UTF-8 response: {utf8_response}")  # Debug print 10: Check the final UTF-8 response

        return [utf8_response]

    except Exception as e:
        print(f"Error: {str(e)}")  # Debug print 11: Catch any errors and print them
        raise HTTPException(status_code=500, detail=f"Error processing the request: {str(e)}")
