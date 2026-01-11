# gui/upload_page.py
import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
import pandas as pd
import threading

from backend.policy_preprocessor import preprocess_policy
from backend.embedding_model import generate_embeddings
from backend.rag_pipeline import run_rag_explanations


class UploadPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="#f9fafb")
        self.last_processed_file = None

        # --- Color Palette ---
        self.COLOR_BLUE_PRIMARY = "#1648b3"
        self.COLOR_BLUE_HOVER = "#102e80"
        self.COLOR_BLUE_DEEP = "#1e3a8a"
        self.COLOR_GREEN_SUCCESS = "#059669"
        self.COLOR_RED_ERROR = "#dc2626"
        self.COLOR_TEXT_PRIMARY = "#111827"
        self.COLOR_TEXT_SECONDARY = "#6b7280"
        self.COLOR_BORDER = "#d1d5db"
        self.COLOR_CARD_BG = "#cbf7dd"

        self._setup_ui()

    def _setup_ui(self):
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=40, pady=30)

        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(4, weight=1)

        title_label = ctk.CTkLabel(
            content_frame,
            text="Upload Company Policy",
            font=("Helvetica", 24, "bold"),
            text_color=self.COLOR_BLUE_DEEP,
            anchor="w"
        )
        title_label.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 20))

        self.upload_btn = ctk.CTkButton(
            content_frame,
            text="Upload Policy File (PDF/DOCX)",
            font=("Helvetica", 14, "bold"),
            corner_radius=50,
            fg_color=self.COLOR_BLUE_PRIMARY,
            hover_color=self.COLOR_BLUE_HOVER,
            command=self.open_file_dialog,
            height=40
        )
        self.upload_btn.grid(row=1, column=0, sticky="w", pady=(0, 10))

        self.status_label = ctk.CTkLabel(
            content_frame,
            text="No file selected.",
            font=("Helvetica", 12),
            text_color=self.COLOR_TEXT_SECONDARY,
            anchor="w"
        )
        self.status_label.grid(row=2, column=0, sticky="w", pady=(0, 20))

        self.extraction_status_label = ctk.CTkLabel(
            content_frame,
            text="",
            font=("Helvetica", 16, "italic"),
            text_color=self.COLOR_TEXT_PRIMARY,
            anchor="w"
        )
        self.extraction_status_label.grid(row=3, column=0, sticky="w", pady=(0, 10))

        text_card = ctk.CTkFrame(
            content_frame,
            fg_color=self.COLOR_CARD_BG,
            corner_radius=12
        )
        text_card.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=10)
        text_card.grid_rowconfigure(1, weight=1)
        text_card.grid_columnconfigure(0, weight=1)

        processed_label = ctk.CTkLabel(
            text_card,
            text="Processed Clauses Preview",
            font=("Helvetica", 14, "bold"),
            text_color="#25592f",
            anchor="w"
        )
        processed_label.grid(row=0, column=0, sticky="w", padx=20, pady=(15, 10))

        self.processed_text = ctk.CTkTextbox(
            text_card,
            wrap="word",
            font=("Helvetica", 12),
            fg_color=self.COLOR_CARD_BG,
            text_color=self.COLOR_TEXT_PRIMARY,
            corner_radius=8,
            border_width=1,
            border_color=self.COLOR_BORDER
        )
        self.processed_text.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))

    # -------------------------
    # MAIN LOGIC
    # -------------------------
    def open_file_dialog(self):
        file_path = filedialog.askopenfilename(
            title="Open Policy File",
            filetypes=[("Documents", "*.pdf *.docx"), ("All Files", "*.*")]
        )
        if not file_path:
            return

        thread = threading.Thread(target=self._process_file, args=(Path(file_path),), daemon=True)
        thread.start()

    def _process_file(self, file_path: Path):
        try:
            self.upload_btn.configure(text="Processing...", state="disabled")
            self.status_label.configure(text=f"Processing: {file_path.name}", text_color=self.COLOR_TEXT_SECONDARY)
            self.extraction_status_label.configure(text="")
            self.processed_text.delete("1.0", "end")
            self.update_idletasks()

            base_dir = Path(__file__).resolve().parent.parent
            policy_dir = base_dir / "data" / "company_policies" / "processed"
            policy_dir.mkdir(parents=True, exist_ok=True)

            # 1️⃣ Preprocess uploaded document
            df = preprocess_policy(file_path, policy_dir)
            self.last_processed_file = policy_dir / f"{file_path.stem}_sentences.parquet"

            # ✅ Save latest uploaded path globally for RAG pipeline
            latest_path = self.last_processed_file
            with open(base_dir / "data" / "latest_policy_path.txt", "w") as f:
                f.write(str(latest_path))

            # 2️⃣ Generate embeddings for the new policy
            from backend.embedding_model import generate_embeddings
            model_dir = base_dir / "data" / "processed" / "embeddings"
            model_dir.mkdir(parents=True, exist_ok=True)

            generate_embeddings(
                self.last_processed_file,
                model_dir / "policy_embeddings.npy",
                model_name="all-mpnet-base-v2",
                text_column="clause_text"
            )

            # 3️⃣ Run RAG mapping automatically
            df_results = run_rag_explanations(prefer_local=True, threshold=0.5)

            # 4️⃣ Update UI
            preview_text = "\n\n---\n\n".join(df["clause_text"].tolist())
            self.processed_text.insert("end", preview_text)
            self.status_label.configure(text="✅ Full pipeline complete!", text_color=self.COLOR_GREEN_SUCCESS)
            self.extraction_status_label.configure(
                text=f"{len(df)} clauses processed from {file_path.name}",
                text_color=self.COLOR_TEXT_PRIMARY,
            )

            print("\n✅ Mapping complete! Results saved at: data/processed/explainable_mappings.parquet")

        except Exception as e:
            messagebox.showerror("Error", f"Pipeline failed:\n{e}")
            print(f"[ERROR] {e}")
            self.status_label.configure(text="❌ Pipeline failed.", text_color=self.COLOR_RED_ERROR)
        finally:
            self.upload_btn.configure(text="Upload Another Policy File", state="normal")


# --------------------------- DEMO ---------------------------
if __name__ == "__main__":
    root = ctk.CTk()
    root.title("SmartCompliance - Upload Policy")
    root.geometry("1000x750")
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    app = UploadPage(root)
    root.mainloop()
