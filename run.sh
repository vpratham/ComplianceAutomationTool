#!/bin/bash
# SmartCompliance Run Script

cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3."
    exit 1
fi

# Check if required data files exist
if [ ! -f "data/processed/scf_sentences.parquet" ]; then
    echo "⚠️  SCF data not found. Running SCF parser..."
    python3 backend/scf_parser.py
fi

if [ ! -f "data/processed/embeddings/scf_embeddings.npy" ]; then
    echo "⚠️  SCF embeddings not found. Generating embeddings..."
    python3 backend/embedding_model.py
fi

# Run the application
echo "🚀 Starting SmartCompliance..."
python3 -m gui.main

