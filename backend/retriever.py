

# backend/retriever.py
import numpy as np
import pandas as pd
import faiss
from pathlib import Path
from typing import Optional


def build_faiss_index(embeddings: np.ndarray, dim: int):
    """Build a FAISS Index for inner-product (cosine after normalization)."""
    index = faiss.IndexFlatIP(dim)
    faiss.normalize_L2(embeddings)
    index.add(embeddings)
    return index


def retrieve_top_matches(
    scf_emb_path,
    policy_emb_path,
    scf_data_path,
    policy_data_path,
    output_path,
    top_k=50,
    similarity_threshold: Optional[float] = 0.5
):
    """
    Retrieve SCF matches per policy clause using FAISS.

    - For each policy clause embedding, this retrieves up to `top_k` candidates
      from the SCF corpus and then keeps only those with similarity_score >= similarity_threshold.
    - Saves:
        - retrieval_results.parquet : row per (clause, matched_scf) (same schema as before)
        - policy_clauses.parquet   : unique policy clauses (one row per clause) — useful to align with embeddings
    """
    scf_emb_path = Path(scf_emb_path)
    policy_emb_path = Path(policy_emb_path)
    scf_data_path = Path(scf_data_path)
    policy_data_path = Path(policy_data_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load embeddings and data
    scf_embeddings = np.load(scf_emb_path)
    policy_embeddings = np.load(policy_emb_path)
    scf_df = pd.read_parquet(scf_data_path)
    policy_df = pd.read_parquet(policy_data_path)

    if scf_embeddings.shape[0] != len(scf_df):
        print(
            f"⚠️ Warning: SCF embeddings rows ({scf_embeddings.shape[0]}) "
            f"!= scf_df rows ({len(scf_df)}). Ensure embeddings align to scf_sentences.parquet."
        )

    dim = scf_embeddings.shape[1]
    index = build_faiss_index(scf_embeddings, dim)

    print(f"🔍 Querying {len(policy_embeddings)} policy clauses against {len(scf_embeddings)} SCF sentences (top_k={top_k})...")
    # ensure policy embeddings normalized for inner-product cosine similarity
    faiss.normalize_L2(policy_embeddings)
    scores, indices = index.search(policy_embeddings, top_k)

    results = []
    # iterate over each clause embedding (i corresponds to the row order of policy_embeddings)
    for i, (idx_list, score_list) in enumerate(zip(indices, scores)):
        # read clause metadata from policy_df by matching embedding order:
        # policy_data_path is expected to be sentence-level rows in the same order as policy_embeddings.npy
        try:
            clause_row = policy_df.iloc[i]
            policy_id = clause_row.get("policy_id", f"policy_{i}")
            clause_index = clause_row.get("clause_index", i)
            clause_text = clause_row.get("clause_text", clause_row.get("text", ""))
        except IndexError:
            # fallback: if policy_df shorter than embeddings, still proceed with indices
            policy_id = f"policy_{i}"
            clause_index = i
            clause_text = ""

        for j, idx in enumerate(idx_list):
            if idx < 0 or idx >= len(scf_df):
                continue
            score = float(score_list[j])
            # filter by threshold if provided
            if similarity_threshold is not None and score < similarity_threshold:
                continue
            scf_row = scf_df.iloc[idx]
            matched_text = scf_row.get("text", scf_row.get("control_description", ""))
            results.append({
                "policy_id": policy_id,
                "clause_index": clause_index,
                "clause_text": clause_text,
                "matched_scf_id": scf_row.get("scf_id"),
                "matched_domain": scf_row.get("domain", "") if "domain" in scf_row else "",
                "matched_text": matched_text,
                "similarity_score": score
            })

    results_df = pd.DataFrame(results)
    results_df.to_parquet(output_path, index=False)
    print(f"✅ Retrieval complete → {output_path}")

    # Also write unique policy clauses (one row per clause) to make alignment explicit
    # Prefer to extract unique clauses from the original policy_data_path (policy_df)
    try:
        # Determine clause text column
        if "clause_text" in policy_df.columns:
            clause_col = "clause_text"
        elif "text" in policy_df.columns:
            clause_col = "text"
            policy_df = policy_df.rename(columns={"text": "clause_text"})
        else:
            # try any column with 'text' substring
            possible = [c for c in policy_df.columns if "text" in c.lower()]
            clause_col = possible[0] if possible else policy_df.columns[0]

        # We assume policy_embeddings were generated in the same order as policy_df rows.
        policy_clauses = policy_df[[c for c in ("policy_id", "clause_index", clause_col) if c in policy_df.columns]].copy()
        policy_clauses = policy_clauses.rename(columns={clause_col: "clause_text"})
        policy_clauses.to_parquet(output_path.parent / "policy_clauses.parquet", index=False)
        print(f"✅ Wrote unique policy clauses → {output_path.parent / 'policy_clauses.parquet'}")
    except Exception as e:
        print("⚠️ Failed to write policy_clauses.parquet:", e)

    return results_df


if __name__ == "__main__":
    # Default paths based on your repo structure
    base = Path(__file__).resolve().parent.parent
    data_dir = base / "data" / "processed"
    emb_dir = data_dir / "embeddings"

    scf_emb = emb_dir / "scf_embeddings.npy"
    policy_emb = emb_dir / "policy_embeddings.npy"
    scf_data = data_dir / "scf_sentences.parquet"
    policy_data = base / "data" / "company_policies" / "processed" / "example_policy_sentences.parquet"
    output = data_dir / "retrieval_results.parquet"

    # Example usage: top_k=50 and threshold 0.5 (keeps all matches >= 0.5)
    retrieve_top_matches(scf_emb, policy_emb, scf_data, policy_data, output, top_k=50, similarity_threshold=0.5)
