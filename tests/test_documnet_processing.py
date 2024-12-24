import pytest
from fastapi.testclient import TestClient
from main import app  # Assuming the FastAPI app is in main.py
from io import BytesIO
import os

# Create a TestClient instance for testing
client = TestClient(app)

# Test for valid document upload
def test_valid_pdf_document():
    # Load a sample PDF file (you can place a test PDF in the tests directory)
    with open("tests/sample_document.pdf", "rb") as f:
        response = client.post(
            "/validate-document", files={"file": ("sample_document.pdf", f, "application/pdf")}
        )
    
    assert response.status_code == 200
    assert "completed_fields" in response.json()
    assert "empty_fields" in response.json()

# Test for invalid file type (e.g., uploading a text file)
def test_invalid_file_type():
    # Upload a text file
    with open("tests/sample_document.txt", "rb") as f:
        response = client.post(
            "/validate-document", files={"file": ("sample_document.txt", f, "text/plain")}
        )
    
    assert response.status_code == 400
    assert response.json() == {"detail": "Unsupported file type. Only JPEG, PNG, and PDF are allowed."}

# Test for valid image file upload
def test_valid_image():
    # Upload a sample JPEG image
    with open("tests/sample_image.jpg", "rb") as f:
        response = client.post(
            "/validate-document", files={"file": ("sample_image.jpg", f, "image/jpeg")}
        )

    assert response.status_code == 200
    assert "completed_fields" in response.json()
    assert "empty_fields" in response.json()

# Test for empty file (no file uploaded)
def test_empty_file():
    response = client.post("/validate-document")
    assert response.status_code == 422  # Unprocessable Entity

# Test for /generate-response endpoint (simple question test)
def test_generate_response():
    # Sample request to the /generate-response endpoint
    payload = {"question": "How do I apply for a driver's license?"}
    response = client.post("/generate-response", json=payload)
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0
    assert "<html>" in response.json()[0]  # Check if HTML content is included in response

# Test for a missing document type (in /validate-document)
def test_missing_document_type():
    payload = {"document_type": "nonexistent_type"}
    response = client.post("/validate-document", json=payload)
    assert response.status_code == 404
    assert response.json() == {"detail": "Document type not found in database."}

# Test for the case when an image can't be processed by Grok Vision
def test_invalid_image_processing():
    # We simulate an error in image processing by passing invalid base64 or corrupted image
    response = client.post(
        "/validate-document", files={"file": ("invalid_image.jpg", BytesIO(b"invalid"), "image/jpeg")}
    )
    
    assert response.status_code == 500
    assert "Error processing the document" in response.json()['detail']
# e 33
