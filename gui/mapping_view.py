import threading
import json
import pandas as pd
from pathlib import Path
import customtkinter as ctk
from tkinter import ttk, messagebox, Toplevel
from backend.rag_pipeline import run_rag_explanations


class MappingPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        # 🎨 Color Palette
        self.COLOR_BLUE_PRIMARY = "#1648b3"
        self.COLOR_BLUE_HOVER = "#102e80"
        self.COLOR_BLUE_DEEP = "#1e3a8a"
        self.COLOR_GREEN_SUCCESS = "#059669"
        self.COLOR_RED_ERROR = "#dc2626"
        self.COLOR_TEXT_PRIMARY = "#111827"
        self.COLOR_TEXT_SECONDARY = "#6b7280"
        self.COLOR_BORDER = "#d1d5db"
        self.COLOR_CARD_BG = "#cbf7dd"

        self._model_df = None
        self._full_model_df = None  # Store full dataset for filtering
        self._row_to_index = {}

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("green")

        self._setup_ui()

    # ------------------------- UI SETUP -------------------------
    def _setup_ui(self):
        self.configure(fg_color="white")

        # Title
        title = ctk.CTkLabel(
            self,
            text="Policy–SCF Compliance Mapping",
            font=("Helvetica", 24, "bold"),
            text_color=self.COLOR_BLUE_DEEP,
        )
        title.pack(pady=(30, 20))

        # Top control bar
        button_frame = ctk.CTkFrame(self, fg_color="white", corner_radius=12)
        button_frame.pack(fill="x", pady=(10, 15))

        self.run_btn = ctk.CTkButton(
            button_frame,
            text="Show Mapping",
            fg_color=self.COLOR_BLUE_PRIMARY,
            hover_color=self.COLOR_BLUE_HOVER,
            font=("Helvetica", 14, "bold"),
            corner_radius=50,
            height=40,
            width=200,
            command=self._run_analysis
        )
        self.run_btn.pack(padx=40, pady=20, side="left")

        # Progress bar (centered)
        self.progress = ttk.Progressbar(
            button_frame,
            mode="indeterminate",
            length=680
        )
        self.progress.pack(padx=10, pady=(25, 20), side="left")
        
        # Search bar frame (below button frame)
        search_frame = ctk.CTkFrame(self, fg_color="white", corner_radius=12)
        search_frame.pack(fill="x", padx=40, pady=(0, 15))
        
        # Search label
        search_label = ctk.CTkLabel(
            search_frame,
            text="Search by SCF ID:",
            font=("Helvetica", 12, "bold"),
            text_color=self.COLOR_TEXT_PRIMARY
        )
        search_label.pack(side="left", padx=(20, 10), pady=15)
        
        # Search entry
        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Enter SCF ID (e.g., CC1.1, AC-3, etc.)...",
            font=("Helvetica", 12),
            height=35,
            width=400,
            corner_radius=8
        )
        self.search_entry.pack(side="left", padx=(0, 10), pady=15)
        self.search_entry.bind("<KeyRelease>", self._on_search_change)
        
        # Clear search button
        self.clear_search_btn = ctk.CTkButton(
            search_frame,
            text="Clear",
            fg_color=self.COLOR_TEXT_SECONDARY,
            hover_color="#5d6979",
            font=("Helvetica", 12),
            height=35,
            width=80,
            corner_radius=50,
            command=self._clear_search
        )
        self.clear_search_btn.pack(side="left", padx=(0, 20), pady=15)
        
        # Results count label
        self.search_results_label = ctk.CTkLabel(
            search_frame,
            text="",
            font=("Helvetica", 11),
            text_color=self.COLOR_TEXT_SECONDARY
        )
        self.search_results_label.pack(side="right", padx=(0, 20), pady=15)

        # ---------------- TABLE SECTION ----------------
        table_frame = ctk.CTkFrame(
            self,
            fg_color=self.COLOR_CARD_BG,
            corner_radius=12,
            border_color=self.COLOR_BORDER,
            border_width=2
        )
        table_frame.pack(fill="both", expand=True, padx=40, pady=(20, 30))

        columns = ("Index", "ClauseText", "SCFMappedClauses", "Action")

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=15,
            style="Custom.Treeview"
        )

        # --- Table Headings ---
        self.tree.heading("Index", text="Index")
        self.tree.heading("ClauseText", text="Policy Clause")
        self.tree.heading("SCFMappedClauses", text="SCF Mapped Clauses")
        self.tree.heading("Action", text="Action")

        self.tree.column("Index", width=60, anchor="center")
        self.tree.column("ClauseText", width=310, anchor="w")
        self.tree.column("SCFMappedClauses", width=420, anchor="w")
        self.tree.column("Action", width=120, anchor="center")

        # --- Scrollbars ---
        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=y_scroll.set, xscroll=x_scroll.set)

        # --- Style (Borders + Alternating Rows + Header Colors) ---
        style = ttk.Style()

        # Base table style
        style.configure(
            "Custom.Treeview",
            font=("Helvetica", 10),
            rowheight=25,
            background="white",
            fieldbackground="white",
            bordercolor=self.COLOR_BORDER,
            highlightthickness=1,
            bd=1
        )

        # 🎨 Header style — dark blue with white text
        style.configure(
            "Custom.Treeview.Heading",
            font=("Helvetica", 11, "bold"),
            foreground=self.COLOR_BLUE_DEEP,                   # Header text color
            background=self.COLOR_BLUE_DEEP,      # Dark blue background
            relief="raised"
        )
        style.map("Custom.Treeview.Heading",
                background=[("active", self.COLOR_BLUE_HOVER)])

        # Zebra striping for readability
        self.tree.tag_configure("evenrow", background="#f9fafb")
        self.tree.tag_configure("oddrow", background="#ffffff")

        self.tree.pack(fill="both", expand=True, side="left", padx=10, pady=10)
        y_scroll.pack(side="right", fill="y")
        x_scroll.pack(side="bottom", fill="x")

        # Double-click for detail view
        self.tree.bind("<Button-1>", self._on_tree_click)

        # Centered status label
        self.status = ctk.CTkLabel(
            self,
            text="Ready to run mapping.",
            font=("Helvetica", 11),
            text_color=self.COLOR_TEXT_SECONDARY,
        )
        self.status.pack(pady=(10, 0))
        self.status.configure(anchor="center", justify="center")

    # ------------------------- RUN ANALYSIS -------------------------
    def _run_analysis(self):
        self.run_btn.configure(state="disabled")
        self.progress["mode"] = "indeterminate"
        self.progress.start(10)
        self.status.configure(text="Running mapping analysis...", text_color=self.COLOR_BLUE_DEEP)

        thread = threading.Thread(target=self._run_backend, daemon=True)
        thread.start()

    def _run_backend(self):
        try:
            df = run_rag_explanations(prefer_local=False)
            if isinstance(df, list):
                df = pd.DataFrame(df)
            self.after(0, lambda: self._load_results(df))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.after(0, self._finish_run)

    def _finish_run(self):
        self.progress.stop()
        self.run_btn.configure(state="normal")
        self.status.configure(
            text="Mapping completed successfully!",
            text_color=self.COLOR_GREEN_SUCCESS
        )

    # ------------------------- LOAD RESULTS -------------------------
    def _load_results(self, df=None):
        try:
            if df is None:
                base = Path(__file__).resolve().parents[1]
                candidates = list((base / "data" / "processed").glob("**/explainable_mappings.parquet"))
                if not candidates:
                    messagebox.showwarning("Missing Data", "No explainable_mappings.parquet found.")
                    return
                df = pd.read_parquet(max(candidates, key=lambda f: f.stat().st_mtime))

            if isinstance(df, list):
                df = pd.DataFrame(df)

            self._model_df = df.reset_index(drop=True)
            self._full_model_df = df.reset_index(drop=True).copy()  # Store full dataset
            self.status.configure(
                text=f"Loaded {len(df)} mapping results successfully.",
                text_color=self.COLOR_GREEN_SUCCESS
            )
            self._populate_table(df)
            self._update_search_results_label(len(df), len(df))

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load mapping results:\n{e}")

    # ------------------------- POPULATE TABLE -------------------------
    def _populate_table(self, df: pd.DataFrame):
        for i in self.tree.get_children():
            self.tree.delete(i)
        self._row_to_index.clear()

        for row_idx, row in df.iterrows():
            clause_index = row.get("clause_index", row_idx)
            clause_text = str(row.get("clause_text", "")).strip()
            mapping_expl = row.get("mapping_explanations", [])

            if isinstance(mapping_expl, str):
                try:
                    mapping_expl = json.loads(mapping_expl)
                except Exception:
                    mapping_expl = []
            if isinstance(mapping_expl, dict):
                mapping_expl = [mapping_expl]
            if not isinstance(mapping_expl, list):
                mapping_expl = []

            # Extract SCF IDs only
            scf_ids = []
            for m in mapping_expl:
                if isinstance(m, dict):
                    scf_id = m.get("matched_scf_id", "") or m.get("scf_id", "")
                    if scf_id:
                        scf_ids.append(scf_id)

            mapping_summary = ", ".join(scf_ids) if scf_ids else "No mappings found"
            tag = "evenrow" if row_idx % 2 == 0 else "oddrow"

            # Insert clause row with a button in the last column
            self.tree.insert(
                "", "end",
                iid=row_idx,
                values=(clause_index, clause_text, mapping_summary, "View Details"),
                tags=(tag,)
            )
            self._row_to_index[row_idx] = row_idx

        # Add a button in the last column using a custom cell renderer
        self.tree.bind("<Button-1>", self._on_tree_click)
    
    # ------------------------- SEARCH FUNCTIONALITY -------------------------
    def _on_search_change(self, event=None):
        """Filter table based on search input."""
        if self._full_model_df is None:
            return
        
        search_text = self.search_entry.get().strip().upper()
        
        if not search_text:
            # Show all results
            self._model_df = self._full_model_df.copy()
            self._populate_table(self._model_df)
            self._update_search_results_label(len(self._full_model_df), len(self._full_model_df))
            return
        
        # Filter rows where any SCF ID matches the search
        filtered_rows = []
        for idx, row in self._full_model_df.iterrows():
            mapping_expl = row.get("mapping_explanations", [])
            
            # Parse mapping explanations
            if isinstance(mapping_expl, str):
                try:
                    mapping_expl = json.loads(mapping_expl)
                except Exception:
                    mapping_expl = []
            if isinstance(mapping_expl, dict):
                mapping_expl = [mapping_expl]
            if not isinstance(mapping_expl, list):
                mapping_expl = []
            
            # Check if any SCF ID matches the search (case-insensitive, partial match)
            matches = False
            for m in mapping_expl:
                if isinstance(m, dict):
                    scf_id = str(m.get("matched_scf_id", "") or m.get("scf_id", "")).upper()
                    # Support partial matching: "CC1" should match "CC1.1", "CC1.2", etc.
                    if search_text in scf_id:
                        matches = True
                        break
            
            if matches:
                filtered_rows.append(idx)
        
        if filtered_rows:
            filtered_df = self._full_model_df.loc[filtered_rows].reset_index(drop=True)
            self._model_df = filtered_df
            self._populate_table(filtered_df)
            self._update_search_results_label(len(filtered_df), len(self._full_model_df))
        else:
            # No matches - clear table
            for i in self.tree.get_children():
                self.tree.delete(i)
            self._row_to_index.clear()
            self._update_search_results_label(0, len(self._full_model_df))
    
    def _clear_search(self):
        """Clear the search field and show all results."""
        self.search_entry.delete(0, "end")
        if self._full_model_df is not None:
            self._model_df = self._full_model_df.copy()
            self._populate_table(self._model_df)
            self._update_search_results_label(len(self._full_model_df), len(self._full_model_df))
    
    def _update_search_results_label(self, filtered_count, total_count):
        """Update the search results count label."""
        if filtered_count == total_count:
            self.search_results_label.configure(text="")
        else:
            self.search_results_label.configure(
                text=f"Showing {filtered_count} of {total_count} results",
                text_color=self.COLOR_BLUE_DEEP
            )

    def _on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            col = self.tree.identify_column(event.x)
            if col == "#4":  # 4th column (View Details)
                row_id = self.tree.identify_row(event.y)
                if row_id:
                    idx = int(row_id)
                    self._show_details_popup(idx)

    def _show_details_popup(self, idx):
        if self._model_df is None:
            return
        record = self._model_df.iloc[idx].to_dict()
        mapping_expl = record.get("mapping_explanations", [])
        if isinstance(mapping_expl, str):
            try:
                mapping_expl = json.loads(mapping_expl)
            except Exception:
                mapping_expl = []
        if isinstance(mapping_expl, dict):
            mapping_expl = [mapping_expl]
        if not isinstance(mapping_expl, list):
            mapping_expl = []

        top = Toplevel(master=self.winfo_toplevel())
        top.title(f"Clause Details — Index {idx}")
        top.geometry("800x750")
        top.resizable(True, True)

        # ✅ Main layout: top part scrollable, bottom fixed
        main_container = ctk.CTkFrame(top, fg_color="white")
        main_container.pack(fill="both", expand=True)

        scrollable = ctk.CTkScrollableFrame(main_container, fg_color="white", corner_radius=0)
        scrollable.pack(fill="both", expand=True, padx=8, pady=8)

        # Header info
        header_frame = ctk.CTkFrame(scrollable, fg_color="white")
        header_frame.pack(fill="x", padx=8, pady=(8, 2), anchor="w")

        ctk.CTkLabel(
            header_frame,
            text=f"Clause Index:",
            font=("Helvetica", 15, "bold"),
            text_color=self.COLOR_BLUE_DEEP,
            width=120,
            anchor="w"
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header_frame,
            text=str(record.get('clause_index', idx)),
            font=("Helvetica", 15),
            text_color=self.COLOR_TEXT_PRIMARY,
            anchor="w"
        ).grid(row=0, column=1, sticky="w", padx=(10,0))
        ctk.CTkLabel(
            header_frame,
            text=f"Clause Text:",
            font=("Helvetica", 13, "bold"),
            text_color=self.COLOR_BLUE_DEEP,
            width=120,
            anchor="nw"
        ).grid(row=1, column=0, sticky="nw", pady=(8,0))
        ctk.CTkLabel(
            header_frame,
            text=str(record.get('clause_text', '')),
            font=("Helvetica", 13),
            text_color=self.COLOR_TEXT_PRIMARY,
            wraplength=780,
            anchor="nw",
            justify="left"
        ).grid(row=1, column=1, sticky="nw", padx=(10,0), pady=(8,0))

        # Section title
        ctk.CTkLabel(
            scrollable,
            text="Mapping Explanations:",
            font=("Helvetica", 14, "bold"),
            text_color=self.COLOR_BLUE_DEEP
        ).pack(anchor="w", pady=(18, 4), padx=8)

        # ✅ Scrollable explanations container (no Treeview)
        for i, m in enumerate(mapping_expl):
            if not isinstance(m, dict):
                continue

            frame = ctk.CTkFrame(
                scrollable,
                fg_color="#cbf7dd",
                corner_radius=10,
                border_color=self.COLOR_BORDER,
                border_width=1
            )
            frame.pack(fill="x", padx=10, pady=6, anchor="w")

            scf_id = m.get("matched_scf_id", "")
            scf_domain = m.get("matched_domain", "")
            confidence = m.get("confidence_comment", "")
            explanation = m.get("explanation", "")

            # Extract semantic similarity score
            import re, textwrap
            sim_score_match = re.search(r"semantic similarity score (?:is|of) ([0-9.]+)", explanation)
            sim_score = sim_score_match.group(1) if sim_score_match else ""

            # Clean explanation text and wrap it nicely
            explanation_clean = self._extract_scf_text_popup(explanation)
            explanation_clean = re.sub(r"\s+", " ", explanation_clean).strip()
            explanation_wrapped = textwrap.fill(explanation_clean, width=110)

            # Each entry displayed clearly
            ctk.CTkLabel(frame, text=f"SCF ID: {scf_id}", font=("Helvetica", 13, "bold"), text_color=self.COLOR_BLUE_DEEP, anchor="w").pack(anchor="w", padx=10, pady=(6, 0))
            ctk.CTkLabel(frame, text=f"Domain: {scf_domain}", font=("Helvetica", 13), text_color=self.COLOR_TEXT_PRIMARY, anchor="w").pack(anchor="w", padx=10, pady=(0, 0))
            ctk.CTkLabel(frame, text=f"Confidence: {confidence}", font=("Helvetica", 13), text_color=self.COLOR_TEXT_PRIMARY, anchor="w").pack(anchor="w", padx=10, pady=(0, 0))
            if sim_score:
                ctk.CTkLabel(frame, text=f"Similarity Score: {sim_score}", font=("Helvetica", 13), text_color="#06402B", anchor="w").pack(anchor="w", padx=10, pady=(0, 4))
            ctk.CTkLabel(
                frame,
                text=f"Explanation: {explanation_wrapped}",
                font=("Helvetica", 13),
                text_color=self.COLOR_TEXT_PRIMARY,
                anchor="w",
                justify="left",
                wraplength=1200
            ).pack(fill="x", padx=10, pady=(0, 8))

        # ✅ Bottom buttons frame (always visible)
        btn_frame = ctk.CTkFrame(main_container, fg_color="white")
        btn_frame.pack(fill="x", padx=8, pady=8, side="bottom")

        ctk.CTkButton(
            btn_frame,
            text="Close",
            fg_color=self.COLOR_BLUE_PRIMARY,
            hover_color=self.COLOR_BLUE_HOVER,
            command=top.destroy
        ).pack(side="right", padx=6, pady=6)

