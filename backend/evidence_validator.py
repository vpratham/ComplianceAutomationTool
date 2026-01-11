# backend/evidence_validator.py
"""
Evidence validation module that matches uploaded evidence artifacts to SCF Evidence Request List (ERL) requirements
and validates whether the evidence satisfies the requirements.
"""

import numpy as np
import pandas as pd
import faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer
from typing import Dict, List, Optional, Tuple
from utils.evidence_extractor import extract_evidence_content


def load_erl_requirements(base_dir: Path) -> pd.DataFrame:
    """
    Load Evidence Request List (ERL) requirements.
    Returns dataframe with erl_id, area_focus, artifact_name, artifact_desc, and linked scf_id.
    """
    erl_path = base_dir / "data" / "processed" / "scf_evidence_list.parquet"
    if not erl_path.exists():
        raise FileNotFoundError(f"ERL requirements file not found: {erl_path}")
    
    erl_df = pd.read_parquet(erl_path)
    
    # Also load controls to get SCF IDs linked to ERL
    controls_path = base_dir / "data" / "processed" / "scf_controls.parquet"
    if controls_path.exists():
        controls_df = pd.read_parquet(controls_path)
        # Merge to get scf_id for each erl_id
        erl_df = erl_df.merge(
            controls_df[['scf_id', 'erl_ref']].drop_duplicates(),
            left_on='erl_id',
            right_on='erl_ref',
            how='left'
        )
    
    return erl_df


def create_erl_embeddings(erl_df: pd.DataFrame, model_name: str = "all-mpnet-base-v2") -> Tuple[np.ndarray, pd.DataFrame]:
    """
    Create embeddings for ERL requirements.
    Combines artifact_name and artifact_desc for better matching.
    
    Returns:
        Tuple of (embeddings array, enriched ERL dataframe)
    """
    model = SentenceTransformer(model_name)
    
    # Create combined text for embedding (artifact name + description)
    erl_df = erl_df.copy()
    erl_df['combined_text'] = (
        erl_df['artifact_name'].fillna('').astype(str) + " " +
        erl_df['artifact_desc'].fillna('').astype(str)
    ).str.strip()
    
    # Generate embeddings
    texts = erl_df['combined_text'].tolist()
    embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)
    
    return embeddings, erl_df


