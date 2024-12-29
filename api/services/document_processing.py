from fastapi import UploadFile, HTTPException
from ..utils.image_utils import encode_image_to_base64, convert_pdf_to_images, pil_image_to_base64
from .grok_vision import process_image_with_grok
from .grok_text import process_document_with_text_model
import tempfile

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

        aggregated_results = []
        for base64_image in base64_images:
            result = process_image_with_grok(base64_image)
            aggregated_results.append(result)

        return process_document_with_text_model(aggregated_results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing the document: {str(e)}")
