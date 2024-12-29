from pydantic import BaseModel
from typing import List

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
  