def validate_evidence_against_erl(
    evidence_text: str,
    scf_id: str,
    erl_df: pd.DataFrame,
    erl_embeddings: np.ndarray,
    model_name: str = "all-mpnet-base-v2",
    similarity_threshold: float = 0.6
) -> Dict:
    """
    Validate evidence content against ERL requirements for a specific SCF control.
    
    Args:
        evidence_text: Extracted text from evidence artifact
        scf_id: SCF control ID to validate against
        erl_df: DataFrame containing ERL requirements
        erl_embeddings: Pre-computed embeddings for ERL requirements
        model_name: Sentence transformer model name
        similarity_threshold: Minimum similarity score for valid match
    
    Returns:
        Dictionary with validation results:
        - is_valid: Boolean indicating if evidence satisfies requirements
        - confidence_score: Highest similarity score
        - matched_erl_id: Best matching ERL ID
        - matched_artifact_name: Name of matched artifact requirement
        - matched_artifact_desc: Description of matched artifact requirement
        - validation_explanation: Explanation of validation result
        - all_matches: List of all ERL matches above threshold
    """
    if not evidence_text or not evidence_text.strip():
        return {
            'is_valid': False,
            'confidence_score': 0.0,
            'matched_erl_id': None,
            'matched_artifact_name': None,
            'matched_artifact_desc': None,
            'validation_explanation': 'Evidence contains no extractable text.',
            'all_matches': []
        }
    
    # Filter ERL requirements for this SCF control
    relevant_erl = erl_df[erl_df['scf_id'] == scf_id].copy()
    
    if len(relevant_erl) == 0:
        # If no ERL linked to this SCF ID, check all ERLs but note this
        relevant_erl = erl_df.copy()
        use_all_erl = True
    else:
        use_all_erl = False
    
    if len(relevant_erl) == 0:
        return {
            'is_valid': False,
            'confidence_score': 0.0,
            'matched_erl_id': None,
            'matched_artifact_name': None,
            'matched_artifact_desc': None,
            'validation_explanation': f'No ERL requirements found for SCF control {scf_id}.',
            'all_matches': []
        }
    
    # Get embeddings for relevant ERL requirements
    relevant_indices = relevant_erl.index.tolist()
    relevant_embeddings = erl_embeddings[relevant_indices]
    
    # Generate embedding for evidence text
    model = SentenceTransformer(model_name)
    evidence_embedding = model.encode([evidence_text], normalize_embeddings=True)
    
    # Build FAISS index for similarity search
    dim = relevant_embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    faiss.normalize_L2(relevant_embeddings)
    index.add(relevant_embeddings)
    
    # Search for best matches
    faiss.normalize_L2(evidence_embedding)
    scores, indices = index.search(evidence_embedding, min(10, len(relevant_erl)))
    
    # Process matches
    all_matches = []
    best_match = None
    best_score = 0.0
    
    for score, idx_pos in zip(scores[0], indices[0]):
        if idx_pos < 0 or idx_pos >= len(relevant_erl):
            continue
        
        actual_idx = relevant_indices[idx_pos]
        erl_row = relevant_erl.loc[actual_idx]
        
        match_info = {
            'erl_id': erl_row.get('erl_id'),
            'artifact_name': erl_row.get('artifact_name', ''),
            'artifact_desc': erl_row.get('artifact_desc', ''),
            'area_focus': erl_row.get('area_focus', ''),
            'similarity_score': float(score),
            'scf_id': erl_row.get('scf_id', scf_id)
        }
        
        all_matches.append(match_info)
        
        if score > best_score:
            best_score = float(score)
            best_match = match_info
    
    # Determine validity
    is_valid = best_score >= similarity_threshold
    
    # Create explanation
    if best_match:
        if use_all_erl:
            explanation_prefix = f"Note: No direct ERL link found for {scf_id}. "
        else:
            explanation_prefix = ""
        
        if is_valid:
            validation_explanation = (
                f"{explanation_prefix}Evidence successfully matches ERL requirement "
                f"'{best_match['artifact_name']}' with high confidence (score: {best_score:.3f}). "
                f"The evidence content aligns with the requirement: '{best_match['artifact_desc'][:200]}...'"
            )
        else:
            validation_explanation = (
                f"{explanation_prefix}Evidence partially matches ERL requirement "
                f"'{best_match['artifact_name']}' but confidence is below threshold "
                f"(score: {best_score:.3f}, required: {similarity_threshold}). "
                f"Manual review recommended. Best match requirement: '{best_match['artifact_desc'][:200]}...'"
            )
    else:
        validation_explanation = (
            f"No suitable ERL requirement matches found for evidence. "
            f"Evidence may not satisfy requirements for SCF control {scf_id}."
        )
    
    return {
        'is_valid': is_valid,
        'confidence_score': best_score,
        'matched_erl_id': best_match['erl_id'] if best_match else None,
        'matched_artifact_name': best_match['artifact_name'] if best_match else None,
        'matched_artifact_desc': best_match['artifact_desc'] if best_match else None,
        'matched_area_focus': best_match.get('area_focus', '') if best_match else None,
        'validation_explanation': validation_explanation,
        'all_matches': all_matches,
        'similarity_threshold': similarity_threshold
    }


