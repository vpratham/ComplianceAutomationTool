# backend/rag_pipeline.py

import numpy as np
import pandas as pd
import faiss
from difflib import SequenceMatcher
from pathlib import Path
from sentence_transformers import SentenceTransformer


# ---------------------------------------------------------
# Confidence Scoring
# ---------------------------------------------------------
def get_confidence_comment(score: float) -> str:
    """Assign confidence level based on similarity score."""
    if score >= 0.65:
        return "High Confidence"
    elif score >= 0.55:
        return "Medium Confidence"
    else:
        return "Low Confidence"


# ---------------------------------------------------------
# Merge Logic (with duplicate filtering and threshold)
# ---------------------------------------------------------
def merge_candidates(candidates, scf_embeddings_map, threshold=0.5):
    """Merge semantically similar SCF candidates and keep all above threshold."""
    merged = []
    seen_ids = set()

    candidates = sorted(
        [c for c in candidates if c["similarity_score"] >= threshold],
        key=lambda x: x["similarity_score"],
        reverse=True,
    )

    for cand in candidates:
        scf_id = cand["matched_scf_id"]
        if scf_id in seen_ids:
            continue
        seen_ids.add(scf_id)

        duplicate_found = False
        for m in merged:
            ratio = SequenceMatcher(None, m["matched_text"], cand["matched_text"]).ratio()
            if ratio >= 0.6:
                duplicate_found = True
                break

        if not duplicate_found:
            merged.append(cand)

    return merged


# ---------------------------------------------------------
# FAISS Retrieval
# ---------------------------------------------------------
def retrieve_top_scf_matches(clause_embedding, index, scf_records):
    """Retrieve diverse top SCF candidates from FAISS index."""
    top_k = 50
    faiss.normalize_L2(clause_embedding)
    D, I = index.search(clause_embedding, top_k)

    candidates = []
    seen_ids = set()

    for dist, idx in zip(D[0], I[0]):
        if idx < 0 or idx >= len(scf_records):
            continue
        scf_item = scf_records[idx]
        scf_id = scf_item.get("scf_id")
        if scf_id not in seen_ids:
            seen_ids.add(scf_id)
            candidates.append(
                {
                    "matched_scf_id": scf_id,
                    "matched_domain": scf_item.get("domain", ""),
                    "matched_text": scf_item.get("text", ""),
                    "similarity_score": float(dist),
                }
            )
    return candidates


# ---------------------------------------------------------
# Generate Explanations (no LLM)
# ---------------------------------------------------------
def generate_mapping_explanations(policy_df, index, scf_records, scf_embeddings_map, threshold=0.5):
    """Generate mapping explanations for each clause using semantic similarity."""
    results = []
    total = len(policy_df)

    for idx, row in enumerate(policy_df.itertuples(index=False), start=1):
        clause_text = row.clause_text
        clause_embedding = row.embedding.reshape(1, -1)
        faiss.normalize_L2(clause_embedding)

        # Retrieve candidates
        candidates = retrieve_top_scf_matches(clause_embedding, index, scf_records)

        # ✅ Live progress log (for GUI)
        print(f"🔹 Mapping clause {idx}/{total} → Found {len(candidates)} candidate matches", flush=True)

        # Merge and filter matches above threshold
        merged_matches = merge_candidates(candidates, scf_embeddings_map, threshold=threshold)

        # 🛟 Fallback — if no matches above threshold, take best available
        if not merged_matches and len(candidates) > 0:
            fallback = candidates[0].copy()
            fallback["similarity_score"] = fallback.get("similarity_score", 0.0)
            fallback["confidence_comment"] = f"Very Low (Fallback, Sim={fallback['similarity_score']:.2f})"
            fallback["matched_scf_id"] = fallback.get("matched_scf_id", "Unknown")
            fallback["matched_domain"] = fallback.get("matched_domain", "Unknown")
            fallback["matched_text"] = fallback.get("matched_text", "(No match text found)")
            fallback["explanation"] = (
                f"No strong semantic match found, but this clause loosely relates to "
                f"'{fallback['matched_text']}' with similarity {fallback['similarity_score']:.2f}."
            )
            merged_matches = [fallback]

        # Build explanations
        explanations = []
        for match in merged_matches:
            confidence = get_confidence_comment(match.get("similarity_score", 0.0))
            explanation = (
                f"This clause likely aligns with SCF control text that says: "
                f"'{match['matched_text']}'. "
                f"The semantic similarity score is {match.get('similarity_score', 0.0):.2f}, "
                f"suggesting a {confidence.lower()} match."
            )

            explanations.append(
                {
                    "matched_scf_id": match.get("matched_scf_id", "Unknown"),
                    "matched_domain": match.get("matched_domain", "Unknown"),
                    "matched_text": match.get("matched_text", "(No text)"),
                    "confidence_comment": confidence,
                    "explanation": explanation,
                }
            )

        results.append(
            {
                "policy_id": getattr(row, "policy_id", "example_policy"),
                "clause_index": getattr(row, "clause_index", idx),
                "clause_text": clause_text,
                "mapping_explanations": explanations,
            }
        )

    print("✅ Mapping complete!\n", flush=True)
    return results


