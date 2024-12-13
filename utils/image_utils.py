import base64
from PIL import Image
import io

def encode_image_to_base64(image_file):
    image_file.seek(0) 
    image_data = image_file.read()
    return base64.b64encode(image_data).decode('utf-8')

def convert_pdf_to_images(pdf_path: str) -> list:
    """Konwertuje plik PDF na listę obrazów w formacie PIL."""
    from pdf2image import convert_from_path
    return convert_from_path(pdf_path)

def pil_image_to_base64(pil_image: Image.Image) -> str:
    """Konwertuje obiekt obrazu PIL na Base64."""
    buffer = io.BytesIO()
    pil_image.save(buffer, format="JPEG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")
