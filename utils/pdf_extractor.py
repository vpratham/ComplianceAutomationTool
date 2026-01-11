# utils/pdf_extractor.py
import fitz  # PyMuPDF
import docx
import re

def extract_text_from_pdf(file_path):
    """Extract text content from a PDF using PyMuPDF."""
    text = ""
    with fitz.open(file_path) as doc:
        for page in doc:
            text += page.get_text("text") + "\n"
    return clean_text(text)

def extract_text_from_docx(file_path):
    """Extract text content from a DOCX file using python-docx."""
    doc = docx.Document(file_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return clean_text(text)

def clean_text(text):
    """Normalize extracted text by removing extra spaces, headers, etc."""
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text
