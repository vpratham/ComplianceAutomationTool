# backend/scf_parser.py
import pandas as pd
import re
import os
from pathlib import Path

# Helper for text cleanup
def clean_text(txt):
    if pd.isna(txt):
        return ""
    txt = str(txt).replace("\r", " ").replace("\n", " ").strip()
    txt = re.sub(r"\s+", " ", txt)
    return txt

# Split long text into pseudo-sentences for embeddings
def split_sentences(text):
    text = clean_text(text)
    # naive sentence split
    return re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)

def parse_scf_dataset(excel_path, output_dir):
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # --- 1️⃣ Read Key Sheets ---
    print("Loading sheets...")
    xls = pd.ExcelFile(excel_path)

    # Main Controls
    controls = pd.read_excel(xls, sheet_name="SCF 2024.3")
    controls.columns = controls.columns.str.strip()
    controls.rename(columns={
        "SCF Domain": "domain",
        "SCF Control": "control_title",
        "SCF #": "scf_id",
        "Secure Controls Framework (SCF)\nControl Description": "control_description",
        "Evidence Request List (ERL) #": "erl_ref"
    }, inplace=True)
    controls = controls[["scf_id", "domain", "control_title", "control_description", "erl_ref"]]
    controls["control_description"] = controls["control_description"].apply(clean_text)

    # Assessment Objectives
    # Assessment Objectives (robust version)
    aos = pd.read_excel(xls, sheet_name="Assessment Objectives 2024.3")
    aos.columns = aos.columns.str.strip()

    # Find best-matching columns dynamically (handles renamed or spaced variants)
    def find_col(possible_names, columns):
        for name in columns:
            clean = name.lower().replace("\n", " ").replace("  ", " ").strip()
            for target in possible_names:
                if target.lower() in clean:
                    return name
        return None

    col_map = {
        "scf_id": find_col(["SCF #"], aos.columns),
        "ao_id": find_col(["SCF AO #"], aos.columns),
        "ao_text": find_col(["SCF Assessment Objective"], aos.columns),
        "ao_origin": find_col(["Origin"], aos.columns),
    }

    missing = [k for k, v in col_map.items() if v is None]
    if missing:
        raise KeyError(f"Missing expected columns in Assessment Objectives sheet: {missing}")

    aos = aos[[col_map["scf_id"], col_map["ao_id"], col_map["ao_text"], col_map["ao_origin"]]]
    aos.columns = ["scf_id", "ao_id", "ao_text", "ao_origin"]
    aos["ao_text"] = aos["ao_text"].apply(clean_text)


    # Evidence Request List
    erl = pd.read_excel(xls, sheet_name="Evidence Request List 2024.3")
    erl.columns = erl.columns.str.strip()
    erl.rename(columns={
        "ERL #": "erl_id",
        "Area of Focus": "area_focus",
        "Documentation Artifact": "artifact_name",
        "Artifact Description": "artifact_desc"
    }, inplace=True)
    erl = erl[["erl_id", "area_focus", "artifact_name", "artifact_desc"]]
    erl["artifact_desc"] = erl["artifact_desc"].apply(clean_text)

    print(f"Loaded: {len(controls)} controls, {len(aos)} objectives, {len(erl)} evidence rows")

    # --- 2️⃣ Join Data ---
    merged = controls.merge(aos, on="scf_id", how="left")
    merged = merged.merge(erl, left_on="erl_ref", right_on="erl_id", how="left")

    # --- 3️⃣ Generate sentence-level data ---
    sentences = []
    for _, row in merged.iterrows():
        control_sents = split_sentences(row.get("control_description", ""))
        ao_sents = split_sentences(row.get("ao_text", ""))

        for s in control_sents:
            if len(s.strip()) > 20:
                sentences.append({
                    "scf_id": row["scf_id"],
                    "source": "control",
                    "text": s,
                    "domain": row["domain"],
                    "control_title": row["control_title"]
                })
        for s in ao_sents:
            if len(s.strip()) > 20:
                sentences.append({
                    "scf_id": row["scf_id"],
                    "source": "objective",
                    "text": s,
                    "domain": row["domain"],
                    "control_title": row["control_title"]
                })

    sent_df = pd.DataFrame(sentences)
    print(f"Created {len(sent_df)} sentence-level records.")

    # --- 4️⃣ Save Outputs ---
    controls.to_parquet(os.path.join(output_dir, "scf_controls.parquet"), index=False)
    aos.to_parquet(os.path.join(output_dir, "scf_assessment_objectives.parquet"), index=False)
    erl.to_parquet(os.path.join(output_dir, "scf_evidence_list.parquet"), index=False)
    sent_df.to_parquet(os.path.join(output_dir, "scf_sentences.parquet"), index=False)

    print("✅ SCF dataset successfully parsed and saved to", output_dir)


if __name__ == "__main__":
    base = Path(__file__).resolve().parent.parent  # project root
    EXCEL_PATH = base / "data" / "secure-controls-framework-scf-2024-3.xlsx"
    OUTPUT_DIR = base / "data" / "processed"

    print("Reading from:", EXCEL_PATH)
    parse_scf_dataset(EXCEL_PATH, OUTPUT_DIR)