# --- Helpers (shared logic with report_page) ---
    def _extract_scf_text_popup(self, explanation: str) -> str:
        """Extract the SCF control quoted text robustly for the details popup.
        Same approach as report_page._extract_scf_text: allow apostrophes by
        selecting the last matching closing quote.
        """
        if not explanation:
            return ""
        import re
        text = str(explanation)
        phrase = re.search(r"scf\s+control\s+text\s+that\s+says", text, flags=re.IGNORECASE)
        if phrase:
            start = phrase.end()
            openers = {"\"": "\"", "'": "'", "“": "”", "‘": "’"}
            opener_idx = -1
            opener_char = None
            for i in range(start, len(text)):
                ch = text[i]
                if ch in openers:
                    opener_idx = i
                    opener_char = ch
                    break
            if opener_idx != -1:
                closer_char = openers[opener_char]
                closer_idx = text.rfind(closer_char)
                if closer_idx > opener_idx + 1:
                    return text[opener_idx + 1: closer_idx].strip(" '”’\"").rstrip('.')

        # Fallbacks
        m = re.search(r'"([^\"]+)"', text)
        if m:
            return m.group(1).strip(" '”’\"").rstrip('.')
        m = re.search(r'“([^”]+)”', text)
        if m:
            return m.group(1).strip(" '”’\"").rstrip('.')
        first = text.find("'")
        last = text.rfind("'")
        if first != -1 and last > first:
            return text[first + 1:last].strip(" '”’\"").rstrip('.')
        return text.strip(" '”’\"").rstrip('.')
# --------------------------- DEMO ---------------------------
if __name__ == "__main__":
    root = ctk.CTk()
    root.title("SmartCompliance - Mapping View")
    root.geometry("1150x750")
    app = MappingPage(root)
    root.mainloop()
