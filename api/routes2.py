from fastapi import APIRouter, UploadFile, HTTPException
from pydantic import BaseModel
from typing import List
from api.services.openai_service import process_image_with_grok, process_document_with_text_model
from api.utils.image_utils import encode_image_to_base64, convert_pdf_to_images, pil_image_to_base64
import tempfile
import logging
import os

router = APIRouter()

# Mock database containing document information
DOCUMENTS_DB = {
    "driver_license_application": {
        "document_name": "Driver's License Application Form",
        "url": "https://www.dps.texas.gov/internetforms/forms/dl-14a.pdf"
    },
    # More document data can be added here...
}

# API endpoint for document validation
@router.post("/validate-document")
async def validate_document(file: UploadFile):
    if file.content_type not in ["image/jpeg", "image/png", "application/pdf"]:
        raise HTTPException(status_code=400, detail="Unsupported file type. Only JPEG, PNG, and PDF are allowed.")

    try:
        base64_images = []

        if file.content_type == "application/pdf":
            with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as temp_pdf:
                temp_pdf.write(file.file.read())
                temp_pdf.flush()
                images = convert_pdf_to_images(temp_pdf.name)
                base64_images = [pil_image_to_base64(image) for image in images]
        else:
            base64_image = encode_image_to_base64(file.file)
            base64_images = [base64_image]

        # Process image with Grok Vision Model
        aggregated_results = [process_image_with_grok(base64_image) for base64_image in base64_images]

        # Further processing with the Grok Text model
        response = process_document_with_text_model(aggregated_results)
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing the document: {str(e)}")

# API endpoint for generating responses
@router.post("/generate-response", response_model=List[str])
def ask_question(request: QuestionRequest):
    """
    Responds to user's question, potentially including document links.
    """
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
