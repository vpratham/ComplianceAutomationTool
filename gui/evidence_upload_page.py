# gui/evidence_upload_page.py
"""
GUI page for uploading evidence artifacts (PDFs, images, screenshots) and validating them
against SCF Evidence Request List (ERL) requirements.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import threading
import pandas as pd

from backend.evidence_validator import process_evidence_artifact
from backend.evidence_manager import register_evidence_validation, get_evidence_summary
from backend.scf_parser import clean_text


class EvidenceUploadPage(ctk.CTkFrame):
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
        self.COLOR_CARD_BG = "#cbf7dd"
        
        self.base_dir = Path(__file__).resolve().parent.parent
        self.selected_scf_id = None
        self.current_validation_result = None
        
        self._setup_ui()
        self._load_scf_controls()

    def _setup_ui(self):
        """Setup the UI components."""
        # Title
        title = ctk.CTkLabel(
            self,
            text="Upload Evidence Artifacts",
            font=("Helvetica", 24, "bold"),
            text_color=self.COLOR_BLUE_DEEP
        )
        title.pack(pady=(30, 20))

        # Main content frame
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=40, pady=20)

        # Left panel: Upload and selection
        left_panel = ctk.CTkFrame(content_frame, fg_color="white", corner_radius=12)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # SCF Control Selection
        scf_frame = ctk.CTkFrame(left_panel, fg_color="white")
        scf_frame.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            scf_frame,
            text="Select SCF Control:",
            font=("Helvetica", 14, "bold"),
            text_color=self.COLOR_TEXT_PRIMARY
        ).pack(anchor="w", pady=(0, 8))

        self.scf_var = ctk.StringVar(value="Select SCF Control ID...")
        self.scf_dropdown = ctk.CTkComboBox(
            scf_frame,
            values=["Loading..."],
            variable=self.scf_var,
            width=400,
            height=35,
            font=("Helvetica", 12),
            command=self._on_scf_selected
        )
        self.scf_dropdown.pack(fill="x", pady=(0, 10))

        # File upload section
        upload_frame = ctk.CTkFrame(left_panel, fg_color="white")
        upload_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            upload_frame,
            text="Upload Evidence File:",
            font=("Helvetica", 14, "bold"),
            text_color=self.COLOR_TEXT_PRIMARY
        ).pack(anchor="w", pady=(0, 8))

        file_info_frame = ctk.CTkFrame(upload_frame, fg_color="#f3f4f6", corner_radius=8)
        file_info_frame.pack(fill="x", pady=(0, 10))

        self.file_label = ctk.CTkLabel(
            file_info_frame,
            text="No file selected",
            font=("Helvetica", 11),
            text_color=self.COLOR_TEXT_SECONDARY,
            anchor="w"
        )
        self.file_label.pack(fill="x", padx=12, pady=12)

        self.upload_btn = ctk.CTkButton(
            upload_frame,
            text="Select Evidence File (PDF/Image)",
            font=("Helvetica", 13, "bold"),
            fg_color=self.COLOR_BLUE_PRIMARY,
            hover_color=self.COLOR_BLUE_HOVER,
            command=self._open_file_dialog,
            height=40,
            width=300
        )
        self.upload_btn.pack(pady=(0, 10))

        # Validation button
        self.validate_btn = ctk.CTkButton(
            upload_frame,
            text="Validate Evidence",
            font=("Helvetica", 13, "bold"),
            fg_color=self.COLOR_GREEN_SUCCESS,
            hover_color="#047857",
            command=self._validate_evidence,
            height=40,
            width=300,
            state="disabled"
        )
        self.validate_btn.pack(pady=(0, 10))

        # Progress bar
        self.progress = ttk.Progressbar(
            upload_frame,
            mode="indeterminate",
            length=300
        )
        self.progress.pack(fill="x", pady=(0, 10))

        # Status label
        self.status_label = ctk.CTkLabel(
            upload_frame,
            text="Select SCF control and upload evidence file to begin validation.",
            font=("Helvetica", 11),
            text_color=self.COLOR_TEXT_SECONDARY
        )
        self.status_label.pack(fill="x", pady=(0, 20))

        # Right panel: Validation results
        right_panel = ctk.CTkFrame(content_frame, fg_color="white", corner_radius=12)
        right_panel.pack(side="right", fill="both", expand=True, padx=(10, 0))

        results_title = ctk.CTkLabel(
            right_panel,
            text="Validation Results",
            font=("Helvetica", 16, "bold"),
            text_color=self.COLOR_BLUE_DEEP
        )
        results_title.pack(pady=(20, 15))

        # Results scrollable frame
        self.results_scroll = ctk.CTkScrollableFrame(
            right_panel,
            fg_color="#f9fafb",
            corner_radius=8
        )
        self.results_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Summary statistics at bottom
        self._display_summary(left_panel)

    def _load_scf_controls(self):
        """Load SCF controls for dropdown selection."""
        try:
            controls_path = self.base_dir / "data" / "processed" / "scf_controls.parquet"
            if not controls_path.exists():
                self.scf_dropdown.configure(values=["No SCF controls found. Please run SCF parser first."])
                return
            
            controls_df = pd.read_parquet(controls_path)
            
            # Create display strings: "SCF_ID - Control Title"
            scf_options = []
            for _, row in controls_df.iterrows():
                scf_id = row.get('scf_id', '')
                title = row.get('control_title', '')
                if scf_id and title:
                    display = f"{scf_id} - {title[:50]}"
                    scf_options.append(display)
                elif scf_id:
                    scf_options.append(str(scf_id))
            
            if scf_options:
                self.scf_dropdown.configure(values=scf_options)
            else:
                self.scf_dropdown.configure(values=["No controls available"])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load SCF controls: {e}")

    def _on_scf_selected(self, choice):
        """Handle SCF control selection."""
        if choice and " - " in choice:
            self.selected_scf_id = choice.split(" - ")[0]
        elif choice and choice not in ["Loading...", "No controls available", "No SCF controls found. Please run SCF parser first."]:
            self.selected_scf_id = choice
        else:
            self.selected_scf_id = None
        
        self._update_validate_button_state()

    def _open_file_dialog(self):
        """Open file dialog to select evidence file."""
        file_path = filedialog.askopenfilename(
            title="Select Evidence File",
            filetypes=[
                ("All Supported", "*.pdf *.png *.jpg *.jpeg *.tiff *.bmp *.gif *.webp"),
                ("PDF Files", "*.pdf"),
                ("Image Files", "*.png *.jpg *.jpeg *.tiff *.bmp *.gif *.webp"),
                ("All Files", "*.*")
            ]
        )
        
        if file_path:
            self.selected_file_path = Path(file_path)
            self.file_label.configure(
                text=f"Selected: {self.selected_file_path.name}",
                text_color=self.COLOR_TEXT_PRIMARY
            )
            self._update_validate_button_state()

    def _update_validate_button_state(self):
        """Update validate button state based on selections."""
        has_file = hasattr(self, 'selected_file_path') and self.selected_file_path
        has_scf = self.selected_scf_id is not None
        
        if has_file and has_scf:
            self.validate_btn.configure(state="normal")
        else:
            self.validate_btn.configure(state="disabled")

    def _validate_evidence(self):
        """Validate uploaded evidence against ERL requirements."""
        if not hasattr(self, 'selected_file_path') or not self.selected_file_path.exists():
            messagebox.showerror("Error", "Please select a valid evidence file.")
            return
        
        if not self.selected_scf_id:
            messagebox.showerror("Error", "Please select an SCF control ID.")
            return
        
        # Disable buttons and show progress
        self.validate_btn.configure(state="disabled")
        self.upload_btn.configure(state="disabled")
        self.progress.start(10)
        self.status_label.configure(
            text="Processing evidence... This may take a moment.",
            text_color=self.COLOR_BLUE_DEEP
        )
        
        # Run validation in background thread
        thread = threading.Thread(target=self._run_validation, daemon=True)
        thread.start()

    def _run_validation(self):
        """Run evidence validation in background thread."""
        try:
            # Process evidence
            result = process_evidence_artifact(
                str(self.selected_file_path),
                self.selected_scf_id,
                base_dir=self.base_dir,
                similarity_threshold=0.6
            )
            
            # Register in evidence manager
            if result.get('success'):
                result = register_evidence_validation(result, self.base_dir, copy_file=True)
            
            self.current_validation_result = result
            
            # Update UI in main thread
            self.after(0, self._display_validation_results, result)
            
        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda: messagebox.showerror("Validation Error", f"Failed to validate evidence:\n{error_msg}"))
            self.after(0, self._finish_validation, failed=True)

    def _display_validation_results(self, result: dict):
        """Display validation results in the UI."""
        # Clear previous results
        for widget in self.results_scroll.winfo_children():
            widget.destroy()
        
        if not result.get('success'):
            error_frame = ctk.CTkFrame(
                self.results_scroll,
                fg_color="#fee2e2",
                corner_radius=8
            )
            error_frame.pack(fill="x", padx=10, pady=10)
            
            ctk.CTkLabel(
                error_frame,
                text="❌ Validation Failed",
                font=("Helvetica", 14, "bold"),
                text_color=self.COLOR_RED_ERROR
            ).pack(anchor="w", padx=15, pady=(15, 5))
            
            ctk.CTkLabel(
                error_frame,
                text=f"Error: {result.get('error', 'Unknown error')}",
                font=("Helvetica", 11),
                text_color=self.COLOR_TEXT_PRIMARY,
                wraplength=400,
                justify="left"
            ).pack(anchor="w", padx=15, pady=(0, 15))
            
            self._finish_validation(failed=True)
            return
        
        # Validation status card
        status_color = self.COLOR_GREEN_SUCCESS if result.get('is_valid') else self.COLOR_RED_ERROR
        status_bg = "#d1fae5" if result.get('is_valid') else "#fee2e2"
        status_text = "✅ VALID" if result.get('is_valid') else "❌ INVALID"
        
        status_frame = ctk.CTkFrame(
            self.results_scroll,
            fg_color=status_bg,
            corner_radius=8
        )
        status_frame.pack(fill="x", padx=10, pady=(10, 15))
        
        ctk.CTkLabel(
            status_frame,
            text=status_text,
            font=("Helvetica", 18, "bold"),
            text_color=status_color
        ).pack(pady=15)
        
        # Confidence score
        confidence = result.get('confidence_score', 0.0)
        ctk.CTkLabel(
            status_frame,
            text=f"Confidence Score: {confidence:.3f}",
            font=("Helvetica", 13),
            text_color=self.COLOR_TEXT_PRIMARY
        ).pack(pady=(0, 15))
        
        # Details frame
        details_frame = ctk.CTkFrame(
            self.results_scroll,
            fg_color="white",
            corner_radius=8
        )
        details_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # SCF ID and File info
        info_items = [
            ("SCF Control ID:", result.get('scf_id', 'N/A')),
            ("File Name:", result.get('file_name', 'N/A')),
            ("File Type:", result.get('file_type', 'N/A').upper()),
            ("File Size:", f"{result.get('file_size', 0) / 1024:.1f} KB")
        ]
        
        for label, value in info_items:
            row_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
            row_frame.pack(fill="x", padx=15, pady=8)
            
            ctk.CTkLabel(
                row_frame,
                text=label,
                font=("Helvetica", 11, "bold"),
                text_color=self.COLOR_TEXT_SECONDARY,
                width=120,
                anchor="w"
            ).pack(side="left")
            
            ctk.CTkLabel(
                row_frame,
                text=str(value),
                font=("Helvetica", 11),
                text_color=self.COLOR_TEXT_PRIMARY,
                anchor="w"
            ).pack(side="left", padx=(10, 0))
        
        # Matched ERL requirement
        if result.get('matched_artifact_name'):
            erl_frame = ctk.CTkFrame(
                self.results_scroll,
                fg_color="#eff6ff",
                corner_radius=8
            )
            erl_frame.pack(fill="x", padx=10, pady=(0, 10))
            
            ctk.CTkLabel(
                erl_frame,
                text="Matched ERL Requirement:",
                font=("Helvetica", 12, "bold"),
                text_color=self.COLOR_BLUE_DEEP
            ).pack(anchor="w", padx=15, pady=(15, 5))
            
            ctk.CTkLabel(
                erl_frame,
                text=f"Artifact: {result.get('matched_artifact_name', 'N/A')}",
                font=("Helvetica", 11),
                text_color=self.COLOR_TEXT_PRIMARY,
                wraplength=450,
                justify="left"
            ).pack(anchor="w", padx=15, pady=(0, 5))
            
            artifact_desc = result.get('matched_artifact_desc', '')
            if artifact_desc:
                desc_short = artifact_desc[:300] + "..." if len(artifact_desc) > 300 else artifact_desc
                ctk.CTkLabel(
                    erl_frame,
                    text=f"Description: {desc_short}",
                    font=("Helvetica", 10),
                    text_color=self.COLOR_TEXT_SECONDARY,
                    wraplength=450,
                    justify="left"
                ).pack(anchor="w", padx=15, pady=(0, 15))
        
        # Validation explanation
        explanation = result.get('validation_explanation', '')
        if explanation:
            exp_frame = ctk.CTkFrame(
                self.results_scroll,
                fg_color="#f9fafb",
                corner_radius=8
            )
            exp_frame.pack(fill="x", padx=10, pady=(0, 10))
            
            ctk.CTkLabel(
                exp_frame,
                text="Explanation:",
                font=("Helvetica", 12, "bold"),
                text_color=self.COLOR_TEXT_PRIMARY
            ).pack(anchor="w", padx=15, pady=(15, 5))
            
            ctk.CTkLabel(
                exp_frame,
                text=explanation,
                font=("Helvetica", 10),
                text_color=self.COLOR_TEXT_SECONDARY,
                wraplength=450,
                justify="left"
            ).pack(anchor="w", padx=15, pady=(0, 15))
        
        # Extracted text preview
        extracted_preview = result.get('extracted_text_preview', '')
        if extracted_preview:
            text_frame = ctk.CTkFrame(
                self.results_scroll,
                fg_color="#f9fafb",
                corner_radius=8
            )
            text_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
            
            ctk.CTkLabel(
                text_frame,
                text="Extracted Text Preview:",
                font=("Helvetica", 12, "bold"),
                text_color=self.COLOR_TEXT_PRIMARY
            ).pack(anchor="w", padx=15, pady=(15, 5))
            
            text_preview = ctk.CTkTextbox(
                text_frame,
                height=150,
                wrap="word",
                font=("Helvetica", 10),
                fg_color="white"
            )
            text_preview.pack(fill="both", expand=True, padx=15, pady=(0, 15))
            text_preview.insert("1.0", extracted_preview)
            text_preview.configure(state="disabled")
        
        self._finish_validation(failed=False)

    def _display_summary(self, parent):
        """Display evidence summary statistics."""
        summary_frame = ctk.CTkFrame(parent, fg_color="#f3f4f6", corner_radius=8)
        summary_frame.pack(fill="x", padx=20, pady=(20, 20))
        
        ctk.CTkLabel(
            summary_frame,
            text="Evidence Summary",
            font=("Helvetica", 13, "bold"),
            text_color=self.COLOR_TEXT_PRIMARY
        ).pack(pady=(15, 10))
        
        try:
            summary = get_evidence_summary(self.base_dir)
            
            stats = [
                f"Total Evidence: {summary['total_evidence']}",
                f"Valid: {summary['valid_evidence']}",
                f"Invalid: {summary['invalid_evidence']}",
                f"SCF Controls Covered: {summary['unique_scf_controls']}",
                f"Avg Confidence: {summary['average_confidence']:.3f}"
            ]
            
            for stat in stats:
                ctk.CTkLabel(
                    summary_frame,
                    text=stat,
                    font=("Helvetica", 10),
                    text_color=self.COLOR_TEXT_SECONDARY
                ).pack(pady=3)
        except Exception:
            ctk.CTkLabel(
                summary_frame,
                text="No evidence records yet",
                font=("Helvetica", 10),
                text_color=self.COLOR_TEXT_SECONDARY
            ).pack(pady=3)
        
        ctk.CTkLabel(
            summary_frame,
            text="",  # Spacer
            height=10
        ).pack()

    def _finish_validation(self, failed=False):
        """Finish validation and re-enable UI."""
        self.progress.stop()
        self.validate_btn.configure(state="normal")
        self.upload_btn.configure(state="normal")
        
        if not failed:
            self.status_label.configure(
                text="Validation complete! Results displayed above.",
                text_color=self.COLOR_GREEN_SUCCESS
            )
            # Refresh summary
            self._display_summary_refresh()
        else:
            self.status_label.configure(
                text="Validation failed. Please check the error message.",
                text_color=self.COLOR_RED_ERROR
            )

    def _display_summary_refresh(self):
        """Refresh summary display."""
        # Find and update summary frame
        for widget in self.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                for child in widget.winfo_children():
                    if isinstance(child, ctk.CTkFrame) and "Summary" in str(child):
                        # Rebuild summary
                        break


if __name__ == "__main__":
    root = ctk.CTk()
    root.title("SmartCompliance - Evidence Upload")
    root.geometry("1200x800")
    app = EvidenceUploadPage(root)
    root.mainloop()

