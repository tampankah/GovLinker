from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..routes.document_db import DOCUMENTS_DB
from ..routes.grok_utils import client, CHAT_MODEL_NAME

class QuestionRequest(BaseModel):
    question: str

router = APIRouter(prefix="/questions", tags=["Questions"])

@router.post("/generate-response")
def ask_question(request: QuestionRequest):
    base_messages = [
        {
            "role": "system",
            "content": ("You are a funny, friendly, and incredibly knowledgeable assistant who works at the DMV "
                        "and provides helpful guidance on forms and processes.")
        },
        {"role": "user", "content": request.question}
    ]

    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL_NAME,
            messages=base_messages,
        )
        initial_message = response.choices[0].message
        requires_document = any(keyword in request.question.lower() for keyword in ["form", "document", "application", "download"])

        document_links_html = ""
        if requires_document:
            for doc_key, doc_info in DOCUMENTS_DB.items():
                document_links_html += f'<p><a href="{doc_info["url"]}" download="{doc_info["document_name"]}">{doc_info["document_name"]}</a></p>'

        grok_response = (
            f"Sure thing! Here are the documents: {document_links_html} Let me know if you'd like help with them."
            if requires_document else
            initial_message.content
        )
        return [grok_response]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing the request: {str(e)}")
