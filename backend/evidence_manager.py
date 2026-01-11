# backend/evidence_manager.py
"""
Evidence management module for storing and retrieving evidence validation results.
Manages evidence artifacts, their validation status, and linking to SCF controls.
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional
import shutil
from datetime import datetime


def get_evidence_storage_dir(base_dir: Path) -> Path:
    """Get the directory for storing evidence artifacts."""
    evidence_dir = base_dir / "data" / "evidence_artifacts"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    return evidence_dir


def get_evidence_registry_path(base_dir: Path) -> Path:
    """Get the path to the evidence registry (Parquet file)."""
    return base_dir / "data" / "processed" / "evidence_registry.parquet"


def save_evidence_artifact(source_path: Path, base_dir: Path) -> Path:
    """
    Copy evidence artifact to storage directory and return new path.
    
    Args:
        source_path: Original path to evidence file
        base_dir: Base directory of project
    
    Returns:
        Path to saved evidence artifact
    """
    evidence_dir = get_evidence_storage_dir(base_dir)
    file_name = source_path.name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create unique filename with timestamp
    stem = source_path.stem
    suffix = source_path.suffix
    new_name = f"{timestamp}_{stem}{suffix}"
    dest_path = evidence_dir / new_name
    
    # Copy file
    shutil.copy2(source_path, dest_path)
    
    return dest_path


def register_evidence_validation(
    validation_result: Dict,
    base_dir: Path,
    copy_file: bool = True
) -> Dict:
    """
    Register evidence validation result in the registry.
    
    Args:
        validation_result: Result dictionary from process_evidence_artifact()
        base_dir: Base directory of project
        copy_file: Whether to copy evidence file to storage (default: True)
    
    Returns:
        Updated validation result with registry information
    """
    registry_path = get_evidence_registry_path(base_dir)
    
    # Save evidence file to storage if copy_file is True
    if copy_file and validation_result.get('success'):
        source_path = Path(validation_result['file_path'])
        if source_path.exists():
            saved_path = save_evidence_artifact(source_path, base_dir)
            validation_result['stored_file_path'] = str(saved_path)
            validation_result['file_name_stored'] = saved_path.name
        else:
            validation_result['stored_file_path'] = validation_result.get('file_path')
            validation_result['file_name_stored'] = validation_result.get('file_name')
    else:
        validation_result['stored_file_path'] = validation_result.get('file_path')
        validation_result['file_name_stored'] = validation_result.get('file_name')
    
    # Prepare record for registry
    record = {
        'timestamp': datetime.now().isoformat(),
        'scf_id': validation_result.get('scf_id', ''),
        'file_name': validation_result.get('file_name', ''),
        'file_name_stored': validation_result.get('file_name_stored', ''),
        'file_path': validation_result.get('file_path', ''),
        'stored_file_path': validation_result.get('stored_file_path', ''),
        'file_type': validation_result.get('file_type', ''),
        'file_size': validation_result.get('file_size', 0),
        'is_valid': validation_result.get('is_valid', False),
        'confidence_score': validation_result.get('confidence_score', 0.0),
        'matched_erl_id': validation_result.get('matched_erl_id', ''),
        'matched_artifact_name': validation_result.get('matched_artifact_name', ''),
        'matched_artifact_desc': validation_result.get('matched_artifact_desc', ''),
        'matched_area_focus': validation_result.get('matched_area_focus', ''),
        'validation_explanation': validation_result.get('validation_explanation', ''),
        'extracted_text_preview': validation_result.get('extracted_text_preview', ''),
        'similarity_threshold': validation_result.get('similarity_threshold', 0.6),
        'success': validation_result.get('success', False),
        'error': validation_result.get('error', '')
    }
    
    # Load existing registry or create new
    if registry_path.exists():
        registry_df = pd.read_parquet(registry_path)
    else:
        registry_df = pd.DataFrame()
    
    # Add new record
    new_record_df = pd.DataFrame([record])
    registry_df = pd.concat([registry_df, new_record_df], ignore_index=True)
    
    # Save updated registry
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_df.to_parquet(registry_path, index=False)
    
    # Add registry ID to result
    validation_result['registry_id'] = len(registry_df) - 1
    validation_result['timestamp'] = record['timestamp']
    
    return validation_result


def load_evidence_registry(base_dir: Path) -> pd.DataFrame:
    """Load the evidence registry."""
    registry_path = get_evidence_registry_path(base_dir)
    if registry_path.exists():
        return pd.read_parquet(registry_path)
    else:
        return pd.DataFrame()


def get_evidence_by_scf_id(scf_id: str, base_dir: Path) -> pd.DataFrame:
    """Get all evidence artifacts for a specific SCF control ID."""
    registry_df = load_evidence_registry(base_dir)
    if len(registry_df) == 0:
        return pd.DataFrame()
    return registry_df[registry_df['scf_id'] == scf_id].copy()


def get_evidence_summary(base_dir: Path) -> Dict:
    """Get summary statistics of evidence registry."""
    registry_df = load_evidence_registry(base_dir)
    
    if len(registry_df) == 0:
        return {
            'total_evidence': 0,
            'valid_evidence': 0,
            'invalid_evidence': 0,
            'unique_scf_controls': 0,
            'average_confidence': 0.0,
            'evidence_by_scf': {}
        }
    
    total = len(registry_df)
    valid = registry_df['is_valid'].sum()
    invalid = total - valid
    unique_scf = registry_df['scf_id'].nunique()
    avg_confidence = registry_df['confidence_score'].mean()
    
    # Count evidence by SCF ID
    evidence_by_scf = registry_df.groupby('scf_id').size().to_dict()
    
    return {
        'total_evidence': total,
        'valid_evidence': valid,
        'invalid_evidence': invalid,
        'unique_scf_controls': unique_scf,
        'average_confidence': float(avg_confidence),
        'evidence_by_scf': evidence_by_scf
    }


def delete_evidence_record(registry_id: int, base_dir: Path, delete_file: bool = False) -> bool:
    """
    Delete an evidence record from registry.
    
    Args:
        registry_id: Index of record to delete
        base_dir: Base directory of project
        delete_file: Whether to also delete the stored file
    
    Returns:
        True if successful, False otherwise
    """
    registry_path = get_evidence_registry_path(base_dir)
    if not registry_path.exists():
        return False
    
    registry_df = pd.read_parquet(registry_path)
    
    if registry_id < 0 or registry_id >= len(registry_df):
        return False
    
    # Optionally delete file
    if delete_file:
        stored_path = registry_df.iloc[registry_id].get('stored_file_path')
        if stored_path and Path(stored_path).exists():
            try:
                Path(stored_path).unlink()
            except Exception:
                pass  # Continue even if file deletion fails
    
    # Remove record
    registry_df = registry_df.drop(registry_df.index[registry_id]).reset_index(drop=True)
    registry_df.to_parquet(registry_path, index=False)
    
    return True


if __name__ == "__main__":
    # Example usage
    base = Path(__file__).resolve().parent.parent
    summary = get_evidence_summary(base)
    print("Evidence Registry Summary:")
    print(f"  Total Evidence: {summary['total_evidence']}")
    print(f"  Valid: {summary['valid_evidence']}")
    print(f"  Invalid: {summary['invalid_evidence']}")
    print(f"  Unique SCF Controls: {summary['unique_scf_controls']}")
    print(f"  Average Confidence: {summary['average_confidence']:.3f}")

