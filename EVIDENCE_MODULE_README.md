# Evidence Validation Module

## Overview
The Evidence Validation module allows auditors to upload evidence artifacts (PDFs, images, screenshots) and automatically validate them against SCF Evidence Request List (ERL) requirements. The system uses OCR (Optical Character Recognition) for images and semantic similarity matching to determine if uploaded evidence satisfies the requirements for each SCF control.

## Features

### 1. Evidence Upload (`gui/evidence_upload_page.py`)
- Upload evidence files (PDF, PNG, JPG, JPEG, TIFF, BMP, GIF, WEBP)
- Select SCF control ID from dropdown
- Automatic text extraction from PDFs and images (OCR)
- Real-time validation against ERL requirements
- Validation results with confidence scores and explanations

### 2. Evidence Registry View (`gui/evidence_view_page.py`)
- View all uploaded evidence artifacts
- Filter by SCF ID or validation status (Valid/Invalid)
- Summary statistics dashboard
- Detailed evidence information with extracted text preview
- Search and filter capabilities

### 3. Backend Validation (`backend/evidence_validator.py`)
- Semantic similarity matching between evidence content and ERL requirements
- Confidence scoring (threshold: 0.6 by default)
- Explains why evidence is valid or invalid
- Links evidence to specific ERL artifacts

### 4. Evidence Management (`backend/evidence_manager.py`)
- Stores evidence artifacts in `data/evidence_artifacts/`
- Maintains evidence registry in Parquet format
- Tracks validation history
- Provides summary statistics

## Installation Requirements

### Python Dependencies
The module requires additional dependencies for OCR functionality:
```bash
pip install pytesseract>=0.3.10
pip install opencv-python>=4.8.0
```

### Tesseract OCR Installation
**Important:** Tesseract OCR must be installed on your system for image text extraction to work.

#### Windows
1. Download Tesseract installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install the executable
3. Add Tesseract to your system PATH, or set `pytesseract.pytesseract.tesseract_cmd` in your code

#### macOS
```bash
brew install tesseract
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

#### Linux (Fedora)
```bash
sudo dnf install tesseract
```

### Configuration (Optional)
If Tesseract is not in your system PATH, you can configure the path in `utils/evidence_extractor.py`:
```python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Windows example
```

## Usage

### 1. Upload and Validate Evidence

1. Navigate to **"Evidence Upload"** from the dashboard sidebar
2. Select an SCF Control ID from the dropdown (e.g., "CC1.1 - Access Control")
3. Click **"Select Evidence File"** and choose a PDF or image file
4. Click **"Validate Evidence"**
5. View validation results:
   - ✅ **VALID**: Evidence satisfies ERL requirements (confidence ≥ 0.6)
   - ❌ **INVALID**: Evidence does not meet requirements or confidence is too low
   - Confidence score, matched ERL artifact, and explanation

### 2. View Evidence Registry

1. Navigate to **"Evidence View"** from the dashboard sidebar
2. View summary statistics:
   - Total evidence count
   - Valid/Invalid counts
   - SCF controls covered
   - Average confidence score
3. Filter evidence by:
   - SCF ID (search box)
   - Validation status (Valid/Invalid dropdown)
4. Double-click any row to view detailed information

### 3. Understanding Validation Results

- **Confidence Score**: Semantic similarity between evidence content and ERL requirement (0.0 - 1.0)
- **Valid Threshold**: Evidence with confidence ≥ 0.6 is considered valid
- **Matched ERL**: The Evidence Request List artifact that best matches the uploaded evidence
- **Explanation**: Detailed explanation of why evidence was validated or rejected

## File Structure

```
SmartCompliance/
├── backend/
│   ├── evidence_validator.py      # Core validation logic
│   └── evidence_manager.py         # Evidence storage and retrieval
├── utils/
│   └── evidence_extractor.py       # PDF/image text extraction + OCR
├── gui/
│   ├── evidence_upload_page.py     # Upload and validate UI
│   └── evidence_view_page.py       # Evidence registry UI
└── data/
    ├── evidence_artifacts/         # Stored evidence files
    └── processed/
        ├── evidence_registry.parquet  # Evidence metadata registry
        └── embeddings/
            └── erl_embeddings.npy     # ERL requirement embeddings
```

## Data Storage

### Evidence Registry Schema
The evidence registry (`evidence_registry.parquet`) contains:
- `timestamp`: Upload timestamp
- `scf_id`: SCF control ID
- `file_name`: Original file name
- `file_name_stored`: Stored file name (with timestamp)
- `file_path`: Original file path
- `stored_file_path`: Path in evidence_artifacts/ directory
- `file_type`: pdf or image
- `file_size`: File size in bytes
- `is_valid`: Boolean validation result
- `confidence_score`: Similarity score (0.0-1.0)
- `matched_erl_id`: Best matching ERL ID
- `matched_artifact_name`: Matched artifact name
- `matched_artifact_desc`: Matched artifact description
- `matched_area_focus`: Area of focus
- `validation_explanation`: Detailed explanation
- `extracted_text_preview`: First 500 chars of extracted text
- `similarity_threshold`: Threshold used for validation
- `success`: Whether validation succeeded
- `error`: Error message if validation failed

## Technical Details

### Text Extraction
- **PDFs**: Uses PyMuPDF (fitz) to extract text
- **Images**: Uses Tesseract OCR with preprocessing:
  - Grayscale conversion
  - Denoising
  - Thresholding (OTSU)
  - Morphological operations

### Semantic Matching
- Uses Sentence Transformers model: `all-mpnet-base-v2`
- Creates embeddings for:
  - Evidence content (extracted text)
  - ERL requirements (artifact_name + artifact_desc)
- Uses FAISS for fast similarity search
- Cosine similarity scoring

### Validation Logic
1. Extract text from evidence file (PDF or image via OCR)
2. Load ERL requirements for selected SCF control
3. Generate embeddings for evidence and ERL requirements
4. Find best matching ERL requirement using semantic similarity
5. Validate if similarity score ≥ threshold (default: 0.6)
6. Generate explanation of validation result

## Troubleshooting

### OCR Issues
- **Error: "Tesseract OCR is not installed"**
  - Install Tesseract OCR (see Installation Requirements above)
  - Ensure Tesseract is in your system PATH
  - For Windows, you may need to set `pytesseract.pytesseract.tesseract_cmd`

### Image Quality Issues
- Low-quality images may have poor OCR results
- The system automatically preprocesses images to improve OCR accuracy
- For best results, use:
  - High-resolution images (≥300 DPI)
  - Clear, well-lit screenshots
  - Images with good contrast

### Validation Issues
- **Low confidence scores**: Evidence content may not align well with ERL requirements
  - Review the matched ERL artifact description
  - Ensure evidence file contains relevant content
  - Consider manual review for borderline cases

### Import Errors
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check that required data files exist:
  - `data/processed/scf_controls.parquet`
  - `data/processed/scf_evidence_list.parquet`
  - Run SCF parser if missing: `python backend/scf_parser.py`

## Future Enhancements
- Batch upload of multiple evidence files
- Evidence linking to policy clauses
- Export evidence validation reports (PDF)
- Evidence approval/rejection workflow
- Integration with compliance report generation

