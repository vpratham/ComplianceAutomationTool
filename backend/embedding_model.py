# backend/embedding_model.py
from sentence_transformers import SentenceTransformer
import numpy as np
import pandas as pd
from pathlib import Path
import os
import sys


def generate_embeddings(input_path, output_path, model_name="all-mpnet-base-v2", text_column="text"):
    """
    Generate and save embeddings for a given parquet file column.

    Args:
        input_path (str | Path): Path to the input parquet file.
        output_path (str | Path): Path to save the .npy embeddings file.
        model_name (str): HuggingFace model name for sentence embeddings.
        text_column (str): Column name containing the text to embed.

    Returns:
        np.ndarray: Generated or loaded embeddings array.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise FileNotFoundError(f"❌ Input file not found: {input_path}")

    print(f"\n📂 Reading data from: {input_path}")
    df = pd.read_parquet(input_path)

    if text_column not in df.columns:
        raise KeyError(f"❌ Column '{text_column}' not found in {input_path}. Available columns: {df.columns.tolist()}")

    texts = df[text_column].astype(str).tolist()
    num_texts = len(texts)
    print(f"📄 Total records: {num_texts}")

    # --- 1️⃣ Check for existing embeddings
    if output_path.exists():
        existing = np.load(output_path)
        if existing.shape[0] == num_texts:
            print(f"✅ Embeddings already exist and match the data count → {output_path}")
            return existing
        else:
            print(f"⚠️ Mismatch: Existing embeddings = {existing.shape[0]} vs current records = {num_texts}")
            print(f"🔁 Regenerating embeddings for consistency...")

    # --- 2️⃣ Load model and generate embeddings
    print(f"🧠 Loading SentenceTransformer model: {model_name}")
    model = SentenceTransformer(model_name)

    print(f"🚀 Generating embeddings (batch_size=64)...")
    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        batch_size=64,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    # --- 3️⃣ Save embeddings
    np.save(output_path, embeddings)
    print(f"✅ Saved embeddings → {output_path}")
    print(f"📊 Embedding shape: {embeddings.shape}")

    return embeddings


if __name__ == "__main__":
    """
    Example standalone execution:
    Regenerates embeddings for SCF and policy sentence datasets.
    """
    base = Path(__file__).resolve().parent.parent
    model_dir = base / "data" / "processed" / "embeddings"
    model_dir.mkdir(parents=True, exist_ok=True)

    scf_path = base / "data" / "processed" / "scf_sentences.parquet"
    policy_path = base / "data" / "company_policies" / "processed" / "example_policy_sentences.parquet"

    scf_output = model_dir / "scf_embeddings.npy"
    policy_output = model_dir / "policy_embeddings.npy"

    print("\n🧾 Generating SCF Embeddings...")
    generate_embeddings(scf_path, scf_output, text_column="text")

    print("\n🏢 Generating Policy Embeddings...")
    generate_embeddings(policy_path, policy_output, text_column="clause_text")

    print("\n✅ All embeddings generated successfully.")
