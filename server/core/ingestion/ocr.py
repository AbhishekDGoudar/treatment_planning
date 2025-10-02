import pytesseract
from PIL import Image

def ocr_image(path: str) -> str:
    return pytesseract.image_to_string(Image.open(path))
