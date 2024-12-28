import base64
from PIL import Image
import io
import PyPDF2

def encode_image_to_base64(image_file):
    image_file.seek(0) 
    image_data = image_file.read()
    return base64.b64encode(image_data).decode('utf-8')

def convert_pdf_to_images(pdf_path):
  """
  Converts a PDF file to a list of PIL Image objects.
  """
  try:
    with open(pdf_path, 'rb') as pdf_file:
      pdf_reader = PyPDF2.PdfReader(pdf_file)
      images = []
      for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]
        image = page.extract_image(format='RGB')  # Extract page as RGB image
        images.append(image)
      return images
  except Exception as e:
    
    raise Exception("Error converting PDF to images")

def pil_image_to_base64(pil_image: Image.Image) -> str:
    """Konwertuje obiekt obrazu PIL na Base64."""
    buffer = io.BytesIO()
    pil_image.save(buffer, format="JPEG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")