def process_evidence_artifact(
    evidence_file_path: str,
    scf_id: str,
    base_dir: Optional[Path] = None,
    similarity_threshold: float = 0.6
) -> Dict:
    """
    Complete evidence processing pipeline: extract content and validate against ERL.
    
    Args:
        evidence_file_path: Path to evidence file (PDF or image)
        scf_id: SCF control ID this evidence is intended to satisfy
        base_dir: Base directory of project (for loading ERL data)
        similarity_threshold: Minimum similarity score for validation
    
    Returns:
        Dictionary with complete validation results including extracted content
    """
    if base_dir is None:
        base_dir = Path(__file__).resolve().parent.parent
    
    # Step 1: Extract content from evidence file
    try:
        extraction_result = extract_evidence_content(evidence_file_path)
        evidence_text = extraction_result['extracted_text']
        file_type = extraction_result['file_type']
        file_name = extraction_result['file_name']
        file_size = extraction_result['file_size']
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'is_valid': False,
            'file_name': Path(evidence_file_path).name if evidence_file_path else 'Unknown'
        }
    
    # Step 2: Load ERL requirements
    try:
        erl_df = load_erl_requirements(base_dir)
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to load ERL requirements: {e}",
            'is_valid': False,
            'file_name': file_name,
            'extracted_text': evidence_text[:500] if evidence_text else ""
        }
    
    # Step 3: Create or load ERL embeddings
    try:
        erl_emb_path = base_dir / "data" / "processed" / "embeddings" / "erl_embeddings.npy"
        erl_metadata_path = base_dir / "data" / "processed" / "erl_with_embeddings.parquet"
        
        # Check if embeddings exist and are up to date
        if erl_emb_path.exists() and erl_metadata_path.exists():
            erl_embeddings = np.load(erl_emb_path)
            erl_with_emb = pd.read_parquet(erl_metadata_path)
            # Check if dimensions match
            if len(erl_with_emb) == len(erl_df) and len(erl_with_emb) == len(erl_embeddings):
                erl_df = erl_with_emb
            else:
                # Regenerate embeddings if mismatch
                erl_embeddings, erl_df = create_erl_embeddings(erl_df)
                np.save(erl_emb_path, erl_embeddings)
                erl_df.to_parquet(erl_metadata_path, index=False)
        else:
            # Generate embeddings
            erl_embeddings, erl_df = create_erl_embeddings(erl_df)
            erl_emb_path.parent.mkdir(parents=True, exist_ok=True)
            np.save(erl_emb_path, erl_embeddings)
            erl_df.to_parquet(erl_metadata_path, index=False)
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to create ERL embeddings: {e}",
            'is_valid': False,
            'file_name': file_name,
            'extracted_text': evidence_text[:500] if evidence_text else ""
        }
    
    # Step 4: Validate evidence against ERL requirements
    try:
        validation_result = validate_evidence_against_erl(
            evidence_text,
            scf_id,
            erl_df,
            erl_embeddings,
            similarity_threshold=similarity_threshold
        )
    except Exception as e:
        return {
            'success': False,
            'error': f"Validation failed: {e}",
            'is_valid': False,
            'file_name': file_name,
            'extracted_text': evidence_text[:500] if evidence_text else ""
        }
    
    # Combine results
    result = {
        'success': True,
        'file_name': file_name,
        'file_path': evidence_file_path,
        'file_type': file_type,
        'file_size': file_size,
        'scf_id': scf_id,
        'extracted_text': evidence_text,
        'extracted_text_preview': evidence_text[:500] + "..." if len(evidence_text) > 500 else evidence_text,
        **validation_result
    }
    
    return result


if __name__ == "__main__":
    # Example usage
    import sys
    base = Path(__file__).resolve().parent.parent
    
    if len(sys.argv) < 3:
        print("Usage: python evidence_validator.py <evidence_file> <scf_id>")
        print("Example: python evidence_validator.py evidence/screenshot.png CC1.1")
        sys.exit(1)
    
    evidence_file = sys.argv[1]
    scf_id = sys.argv[2]
    
    result = process_evidence_artifact(evidence_file, scf_id, base_dir=base)
    
    print(f"\n{'='*60}")
    print(f"Evidence Validation Results")
    print(f"{'='*60}")
    print(f"File: {result.get('file_name', 'Unknown')}")
    print(f"SCF ID: {result.get('scf_id', 'Unknown')}")
    print(f"Valid: {result.get('is_valid', False)}")
    print(f"Confidence Score: {result.get('confidence_score', 0.0):.3f}")
    print(f"\nMatched Artifact: {result.get('matched_artifact_name', 'None')}")
    print(f"\nExplanation:\n{result.get('validation_explanation', 'No explanation')}")

