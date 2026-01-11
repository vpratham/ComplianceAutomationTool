# SmartCompliance  
**AI‑powered Policy → SCF (Secure Controls Framework) Mapping Tool**

## ✅ Project Overview  
SmartCompliance is designed to automate the mapping of company policy clauses to the controls defined in the Secure Controls Framework (SCF). Using retrieval‑augmented generation (RAG) and semantic similarity techniques, it extracts policy text, matches to SCF controls, provides confidence scores and detailed explanations — helping organizations demonstrate compliance efficiently.

## 🎯 Key Features  
- Upload policy documents (PDF/DOCX) and automatically extract clauses  
- Match each clause to one or more SCF controls with “High / Medium / Low” confidence classification  
- Provide explainable mappings — semantic similarity, contextual explanation, matched control ID, domain  
- Interactive desktop GUI built with CustomTkinter + Tkinter for intuitive experience  
- Search/filter functionality (by SCF ID) with dynamic table view  
- Detailed clause‑level view: shows full clause text, all mapping explanations, scores, domains  
- FAQ & contact form for user support, with optional integration to Firebase Realtime Database (fallback to local storage when Firebase unavailable)  
- Export functionality: generate a PDF report summarizing mappings, charts (confidence distribution, domain coverage) and detailed mapping table  
- Modular backend: uses RAG pipeline for mapping, clean data‑structure (Parquet files) for storage and analysis

## 🧱 Project Structure  
```
/project
├── gui/                        ← Desktop application UI code  
│   ├── faqs_page.py            ← FAQ screen with contact form  
│   ├── mapping_page.py         ← Core mapping UI (run analysis, table view, detail popup)  
│   └── report_page.py          ← Compliance report dashboard & PDF download  
├── backend/                    ← Backend logic and pipeline  
│   └── rag_pipeline.py         ← RAG + semantic similarity mapping code  
├── data/
│   ├── processed/              ← Processed data & mappings (Parquet files)  
│   └── …  
├── assets/                     ← UI assets, icons, logos (if any)  
├── .gitignore                  ← Ignored files/folders  
├── README.md                   ← This file  
└── requirements.txt            ← Python dependencies
```

## 📦 Technology Stack  
- Python 3.x  
- CustomTkinter & Tkinter for GUI  
- Pandas & Parquet for data handling  
- Matplotlib (and possibly Seaborn) for charts  
- ReportLab for PDF generation  
- Semantic similarity & RAG (likely using embeddings + LLM) for mapping  
- Optional Firebase Realtime Database for FAQs and support queries  
- Git + GitHub for version control & collaboration

## 🛠 Getting Started  
### Prerequisites  
- Python 3.8+  
- (Recommended) Virtual environment  
  ```bash
  python -m venv .venv
  .venv\Scripts\activate    # Windows  
  source .venv/bin/activate # macOS/Linux  
  ```

### Install dependencies  
```bash
pip install -r requirements.txt
```

### Run the application  
```bash
python main.py
```
*(Assuming your entry‑point is `main.py` — if different, update accordingly)*

### Upload a policy & view mappings  
1. Launch the GUI.  
2. Click **Show Mapping** to run the backend pipeline.  
3. After completion, use the search bar to filter by SCF ID (e.g., `AC‑3`, `CC1.1`).  
4. Double‑click a row or click **View Details** to open the full explanation view.  
5. Navigate to the Report tab to view charts and export a PDF.

## 📝 FAQ & Support  
Access the FAQ page from the sidebar.  
If you encounter any issues or have additional questions, use the contact form — queries will go to Firebase if configured, else saved locally under `data/queries`.

## 📊 What’s Visualized  
- **Confidence Distribution** pie chart: Breakdown of High/Medium/Low confidence mappings  
- **Domain Coverage** bar chart: Top 10 SCF domains by number of mapped clauses  
- **Detailed Table**: Clause index, text snippet, matched SCF ID(s), domain, confidence, score, explanation

## 📁 Data & File Handling  
- Important processed data files (Parquet) are kept in `data/processed/` and **tracked** in Git if they are essential for the application.  
- Virtual environments (`.venv/`, `venv/`) and large library binaries are **excluded** from the repository (see `.gitignore`).  
- For large files or models (>100 MB) consider using Git Large File Storage (Git LFS).

## ✅ Best Practices  
- Use the search bar to quickly locate SCF mappings by control ID.  
- Manually review **low‑confidence** mappings — these may require human oversight.  
- Keep the processed Parquet files up‑to‑date after new policy uploads.  
- After exporting a PDF, archive it appropriately; avoid committing generated files if they bloat the repo.

## 🔮 Roadmap  
- Batch upload of multiple policy documents  
- Allow versioning of policies and mapping revisions  
- Add user authentication and cloud storage for policies and results  
- Integrate interactive dashboards (e.g., via Plotly) for deeper data exploration  
- Add “Explain this mapping” button to open LLM‑dialogue with user about a clause‑to‑control mapping  

## 📄 License  
MIT License — see `LICENSE` file for full details.
