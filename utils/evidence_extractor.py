# utils/evidence_extractor.py
"""
Evidence extraction utilities for processing evidence artifacts (PDFs, images, screenshots).
Supports text extraction from PDFs and OCR from images.
"""
import fitz  # PyMuPDF
from pathlib import Path
from PIL import Image
import re

# Optional OCR dependencies
try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    pytesseract = None

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    np = None


def clean_text(text):
    """Normalize extracted text by removing extra spaces, headers, etc."""
    if not text:
        return ""
    text = str(text).replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_text_from_pdf(file_path):
    """Extract text content from a PDF evidence file using PyMuPDF."""
    text = ""
    try:
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text("text") + "\n"
        return clean_text(text)
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF {file_path}: {e}")


def preprocess_image_for_ocr(image_path):
    """
    Preprocess image to improve OCR accuracy.
    Handles common issues like low contrast, noise, etc.
    """
    if not CV2_AVAILABLE:
        raise ImportError("OpenCV (cv2) is required for image preprocessing. Install with: pip install opencv-python")
    
    # Read image
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"Could not read image file: {image_path}")
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply denoising
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    
    # Apply thresholding to get binary image
    _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Optional: Apply morphological operations to clean up
    kernel = np.ones((1, 1), np.uint8)
    processed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    
    return processed


def extract_text_from_image(image_path, use_preprocessing=True):
    """
    Extract text from an image file using OCR (Tesseract).
    Supports screenshots, scanned documents, and other image formats.
    
    Note: Requires Tesseract OCR to be installed on the system.
    - Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
    - macOS: brew install tesseract
    - Linux: sudo apt-get install tesseract-ocr (Ubuntu/Debian)
    
    Args:
        image_path: Path to the image file
        use_preprocessing: Whether to preprocess image before OCR (recommended)
    
    Returns:
        Extracted text string
    
    Raises:
        ValueError: If Tesseract is not installed or image processing fails
    """
    if not PYTESSERACT_AVAILABLE:
        raise ImportError(
            "pytesseract is required for image OCR. Install with: pip install pytesseract\n"
            "Also ensure Tesseract OCR is installed on your system:\n"
            "- Windows: https://github.com/UB-Mannheim/tesseract/wiki\n"
            "- macOS: brew install tesseract\n"
            "- Linux: sudo apt-get install tesseract-ocr"
        )
    
    try:
        # Check if Tesseract is available
        try:
            pytesseract.get_tesseract_version()
        except Exception:
            raise ValueError(
                "Tesseract OCR is not installed or not in PATH. "
                "Please install Tesseract OCR:\n"
                "- Windows: https://github.com/UB-Mannheim/tesseract/wiki\n"
                "- macOS: brew install tesseract\n"
                "- Linux: sudo apt-get install tesseract-ocr"
            )
    except Exception:
        pass  # If check fails, try anyway
    
    try:
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Check file format
        valid_extensions = {'.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif', '.webp'}
        if image_path.suffix.lower() not in valid_extensions:
            raise ValueError(f"Unsupported image format: {image_path.suffix}. Supported: {valid_extensions}")
        
        if use_preprocessing and CV2_AVAILABLE:
            # Preprocess image for better OCR
            try:
                processed_img = preprocess_image_for_ocr(image_path)
                # Convert grayscale numpy array to PIL Image
                # preprocess_image_for_ocr returns a 2D grayscale array
                pil_image = Image.fromarray(processed_img)
            except Exception as e:
                # Fallback to original image if preprocessing fails
                print(f"Warning: Image preprocessing failed, using original image: {e}")
                pil_image = Image.open(image_path)
        else:
            # Use original image
            pil_image = Image.open(image_path)
        
        # Perform OCR
        # Configure Tesseract to treat image as a single block of text
        custom_config = r'--oem 3 --psm 6'  # Assume uniform block of text
        text = pytesseract.image_to_string(pil_image, config=custom_config)
        
        return clean_text(text)
    except Exception as e:
        raise ValueError(f"Failed to extract text from image {image_path}: {e}")


def extract_evidence_content(file_path):
    """
    Universal evidence extractor that handles both PDF and image files.
    Automatically detects file type and uses appropriate extraction method.
    
    Args:
        file_path: Path to evidence file (PDF or image)
    
    Returns:
        Dictionary with:
        - extracted_text: Extracted text content
        - file_type: 'pdf' or 'image'
        - file_name: Original file name
        - file_size: File size in bytes
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Evidence file not found: {file_path}")
    
    file_type = None
    extracted_text = ""
    
    # Determine file type and extract accordingly
    ext = file_path.suffix.lower()
    
    if ext == '.pdf':
        file_type = 'pdf'
        extracted_text = extract_text_from_pdf(file_path)
    elif ext in {'.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif', '.webp'}:
        file_type = 'image'
        extracted_text = extract_text_from_image(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}. Supported: PDF, PNG, JPG, JPEG, TIFF, BMP, GIF, WEBP")
    
    file_size = file_path.stat().st_size
    
    return {
        'extracted_text': extracted_text,
        'file_type': file_type,
        'file_name': file_path.name,
        'file_size': file_size,
        'file_path': str(file_path)
    }


if __name__ == "__main__":
    # Example usage
    import sys
    if len(sys.argv) > 1:
        test_file = Path(sys.argv[1])
        result = extract_evidence_content(test_file)
        print(f"File: {result['file_name']}")
        print(f"Type: {result['file_type']}")
        print(f"Size: {result['file_size']} bytes")
        print(f"\nExtracted Text (first 500 chars):\n{result['extracted_text'][:500]}...")

