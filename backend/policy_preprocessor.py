# backend/policy_preprocessor.py
import os
import re
import pandas as pd
from pathlib import Path
from utils.pdf_extractor import extract_text_from_pdf, extract_text_from_docx

# def split_into_clauses(text):
#     """Split text into sentence-like clauses suitable for NLP analysis."""
#     sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
#     # sentences = re.split(r'(?:(?<=[.!?])\s+(?=[A-Z]))|(?:\n+)|(?:•\s*)|(?:-\s*)', text)

#     return [s.strip() for s in sentences if len(s.strip()) > 20]
import re

def split_into_clauses(text):
    """
    Smart clause splitter for both policy-style lists and natural sentences.
    Handles:
      - Paragraph sentences (.!?)
      - Numbered lists (1., 1.1., 2.)
      - Bulleted lists (•, -)
      - Line breaks
    """
    sentences = re.split(
        r'(?:(?<=[.!?])\s+(?=[A-Z]))|'   # normal sentences
        r'(?:(?<=\n)\s*\d+(?:\.\d+)*\s+)|'  # numbered clauses
        r'(?:(?<=\n)\s*[a-zA-Z]\.\s+)|'     # lettered subclauses (a. b.)
        r'(?:\n{2,})|'                      # double line breaks
        r'(?:•\s*)|'                        # bullet
        r'(?:-\s*)',                        # dash bullet
        text
    )

    return [s.strip() for s in sentences if len(s.strip()) > 20]


def preprocess_policy(file_path, output_dir):
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # --- 1️⃣ Extract Text ---
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        text = extract_text_from_pdf(file_path)
    elif ext == ".docx":
        text = extract_text_from_docx(file_path)
    else:
        raise ValueError("Unsupported file type. Use PDF or DOCX.")

    # --- 2️⃣ Split into Clauses ---
    clauses = split_into_clauses(text)

    # --- 3️⃣ Build DataFrame ---
    df = pd.DataFrame({
        "policy_id": [file_path.stem] * len(clauses),
        "source": "company_policy",
        "clause_text": clauses,
        "clause_index": range(1, len(clauses) + 1)
    })

    # --- 4️⃣ Save as Parquet ---
    output_path = Path(output_dir) / f"{file_path.stem}_sentences.parquet"
    df.to_parquet(output_path, index=False)
    print(f"✅ Processed {len(df)} clauses → {output_path}")
    return df


if __name__ == "__main__":
    # Example usage
    base = Path(__file__).resolve().parent.parent
    input_file = base / "data" / "company_policies" / "example_policy.pdf"
    output_dir = base / "data" / "company_policies" / "processed" 

    preprocess_policy(input_file, output_dir)
