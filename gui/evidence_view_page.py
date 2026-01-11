# gui/evidence_view_page.py
"""
GUI page for viewing and managing uploaded evidence artifacts and their validation results.
Shows evidence registry, allows filtering by SCF ID, and displays validation status.
"""

import customtkinter as ctk
from tkinter import ttk, messagebox
from pathlib import Path
import pandas as pd
from datetime import datetime
import json

from backend.evidence_manager import load_evidence_registry, get_evidence_summary, delete_evidence_record
from backend.scf_parser import clean_text


class EvidenceViewPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="#f9fafb")
        
        # Color Palette
        self.COLOR_BLUE_PRIMARY = "#1648b3"
        self.COLOR_BLUE_HOVER = "#102e80"
        self.COLOR_BLUE_DEEP = "#1e3a8a"
        self.COLOR_GREEN_SUCCESS = "#059669"
        self.COLOR_RED_ERROR = "#dc2626"
        self.COLOR_TEXT_PRIMARY = "#111827"
        self.COLOR_TEXT_SECONDARY = "#6b7280"
        self.COLOR_BORDER = "#d1d5db"
        
        self.base_dir = Path(__file__).resolve().parent.parent
        self.evidence_df = None
        
        self._setup_ui()
        self.load_evidence_data()

    def _setup_ui(self):
        """Setup the UI components."""
        # Title
        title = ctk.CTkLabel(
            self,
            text="Evidence Registry",
            font=("Helvetica", 24, "bold"),
            text_color=self.COLOR_BLUE_DEEP
        )
        title.pack(pady=(30, 20))

        # Summary cards
        self._create_summary_cards()

        # Search and filter frame
        filter_frame = ctk.CTkFrame(self, fg_color="white", corner_radius=12)
        filter_frame.pack(fill="x", padx=40, pady=(10, 15))

        search_label = ctk.CTkLabel(
            filter_frame,
            text="Filter by SCF ID:",
            font=("Helvetica", 12, "bold"),
            text_color=self.COLOR_TEXT_PRIMARY
        )
        search_label.pack(side="left", padx=(20, 10), pady=15)

        self.search_entry = ctk.CTkEntry(
            filter_frame,
            placeholder_text="Enter SCF ID (e.g., CC1.1, AC-3)...",
            font=("Helvetica", 12),
            height=35,
            width=300,
            corner_radius=8
        )
        self.search_entry.pack(side="left", padx=(0, 10), pady=15)
        self.search_entry.bind("<KeyRelease>", self._on_search_change)

        self.clear_btn = ctk.CTkButton(
            filter_frame,
            text="Clear",
            fg_color=self.COLOR_TEXT_SECONDARY,
            hover_color="#5d6979",
            font=("Helvetica", 12),
            height=35,
            width=80,
            command=self._clear_search
        )
        self.clear_btn.pack(side="left", padx=(0, 10), pady=15)

        # Filter by validation status
        status_label = ctk.CTkLabel(
            filter_frame,
            text="Status:",
            font=("Helvetica", 12, "bold"),
            text_color=self.COLOR_TEXT_PRIMARY
        )
        status_label.pack(side="left", padx=(20, 10), pady=15)

        self.status_var = ctk.StringVar(value="All")
        status_dropdown = ctk.CTkComboBox(
            filter_frame,
            values=["All", "Valid", "Invalid"],
            variable=self.status_var,
            width=150,
            height=35,
            command=self._on_status_filter
        )
        status_dropdown.pack(side="left", padx=(0, 20), pady=15)

        # Refresh button
        refresh_btn = ctk.CTkButton(
            filter_frame,
            text="Refresh",
            fg_color=self.COLOR_BLUE_PRIMARY,
            hover_color=self.COLOR_BLUE_HOVER,
            font=("Helvetica", 12, "bold"),
            height=35,
            width=100,
            command=self.load_evidence_data
        )
        refresh_btn.pack(side="right", padx=(0, 20), pady=15)

        # Results count label
        self.results_label = ctk.CTkLabel(
            filter_frame,
            text="",
            font=("Helvetica", 11),
            text_color=self.COLOR_TEXT_SECONDARY
        )
        self.results_label.pack(side="right", padx=(0, 20), pady=15)

        # Table frame
        table_frame = ctk.CTkFrame(
            self,
            fg_color="white",
            corner_radius=12
        )
        table_frame.pack(fill="both", expand=True, padx=40, pady=(0, 30))

        # Create table
        columns = ("Index", "SCF ID", "File Name", "Type", "Status", "Confidence", "Matched ERL", "Date", "Action")
        
        style = ttk.Style()
        style.configure(
            "Evidence.Treeview",
            font=("Helvetica", 10),
            rowheight=25,
            background="white",
            fieldbackground="white"
        )
        style.configure(
            "Evidence.Treeview.Heading",
            font=("Helvetica", 11, "bold"),
            foreground=self.COLOR_BLUE_DEEP,
            background=self.COLOR_BLUE_DEEP,
            relief="raised"
        )
        style.map("Evidence.Treeview.Heading",
                 background=[("active", self.COLOR_BLUE_HOVER)])

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=20,
            style="Evidence.Treeview"
        )

        # Configure columns
        col_widths = {
            "Index": 60,
            "SCF ID": 100,
            "File Name": 250,
            "Type": 80,
            "Status": 80,
            "Confidence": 100,
            "Matched ERL": 120,
            "Date": 150,
            "Action": 100
        }

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=col_widths.get(col, 120), anchor="w")

        # Scrollbars
        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=y_scroll.set, xscroll=x_scroll.set)

        # Tags for row coloring
        self.tree.tag_configure("valid", background="#d1fae5")
        self.tree.tag_configure("invalid", background="#fee2e2")
        self.tree.tag_configure("evenrow", background="#f9fafb")
        self.tree.tag_configure("oddrow", background="white")

        self.tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        y_scroll.pack(side="right", fill="y")
        x_scroll.pack(side="bottom", fill="x")

        # Bind double-click to view details
        self.tree.bind("<Double-1>", self._on_row_double_click)

    def _create_summary_cards(self):
        """Create summary statistics cards."""
        summary_frame = ctk.CTkFrame(self, fg_color="transparent")
        summary_frame.pack(fill="x", padx=40, pady=(0, 10))

        try:
            summary = get_evidence_summary(self.base_dir)
            
            cards = [
                ("Total Evidence", str(summary['total_evidence']), self.COLOR_BLUE_DEEP),
                ("Valid", str(summary['valid_evidence']), self.COLOR_GREEN_SUCCESS),
                ("Invalid", str(summary['invalid_evidence']), self.COLOR_RED_ERROR),
                ("SCF Controls", str(summary['unique_scf_controls']), self.COLOR_BLUE_PRIMARY),
                ("Avg Confidence", f"{summary['average_confidence']:.3f}", self.COLOR_TEXT_PRIMARY)
            ]

            for i, (label, value, color) in enumerate(cards):
                card = ctk.CTkFrame(summary_frame, fg_color="white", corner_radius=8, width=200)
                card.pack(side="left", padx=10, pady=5)
                card.pack_propagate(False)

                ctk.CTkLabel(
                    card,
                    text=label,
                    font=("Helvetica", 11),
                    text_color=self.COLOR_TEXT_SECONDARY
                ).pack(pady=(15, 5))

                ctk.CTkLabel(
                    card,
                    text=value,
                    font=("Helvetica", 20, "bold"),
                    text_color=color
                ).pack(pady=(0, 15))

        except Exception:
            pass

    def load_evidence_data(self):
        """Load evidence registry data."""
        try:
            self.evidence_df = load_evidence_registry(self.base_dir)
            self._populate_table(self.evidence_df)
            self._create_summary_cards_refresh()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load evidence data: {e}")

    def _populate_table(self, df: pd.DataFrame):
        """Populate table with evidence data."""
        # Clear existing rows
        for item in self.tree.get_children():
            self.tree.delete(item)

        if df is None or len(df) == 0:
            return

        for idx, row in df.iterrows():
            # Format date
            timestamp = row.get('timestamp', '')
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    date_str = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    date_str = timestamp[:16] if len(timestamp) > 16 else timestamp
            else:
                date_str = "N/A"

            # Determine status
            is_valid = row.get('is_valid', False)
            status = "✅ Valid" if is_valid else "❌ Invalid"
            tag = "valid" if is_valid else "invalid"
            
            # Add alternating row tag
            if idx % 2 == 0:
                tag = f"{tag} evenrow"
            else:
                tag = f"{tag} oddrow"

            # Confidence score
            confidence = row.get('confidence_score', 0.0)
            conf_str = f"{confidence:.3f}" if confidence else "N/A"

            # Matched ERL
            erl_id = row.get('matched_erl_id', '') or row.get('matched_artifact_name', '')
            erl_str = erl_id[:20] + "..." if len(str(erl_id)) > 20 else str(erl_id) if erl_id else "N/A"

            # File type
            file_type = row.get('file_type', 'unknown').upper()

            values = (
                idx,
                row.get('scf_id', 'N/A'),
                row.get('file_name', 'N/A'),
                file_type,
                status,
                conf_str,
                erl_str,
                date_str,
                "View Details"
            )

            self.tree.insert("", "end", values=values, tags=(tag,))

        self._update_results_label(len(df), len(df))

    def _on_search_change(self, event=None):
        """Filter table based on search input."""
        if self.evidence_df is None or len(self.evidence_df) == 0:
            return

        search_text = self.search_entry.get().strip().upper()
        status_filter = self.status_var.get()

        # Filter by SCF ID
        if search_text:
            filtered_df = self.evidence_df[
                self.evidence_df['scf_id'].astype(str).str.upper().str.contains(search_text, na=False)
            ].copy()
        else:
            filtered_df = self.evidence_df.copy()

        # Filter by status
        if status_filter == "Valid":
            filtered_df = filtered_df[filtered_df['is_valid'] == True].copy()
        elif status_filter == "Invalid":
            filtered_df = filtered_df[filtered_df['is_valid'] == False].copy()

        self._populate_table(filtered_df)

    def _on_status_filter(self, choice):
        """Handle status filter change."""
        self._on_search_change()

    def _clear_search(self):
        """Clear search and show all results."""
        self.search_entry.delete(0, "end")
        self.status_var.set("All")
        if self.evidence_df is not None:
            self._populate_table(self.evidence_df)

    def _update_results_label(self, filtered_count, total_count):
        """Update results count label."""
        if filtered_count == total_count:
            self.results_label.configure(text=f"Showing all {total_count} evidence records")
        else:
            self.results_label.configure(text=f"Showing {filtered_count} of {total_count} records")

    def _on_row_double_click(self, event):
        """Handle double-click on table row to show details."""
        selection = self.tree.selection()
        if not selection:
            return

        item = self.tree.item(selection[0])
        idx = item['values'][0]  # Index column

        if self.evidence_df is None or idx >= len(self.evidence_df):
            return

        row = self.evidence_df.iloc[idx]
        self._show_details_popup(row, idx)

    def _show_details_popup(self, row, idx):
        """Show detailed evidence information in popup."""
        top = ctk.CTkToplevel(self.winfo_toplevel())
        top.title(f"Evidence Details - {row.get('file_name', 'Unknown')}")
        top.geometry("900x800")
        top.resizable(True, True)

        # Scrollable frame
        scroll_frame = ctk.CTkScrollableFrame(top, fg_color="white")
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Status header
        is_valid = row.get('is_valid', False)
        status_color = self.COLOR_GREEN_SUCCESS if is_valid else self.COLOR_RED_ERROR
        status_bg = "#d1fae5" if is_valid else "#fee2e2"
        status_text = "✅ VALID" if is_valid else "❌ INVALID"

        status_frame = ctk.CTkFrame(scroll_frame, fg_color=status_bg, corner_radius=8)
        status_frame.pack(fill="x", padx=10, pady=(10, 15))

        ctk.CTkLabel(
            status_frame,
            text=status_text,
            font=("Helvetica", 18, "bold"),
            text_color=status_color
        ).pack(pady=15)

        # Details section
        details_frame = ctk.CTkFrame(scroll_frame, fg_color="#f9fafb", corner_radius=8)
        details_frame.pack(fill="x", padx=10, pady=(0, 10))

        info_items = [
            ("Registry ID:", idx),
            ("SCF Control ID:", row.get('scf_id', 'N/A')),
            ("File Name:", row.get('file_name', 'N/A')),
            ("File Type:", row.get('file_type', 'N/A').upper()),
            ("File Size:", f"{row.get('file_size', 0) / 1024:.1f} KB"),
            ("Confidence Score:", f"{row.get('confidence_score', 0.0):.3f}"),
            ("Matched ERL ID:", row.get('matched_erl_id', 'N/A')),
            ("Matched Artifact:", row.get('matched_artifact_name', 'N/A')),
            ("Area of Focus:", row.get('matched_area_focus', 'N/A')),
            ("Upload Date:", row.get('timestamp', 'N/A')[:19] if row.get('timestamp') else 'N/A')
        ]

        for label, value in info_items:
            row_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
            row_frame.pack(fill="x", padx=15, pady=8)

            ctk.CTkLabel(
                row_frame,
                text=label,
                font=("Helvetica", 11, "bold"),
                text_color=self.COLOR_TEXT_SECONDARY,
                width=150,
                anchor="w"
            ).pack(side="left")

            ctk.CTkLabel(
                row_frame,
                text=str(value),
                font=("Helvetica", 11),
                text_color=self.COLOR_TEXT_PRIMARY,
                anchor="w"
            ).pack(side="left", padx=(10, 0))

        # Artifact description
        artifact_desc = row.get('matched_artifact_desc', '')
        if artifact_desc:
            desc_frame = ctk.CTkFrame(scroll_frame, fg_color="#eff6ff", corner_radius=8)
            desc_frame.pack(fill="x", padx=10, pady=(0, 10))

            ctk.CTkLabel(
                desc_frame,
                text="Matched ERL Artifact Description:",
                font=("Helvetica", 12, "bold"),
                text_color=self.COLOR_BLUE_DEEP
            ).pack(anchor="w", padx=15, pady=(15, 5))

            ctk.CTkLabel(
                desc_frame,
                text=artifact_desc,
                font=("Helvetica", 11),
                text_color=self.COLOR_TEXT_PRIMARY,
                wraplength=850,
                justify="left"
            ).pack(anchor="w", padx=15, pady=(0, 15))

        # Validation explanation
        explanation = row.get('validation_explanation', '')
        if explanation:
            exp_frame = ctk.CTkFrame(scroll_frame, fg_color="#f9fafb", corner_radius=8)
            exp_frame.pack(fill="x", padx=10, pady=(0, 10))

            ctk.CTkLabel(
                exp_frame,
                text="Validation Explanation:",
                font=("Helvetica", 12, "bold"),
                text_color=self.COLOR_TEXT_PRIMARY
            ).pack(anchor="w", padx=15, pady=(15, 5))

            ctk.CTkLabel(
                exp_frame,
                text=explanation,
                font=("Helvetica", 10),
                text_color=self.COLOR_TEXT_SECONDARY,
                wraplength=850,
                justify="left"
            ).pack(anchor="w", padx=15, pady=(0, 15))

        # Extracted text preview
        extracted_preview = row.get('extracted_text_preview', '')
        if extracted_preview:
            text_frame = ctk.CTkFrame(scroll_frame, fg_color="#f9fafb", corner_radius=8)
            text_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

            ctk.CTkLabel(
                text_frame,
                text="Extracted Text Preview:",
                font=("Helvetica", 12, "bold"),
                text_color=self.COLOR_TEXT_PRIMARY
            ).pack(anchor="w", padx=15, pady=(15, 5))

            text_preview = ctk.CTkTextbox(
                text_frame,
                height=200,
                wrap="word",
                font=("Helvetica", 10),
                fg_color="white"
            )
            text_preview.pack(fill="both", expand=True, padx=15, pady=(0, 15))
            text_preview.insert("1.0", extracted_preview)
            text_preview.configure(state="disabled")

        # Close button
        btn_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(
            btn_frame,
            text="Close",
            fg_color=self.COLOR_BLUE_PRIMARY,
            hover_color=self.COLOR_BLUE_HOVER,
            command=top.destroy,
            width=100
        ).pack(side="right", padx=10)

    def _create_summary_cards_refresh(self):
        """Refresh summary cards (placeholder for now)."""
        # Summary cards are recreated when data is loaded
        pass


if __name__ == "__main__":
    root = ctk.CTk()
    root.title("SmartCompliance - Evidence Registry")
    root.geometry("1400x800")
    app = EvidenceViewPage(root)
    root.mainloop()

