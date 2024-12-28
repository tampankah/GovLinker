import base64
from PIL import Image
import io
from typing import List
from pdf2image import convert_from_path

def encode_image_to_base64(image_file: io.BytesIO) -> str:
    """Encodes an image file to Base64."""
    try:
        image_file.seek(0)  # Resets the file pointer to the beginning
        image_data = image_file.read()
        return base64.b64encode(image_data).decode('utf-8')
    except Exception as e:
        raise ValueError(f"Error encoding image to Base64: {e}")

def convert_pdf_to_images(pdf_path: str, dpi: int = 200) -> List[Image.Image]:
    """Converts a PDF file into a list of PIL images.

    Args:
        pdf_path (str): Path to the PDF file.
        dpi (int): Image resolution in DPI (default is 200).

    Returns:
        List[Image.Image]: List of images in PIL format.
    """
    try:
        images = convert_from_path(pdf_path, dpi=dpi)
        return images
    except Exception as e:
        raise ValueError(f"Error converting PDF to images: {e}")

def pil_image_to_base64(pil_image: Image.Image, format: str = "JPEG") -> str:
    """Converts a PIL image object to Base64.

    Args:
        pil_image (Image.Image): PIL image object.
        format (str): Image format for saving (e.g., 'JPEG', 'PNG').

    Returns:
        str: Image encoded as a Base64 string.
    """
    try:
        buffer = io.BytesIO()
        pil_image.save(buffer, format=format)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception as e:
        raise ValueError(f"Error converting PIL image to Base64: {e}")