# ---------------------------------------------------------
# Embedding Regeneration Logic
# ---------------------------------------------------------
def regenerate_policy_embeddings(policy_df, model_name="sentence-transformers/all-mpnet-base-v2"):
    """Regenerate embeddings for the given policy dataframe."""
    print(f"🧠 Regenerating policy embeddings using {model_name} ...")
    model = SentenceTransformer(model_name)
    embeddings = model.encode(policy_df["clause_text"].tolist(), show_progress_bar=True)
    np.save(Path("data/processed/embeddings/policy_embeddings.npy"), embeddings)
    print(f"✅ Saved regenerated embeddings: {embeddings.shape}")
    return embeddings


# ---------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------
def run_rag_explanations(prefer_local: bool = True, threshold: float = 0.5):
    """Entry point for RAG explanation generation."""
    print(f"run_rag_explanations called (prefer_local={prefer_local}, threshold={threshold})")

    processed_dir = Path("data/processed/embeddings")
    base_dir = Path(__file__).resolve().parent.parent
    print("📂 Loading embeddings and data...")

    # --- Load embeddings ---
    policy_embeddings = np.load(processed_dir / "policy_embeddings.npy")
    scf_embeddings = np.load(processed_dir / "scf_embeddings.npy")
    print(f"📊 policy_embeddings shape: {policy_embeddings.shape}")
    print(f"📊 scf_embeddings shape: {scf_embeddings.shape}")

    # --- Load SCF records ---
    scf_records_df = pd.read_parquet(base_dir / "data/processed/scf_sentences.parquet")
    scf_records = scf_records_df.to_dict(orient="records")

    # --- Build FAISS index ---
    dim = scf_embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    faiss.normalize_L2(scf_embeddings)
    index.add(scf_embeddings)
    print(f"✅ FAISS index built with {len(scf_records)} SCF records")

    # --- Load latest uploaded policy ---
    latest_path_file = base_dir / "data/latest_policy_path.txt"
    if latest_path_file.exists():
        with open(latest_path_file, "r") as f:
            latest_policy_path = Path(f.read().strip())
        if latest_policy_path.exists():
            print(f"📄 Using latest uploaded policy file: {latest_policy_path.name}")
            policy_df = pd.read_parquet(latest_policy_path)
        else:
            print("⚠️ Latest policy path missing. Falling back to retrieval_results.parquet.")
            policy_df = pd.read_parquet(base_dir / "data/processed/retrieval_results.parquet")
    else:
        print("⚠️ No latest_policy_path.txt found. Using retrieval_results.parquet.")
        policy_df = pd.read_parquet(base_dir / "data/processed/retrieval_results.parquet")

    print(f"📄 Loaded {len(policy_df)} clauses from selected policy file.")

    if "clause_text" not in policy_df.columns:
        raise ValueError("❌ No 'clause_text' column found in policy file.")

    # --- Deduplicate ---
    print(f"🧮 Total clauses before deduplication: {len(policy_df)}")
    policy_df = policy_df.drop_duplicates(subset=["clause_text"], keep="first").reset_index(drop=True)
    print(f"✅ Clauses after deduplication: {len(policy_df)}")

    # --- Ensure embedding alignment ---
    emb_count, row_count = len(policy_embeddings), len(policy_df)
    if emb_count != row_count:
        print(f"⚠️ Mismatch detected: {emb_count} embeddings vs {row_count} clauses")
        print("🔁 Regenerating policy embeddings to ensure full alignment...")
        policy_embeddings = regenerate_policy_embeddings(policy_df)
    else:
        print("✅ Embeddings and clauses are already aligned.")

    print(f"✅ Alignment complete: {len(policy_embeddings)} embeddings ↔ {len(policy_df)} rows")

    # --- Attach embeddings ---
    policy_df["embedding"] = list(policy_embeddings)
    policy_df["clause_index"] = range(len(policy_df))

    # --- Generate mappings ---
    print("⚙️ Generating explainable mappings...")
    scf_embeddings_map = {rec["scf_id"]: scf_embeddings[i] for i, rec in enumerate(scf_records)}
    results = generate_mapping_explanations(policy_df, index, scf_records, scf_embeddings_map, threshold=threshold)

    # --- Save output ---
    output_path = base_dir / "data/processed/explainable_mappings.parquet"
    pd.DataFrame(results).to_parquet(output_path, index=False)
    print(f"✅ Saved explainable mappings → {output_path}")

    # --- Preview ---
    print("\n🔍 Example Mapping Preview:")
    for i, r in enumerate(results[:2]):
        print(f"\nClause {r['clause_index']}: {r['clause_text']}")
        for m in r["mapping_explanations"]:
            print(f" - {m['matched_scf_id']}: {m['confidence_comment']} ({m['matched_domain']}) → {m['matched_text'][:100]}...")

    return pd.DataFrame(results)


# ---------------------------------------------------------
# CLI Run
# ---------------------------------------------------------
if __name__ == "__main__":
    df = run_rag_explanations(prefer_local=True, threshold=0.5)
    print("\n✅ RAG explanations generation complete.")
