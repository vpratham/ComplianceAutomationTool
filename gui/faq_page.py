import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import datetime

# Import Firebase configuration
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)

try:
    from gui.firebase_config import database
    FIREBASE_AVAILABLE = database is not None
except Exception as e:
    # Suppress error messages - Firebase will fallback to local storage
    FIREBASE_AVAILABLE = False
    database = None

class FAQPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill="both", expand=True)
        self.configure(fg_color="#f9fafb")
        self.expanded_items = {}  # Track which FAQ items are expanded
        self._build_ui()

    def _build_ui(self):
        # Title
        title = ctk.CTkLabel(
            self, 
            text="Frequently Asked Questions", 
            font=("Helvetica", 28, "bold"), 
            text_color="#1e3a8a"
        )
        title.pack(pady=(30, 10))

        # Subtitle
        subtitle = ctk.CTkLabel(
            self,
            text="Find answers to common questions about SmartCompliance",
            font=("Helvetica", 14),
            text_color="#6b7280"
        )
        subtitle.pack(pady=(0, 30))

        # Scrollable frame for FAQ items
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self.scroll_frame.pack(fill="both", expand=True, padx=40, pady=10)

        # FAQ Data
        self.faq_data = [
            {
                "question": "What is SmartCompliance?",
                "answer": "SmartCompliance is an AI-powered compliance mapping tool that automatically maps your company policies to the Secure Controls Framework (SCF). It uses advanced RAG (Retrieval-Augmented Generation) technology to provide explainable mappings with confidence scores, helping you demonstrate compliance efficiently."
            },
            {
                "question": "How do I upload a policy document?",
                "answer": "Navigate to the Upload page from the sidebar, click 'Select Policy File', and choose a PDF or DOCX file. The system will automatically process and extract relevant clauses from your policy document. Once uploaded, you can view the mappings on the Mapping page."
            },
            {
                "question": "What file formats are supported?",
                "answer": "SmartCompliance currently supports PDF (.pdf) and Microsoft Word (.docx) file formats. Make sure your documents are readable and contain text (not just scanned images)."
            },
            {
                "question": "What does the confidence score mean?",
                "answer": "The confidence score indicates how well a policy clause matches a specific SCF control:\n\n• High Confidence: Strong semantic match with detailed explanation\n• Medium Confidence: Moderate match with some relevance\n• Low Confidence: Weak match that may require manual review\n\nThe system uses semantic similarity scores to calculate these confidence levels."
            },
            {
                "question": "How accurate are the mappings?",
                "answer": "SmartCompliance uses state-of-the-art embedding models and LLM explainers to provide accurate mappings. While the system is highly effective, we recommend reviewing low-confidence mappings manually to ensure complete accuracy for your specific compliance requirements."
            },
            {
                "question": "Can I export my compliance report?",
                "answer": "Yes! On the Report page, you can download a comprehensive PDF report containing all your policy-to-SCF mappings, confidence scores, and detailed explanations. This report can be used for audits and compliance documentation."
            },
            {
                "question": "What is the Secure Controls Framework (SCF)?",
                "answer": "The Secure Controls Framework (SCF) is a comprehensive cybersecurity control framework that provides a structured approach to implementing security controls. SmartCompliance maps your policies to SCF controls to help you demonstrate compliance with industry standards."
            },
            {
                "question": "How long does it take to process a policy?",
                "answer": "Processing time depends on the size of your policy document. Typically, a standard policy document (10-50 pages) processes in 1-3 minutes. Larger documents may take longer."
            },
            {
                "question": "Can I map multiple policies?",
                "answer": "Currently, you can upload and map one policy at a time. To map multiple policies, upload them sequentially and review the mappings for each policy separately. Future versions will support batch processing."
            },
            {
                "question": "What happens to my data?",
                "answer": "Your policy documents and mappings are processed locally or on secure servers. We prioritize data privacy and security. Processed data is stored in the 'data' directory of your installation. You can delete uploaded files at any time."
            },
            {
                "question": "How do I interpret the mapping explanations?",
                "answer": "Each mapping includes a detailed explanation showing why a policy clause matches a specific SCF control. The explanation highlights key semantic similarities and provides context. Look for highlighted terms and similarity scores to understand the connection."
            },
            {
                "question": "What if I need help with a specific mapping?",
                "answer": "If you're unsure about a mapping or need clarification, use the contact form at the bottom of this page to reach out to our support team. Include the clause text and SCF ID in your query for faster assistance."
            }
        ]

        # Render FAQ items
        self._render_faq_items()

        # Separator
        separator = ctk.CTkFrame(self.scroll_frame, height=2, fg_color="#e5e7eb")
        separator.pack(fill="x", pady=30)

        # Contact Form Section
        self._build_contact_form()

    def _render_faq_items(self):
        """Render all FAQ items with expandable/collapsible functionality."""
        for idx, faq in enumerate(self.faq_data):
            self._create_faq_item(idx, faq["question"], faq["answer"])

    def _create_faq_item(self, idx, question, answer):
        """Create an expandable FAQ item."""
        # Main container for the FAQ item
        item_frame = ctk.CTkFrame(
            self.scroll_frame, 
            fg_color="white", 
            corner_radius=12,
            border_width=1,
            border_color="#e5e7eb"
        )
        item_frame.pack(fill="x", pady=8, padx=10)

        # Question row (always visible)
        question_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        question_frame.pack(fill="x", padx=20, pady=15, anchor="n")

        question_label = ctk.CTkLabel(
            question_frame,
            text=question,
            font=("Helvetica", 15, "bold"),
            text_color="#1f2937",
            anchor="w",
            justify="left"
        )
        question_label.pack(side="left", fill="x", expand=True)

        # Expand/collapse button
        expand_btn = ctk.CTkButton(
            question_frame,
            text="+",
            width=30,
            height=30,
            font=("Helvetica", 18, "bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            text_color="white",
            corner_radius=15,
            command=lambda i=idx: self._toggle_faq(i)
        )
        expand_btn.pack(side="right", padx=(10, 0))

        # Answer frame (initially hidden)
        answer_frame = ctk.CTkFrame(item_frame, fg_color="#f9fafb", corner_radius=8)
        # Pack it but hide it initially
        answer_frame.pack(fill="x", padx=20, pady=(0, 15))
        answer_frame.pack_forget()  # Hide initially

        answer_label = ctk.CTkLabel(
            answer_frame,
            text=answer,
            font=("Helvetica", 13),
            text_color="#4b5563",
            anchor="nw",
            justify="left",
            wraplength=700
        )
        answer_label.pack(fill="x", padx=15, pady=15)

        # Store references
        self.expanded_items[idx] = {
            "item_frame": item_frame,
            "question_frame": question_frame,
            "answer_frame": answer_frame,
            "expand_btn": expand_btn,
            "is_expanded": False
        }

    def _toggle_faq(self, idx):
        """Toggle the expansion state of an FAQ item."""
        item = self.expanded_items[idx]
        
        if item["is_expanded"]:
            # Collapse
            item["answer_frame"].pack_forget()
            item["expand_btn"].configure(text="+")
            item["is_expanded"] = False
        else:
            # Expand - pack answer frame (it will appear below question_frame)
            item["answer_frame"].pack(fill="x", padx=20, pady=(0, 15))
            item["expand_btn"].configure(text="−")
            item["is_expanded"] = True

    def _build_contact_form(self):
        """Build the contact form at the bottom."""
        # Section title
        form_title = ctk.CTkLabel(
            self.scroll_frame,
            text="Still have questions?",
            font=("Helvetica", 22, "bold"),
            text_color="#1e3a8a"
        )
        form_title.pack(pady=(20, 10))

        form_subtitle = ctk.CTkLabel(
            self.scroll_frame,
            text="Contact us and we'll get back to you as soon as possible",
            font=("Helvetica", 13),
            text_color="#6b7280"
        )
        form_subtitle.pack(pady=(0, 25))

        # Form container
        form_frame = ctk.CTkFrame(
            self.scroll_frame,
            fg_color="white",
            corner_radius=12,
            border_width=1,
            border_color="#e5e7eb"
        )
        form_frame.pack(fill="x", padx=10, pady=(0, 30))

        # Form fields container
        fields_container = ctk.CTkFrame(form_frame, fg_color="transparent")
        fields_container.pack(fill="x", padx=30, pady=30)

        # Name field
        name_label = ctk.CTkLabel(
            fields_container,
            text="Name *",
            font=("Helvetica", 13, "bold"),
            text_color="#374151",
            anchor="w"
        )
        name_label.pack(fill="x", pady=(0, 8))

        self.name_entry = ctk.CTkEntry(
            fields_container,
            placeholder_text="Enter your full name",
            height=40,
            font=("Helvetica", 13),
            border_width=1,
            border_color="#d1d5db",
            fg_color="white",
            text_color="#111827"
        )
        self.name_entry.pack(fill="x", pady=(0, 20))

        # Contact info field
        contact_label = ctk.CTkLabel(
            fields_container,
            text="Contact Information *",
            font=("Helvetica", 13, "bold"),
            text_color="#374151",
            anchor="w"
        )
        contact_label.pack(fill="x", pady=(0, 8))

        self.contact_entry = ctk.CTkEntry(
            fields_container,
            placeholder_text="Email or phone number",
            height=40,
            font=("Helvetica", 13),
            border_width=1,
            border_color="#d1d5db",
            fg_color="white",
            text_color="#111827"
        )
        self.contact_entry.pack(fill="x", pady=(0, 20))

        # Query field
        query_label = ctk.CTkLabel(
            fields_container,
            text="Your Query *",
            font=("Helvetica", 13, "bold"),
            text_color="#374151",
            anchor="w"
        )
        query_label.pack(fill="x", pady=(0, 8))

        self.query_textbox = ctk.CTkTextbox(
            fields_container,
            height=120,
            font=("Helvetica", 13),
            border_width=1,
            border_color="#d1d5db",
            fg_color="white",
            text_color="#111827"
        )
        self.query_textbox.pack(fill="x", pady=(0, 25))

        # Submit button
        submit_btn = ctk.CTkButton(
            fields_container,
            text="Submit Query",
            height=45,
            font=("Helvetica", 14, "bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            text_color="white",
            corner_radius=8,
            command=self._submit_query
        )
        submit_btn.pack(pady=(0, 10))

    def _submit_query(self):
        """Handle form submission."""
        name = self.name_entry.get().strip()
        contact = self.contact_entry.get().strip()
        query = self.query_textbox.get("1.0", "end-1c").strip()

        # Validation
        if not name:
            messagebox.showwarning("Missing Information", "Please enter your name.")
            return

        if not contact:
            messagebox.showwarning("Missing Information", "Please enter your contact information.")
            return

        if not query:
            messagebox.showwarning("Missing Information", "Please enter your query.")
            return

        # Basic email validation
        if "@" in contact or len(contact) >= 10:
            pass  # Looks like valid contact info
        else:
            response = messagebox.askyesno(
                "Confirm Contact Info",
                "The contact information seems incomplete. Do you want to submit anyway?"
            )
            if not response:
                return

        # Submit query to Firebase Realtime Database
        try:
            if not FIREBASE_AVAILABLE:
                # Fallback to local file storage if Firebase is not available
                base = Path(__file__).resolve().parent.parent
                queries_dir = base / "data" / "queries"
                queries_dir.mkdir(parents=True, exist_ok=True)
                import json

                query_data = {
                    "name": name,
                    "contact": contact,
                    "query": query,
                    "timestamp": datetime.datetime.now().isoformat()
                }

                query_file = queries_dir / f"query_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(query_file, "w") as f:
                    json.dump(query_data, f, indent=2)

                messagebox.showinfo(
                    "Query Submitted (Local)",
                    f"Thank you, {name}!\n\nYour query has been saved locally. "
                    "Firebase connection is not available."
                )
            else:
                # Prepare query data
                query_data = {
                    "name": name,
                    "contact": contact,
                    "query": query,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "status": "new"  # Track query status
                }

                # Push to Firebase Realtime Database under 'queries' node
                result = database.push("queries", query_data)

                if result:
                    # Show success message
                    messagebox.showinfo(
                        "Query Submitted",
                        f"Thank you, {name}!\n\nYour query has been submitted successfully to our database. "
                        f"We'll get back to you at {contact} as soon as possible."
                    )
                else:
                    # Fallback to local storage if Firebase push failed
                    base = Path(__file__).resolve().parent.parent
                    queries_dir = base / "data" / "queries"
                    queries_dir.mkdir(parents=True, exist_ok=True)
                    import json

                    query_file = queries_dir / f"query_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    with open(query_file, "w") as f:
                        json.dump(query_data, f, indent=2)

                    messagebox.showwarning(
                        "Query Saved Locally",
                        f"Thank you, {name}!\n\nYour query has been saved locally. "
                        f"Firebase connection failed, but your query is stored."
                    )

            # Clear form
            self.name_entry.delete(0, "end")
            self.contact_entry.delete(0, "end")
            self.query_textbox.delete("1.0", "end")

        except Exception as e:
            error_msg = str(e)
            # Provide more specific error messages
            if "database" in error_msg.lower() or "permission" in error_msg.lower():
                messagebox.showerror(
                    "Database Error",
                    f"Failed to connect to database. Please check your Firebase configuration.\n\nError: {error_msg}"
                )
            else:
                messagebox.showerror(
                    "Error",
                    f"Failed to submit query: {error_msg}\n\nPlease try again or contact support directly."
                )


if __name__ == "__main__":
    root = ctk.CTk()
    root.title("SmartCompliance - FAQs")
    root.geometry("900x800")
    faq_page = FAQPage(root)
    root.mainloop()
