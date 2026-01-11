#!/usr/bin/env python3
"""
SmartCompliance Run Script
A simple Python script to launch the SmartCompliance application.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

def check_setup():
    """Check if required files exist and provide helpful messages."""
    print("🔍 Checking SmartCompliance setup...\n")
    
    issues = []
    warnings = []
    
    # Check SCF data
    scf_data = project_root / "data" / "processed" / "scf_sentences.parquet"
    if not scf_data.exists():
        issues.append("SCF data missing. Run: python3 backend/scf_parser.py")
    else:
        print("✅ SCF data found")
    
    # Check SCF embeddings
    scf_emb = project_root / "data" / "processed" / "embeddings" / "scf_embeddings.npy"
    if not scf_emb.exists():
        issues.append("SCF embeddings missing. Run: python3 backend/embedding_model.py")
    else:
        print("✅ SCF embeddings found")
    
    # Check policy embeddings (optional)
    policy_emb = project_root / "data" / "processed" / "embeddings" / "policy_embeddings.npy"
    if not policy_emb.exists():
        warnings.append("Policy embeddings not found. You can upload a policy file to generate them.")
    else:
        print("✅ Policy embeddings found")
    
    print()  # Empty line
    
    if issues:
        print("⚠️  Setup issues found:")
        for issue in issues:
            print(f"   • {issue}")
        print("\nWould you like to continue anyway? (y/n): ", end="")
        try:
            response = input().strip().lower()
            if response != 'y':
                sys.exit(1)
        except KeyboardInterrupt:
            print("\n\nCancelled.")
            sys.exit(1)
    elif warnings:
        print("💡 Note: You can upload a policy file from the Upload page to start mapping.")
    else:
        print("✅ All required files found!\n")

def main():
    """Main entry point."""
    check_setup()
    
    print("🚀 Starting SmartCompliance GUI...")
    print("   (Press Ctrl+C to exit)\n")
    
    try:
        # Import and run the main application
        from gui.main import main as gui_main
        gui_main()
    except KeyboardInterrupt:
        print("\n\n👋 SmartCompliance closed.")
        sys.exit(0)
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("\n💡 Make sure you're in the virtual environment:")
        print("   source venv/bin/activate")
        print("   python3 -m pip install --break-system-packages -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error starting application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

