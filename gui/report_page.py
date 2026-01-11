import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from pathlib import Path
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import seaborn as sns
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer
from collections import Counter

class ReportPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill="both", expand=True)
        self.configure(fg_color="#f9fafb")
        # rows for export (Index, Policy Clause, SCF Mapped Clauses)
        self.export_rows = []
        self._build_ui()

    def _build_ui(self):
        title = ctk.CTkLabel(self, text="Compliance Report Dashboard", font=("Helvetica", 22, "bold"), text_color="#1e3a8a")
        title.pack(pady=(30, 10))
        # Make the main report area scrollable
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="white", corner_radius=12)
        self.scroll_frame.pack(fill="both", expand=True, padx=30, pady=10)
        self.summary_frame = ctk.CTkFrame(self.scroll_frame, fg_color="white", corner_radius=12)
        self.summary_frame.pack(fill="x", padx=10, pady=10)
        self.charts_frame = ctk.CTkFrame(self.scroll_frame, fg_color="white", corner_radius=12)
        self.charts_frame.pack(fill="x", padx=10, pady=10)
        self.table_frame = ctk.CTkFrame(self.scroll_frame, fg_color="white", corner_radius=12)
        self.table_frame.pack(fill="both", expand=True, padx=10, pady=10)
        # Export buttons row
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=20)
        self.download_btn = ctk.CTkButton(btn_row, text="Download PDF", fg_color="#1648b3", hover_color="#102e80", font=("Helvetica", 13, "bold"), command=self.download_pdf)
        self.download_btn.pack(side="left", padx=(0,10))
        self.csv_btn = ctk.CTkButton(btn_row, text="Download CSV", fg_color="#059669", hover_color="#047857", font=("Helvetica", 13, "bold"), command=self.download_csv)
        self.csv_btn.pack(side="left")
        self.load_data_and_render()

    def load_data_and_render(self):
        base = Path(__file__).resolve().parent.parent
        try:
            mappings = pd.read_parquet(base / "data" / "processed" / "explainable_mappings.parquet")
            scf_controls = pd.read_parquet(base / "data" / "processed" / "scf_controls.parquet")
            # Load the most recently uploaded/extracted policy sentences parquet
            policy_dir = base / "data" / "company_policies" / "processed"
            candidates = list(policy_dir.glob("*.parquet"))
            if not candidates:
                raise FileNotFoundError(f"No parquet files found in {policy_dir}")
            latest_policy = max(candidates, key=lambda p: p.stat().st_mtime)
            self.last_policy_file = latest_policy
            policy = pd.read_parquet(latest_policy)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load report data: {e}")
            return
        # Summary
        total_clauses = len(policy)
        high_conf = 0
        med_conf = 0
        low_conf = 0
        top_scf = []
        mapped_clauses = 0
        parse_errors = 0
        # reset export rows
        self.export_rows = []
        for idx, row in mappings.iterrows():
            expls = row['mapping_explanations']
            # Robust parsing for mapping_explanations
            if expls is None:
                expls = []
            elif isinstance(expls, (list, dict, str)):
                pass
            elif hasattr(expls, 'tolist'):
                expls = expls.tolist()
            elif hasattr(expls, 'values'):
                expls = list(expls.values)
            if isinstance(expls, str):
                import json
                try:
                    parsed = json.loads(expls)
                    if isinstance(parsed, dict):
                        expls = [parsed]
                    elif isinstance(parsed, list):
                        expls = parsed
                    else:
                        expls = []
                except Exception:
                    expls = []
                    parse_errors += 1
            elif isinstance(expls, dict):
                expls = [expls]
            elif not isinstance(expls, list):
                expls = []
            if isinstance(expls, list) and len(expls) > 0:
                mapped_clauses += 1
                top = expls[0]
                # collect all mapped scf ids with semantic scores for export view
                mapped_with_scores = []
                for m in expls:
                    if isinstance(m, dict):
                        sid = m.get('matched_scf_id', '') or m.get('scf_id', '')
                        if not sid:
                            continue
                        score_val = self.extract_score(m.get('explanation', ''))
                        label = f"{sid} ({score_val})" if score_val else str(sid)
                        mapped_with_scores.append(label)
                mapped_str = ", ".join(mapped_with_scores) if mapped_with_scores else "No mappings found"
                self.export_rows.append({
                    'Index': row.get('clause_index', idx),
                    'Policy Clause': str(row.get('clause_text', '')),
                    'SCF Mapped Clauses (Score)': mapped_str,
                })
                top_scf.append({
                    'clause_index': row.get('clause_index', idx),
                    'clause_text': row.get('clause_text', ''),
                    'scf_id': top.get('matched_scf_id', ''),
                    'domain': top.get('matched_domain', ''),
                    'confidence': top.get('confidence_comment', ''),
                    'score': self.extract_score(top.get('explanation', '')),
                    'explanation': top.get('explanation', '')
                })
                conf = top.get('confidence_comment', '').lower()
                if 'high' in conf:
                    high_conf += 1
                elif 'medium' in conf:
                    med_conf += 1
                else:
                    low_conf += 1
        if mapped_clauses == 0:
            messagebox.showerror("No Valid Mappings", "No valid clause mappings found. Please check your data files.")
        if parse_errors > 0:
            print(f"Warning: {parse_errors} mapping_explanations failed to parse.")
        # Persist KPIs for exports
        self.total_clauses = total_clauses
        self.mapped_clauses = mapped_clauses
        self.high_conf = high_conf
        self.med_conf = med_conf
        self.low_conf = low_conf
        # Summary UI
        for widget in self.summary_frame.winfo_children():
            widget.destroy()
        # Highest occurring SCF
        scf_ids = [row['scf_id'] for row in top_scf if row['scf_id']]
        scf_counter = Counter(scf_ids)
        most_common_scf = scf_counter.most_common(1)[0][0] if scf_counter else 'N/A'
        self.most_common_scf = most_common_scf
        ctk.CTkLabel(self.summary_frame, text=f"Total Clauses: {total_clauses}", font=("Helvetica", 13, "bold"), text_color="#1648b3").pack(side="left", padx=18)
        ctk.CTkLabel(self.summary_frame, text=f"Mapped Clauses: {mapped_clauses}", font=("Helvetica", 13, "bold"), text_color="#059669").pack(side="left", padx=18)
        ctk.CTkLabel(self.summary_frame, text=f"High Confidence: {high_conf}", font=("Helvetica", 13), text_color="#059669").pack(side="left", padx=18)
        ctk.CTkLabel(self.summary_frame, text=f"Medium Confidence: {med_conf}", font=("Helvetica", 13), text_color="#facc15").pack(side="left", padx=18)
        ctk.CTkLabel(self.summary_frame, text=f"Low Confidence: {low_conf}", font=("Helvetica", 13), text_color="#dc2626").pack(side="left", padx=18)
        ctk.CTkLabel(self.summary_frame, text=f"Most Frequent SCF: {most_common_scf}", font=("Helvetica", 13, "bold"), text_color="#1e3a8a").pack(side="left", padx=12)
        # Charts
        for widget in self.charts_frame.winfo_children():
            widget.destroy()
        self.render_charts(top_scf, parent=self.charts_frame)
        self.render_bar_chart(top_scf, parent=self.charts_frame)
        self.render_table(top_scf)

    def extract_score(self, explanation):
        import re
        match = re.search(r"semantic similarity score (?:is|of) ([0-9.]+)", explanation)
        return match.group(1) if match else ""

    def render_charts(self, top_scf, parent=None):
        parent = parent or self.charts_frame
        conf_counts = {'High':0, 'Medium':0, 'Low':0}
        for row in top_scf:
            conf = row['confidence'].lower()
            if 'high' in conf:
                conf_counts['High'] += 1
            elif 'medium' in conf:
                conf_counts['Medium'] += 1
            else:
                conf_counts['Low'] += 1
        fig1, ax1 = plt.subplots(figsize=(3.5,3.5))
        if sum(conf_counts.values()) > 0:
            ax1.pie([conf_counts['High'], conf_counts['Medium'], conf_counts['Low']], labels=['High','Medium','Low'], colors=["#059669", "#facc15", "#dc2626"], autopct='%1.1f%%', startangle=90)
            ax1.set_title("Confidence Distribution")
        else:
            ax1.text(0.5, 0.5, "No data available", ha="center", va="center", fontsize=14)
            ax1.set_title("Confidence Distribution")
        canvas1 = FigureCanvasTkAgg(fig1, master=parent)
        canvas1.get_tk_widget().pack(side="left", padx=18, pady=10)

    def render_bar_chart(self, top_scf, parent=None):
        parent = parent or self.charts_frame
        import collections
        domain_counts = collections.Counter([row['domain'] for row in top_scf])
        # Sort domains by count descending and take top 10
        sorted_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        domains = [d[0][:18] + '...' if len(d[0]) > 20 else d[0] for d in sorted_domains]
        counts = [d[1] for d in sorted_domains]
        fig2, ax2 = plt.subplots(figsize=(max(6, len(domains)*0.7), 3.5))
        if len(domains) > 0:
            bars = ax2.bar(domains, counts, color="#1648b3", width=0.6)
            ax2.set_title("Top 10 SCF Domains by Coverage", fontsize=11)
            ax2.set_ylabel("# Clauses", fontsize=9)
            ax2.grid(axis='y', linestyle='--', alpha=0.5)
            ax2.tick_params(axis='x', rotation=35, labelsize=8)
            ax2.tick_params(axis='y', labelsize=8)
            ax2.margins(x=0.01)
        else:
            ax2.text(0.5, 0.5, "No data available", ha="center", va="center", fontsize=14)
            ax2.set_title("SCF Domain Coverage", fontsize=11)
        fig2.tight_layout()
        canvas2 = FigureCanvasTkAgg(fig2, master=parent)
        canvas2.get_tk_widget().pack(side="left", padx=18, pady=10)

    def render_table(self, top_scf):
        for widget in self.table_frame.winfo_children():
            widget.destroy()
        cols = ["Clause Index", "Clause Text", "SCF ID", "Domain", "Confidence", "Score", "Explanation"]
        style = ttk.Style()
        style.configure("Custom.Treeview", borderwidth=1, relief="solid", rowheight=22)
        style.map("Custom.Treeview", background=[('selected', '#e5e7eb')])
        style.configure("Custom.Treeview.Heading", font=("Helvetica", 10, "bold"), borderwidth=1, relief="solid")
        style.layout("Custom.Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])
        tree = ttk.Treeview(self.table_frame, columns=cols, show="headings", height=12, style="Custom.Treeview")
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, anchor="w", width=120 if col!="Explanation" else 320)
        tree.pack(fill="both", expand=True, padx=12, pady=12)
        tree.tag_configure('oddrow', background='white')
        tree.tag_configure('evenrow', background='#f3f4f6')
        for i, row in enumerate(top_scf):
            exp = row['explanation']
            exp_clean = self._extract_scf_text(exp)
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            tree.insert("", "end", values=(row['clause_index'], row['clause_text'], row['scf_id'], row['domain'], row['confidence'], row['score'], exp_clean), tags=(tag,))

    def download_pdf(self):
        import datetime
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from pathlib import Path
        from tkinter import messagebox, filedialog

        # Ask user where to save to avoid permission errors
        save_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile="compliance_report.pdf",
            title="Save PDF Report"
        )
        if not save_path:
            return

        doc = SimpleDocTemplate(
            str(save_path), pagesize=letter,
            leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36
        )
        styles = getSampleStyleSheet()
        # Safer paragraph style with aggressive word wrap
        wrap_style = ParagraphStyle('wrap', parent=styles['Normal'], fontSize=9, leading=11, wordWrap='CJK')
        title_style = ParagraphStyle('title', parent=styles['Title'])
        elements = []

        # Title
        title = Paragraph("<b><font color='#1648b3' size=16>SmartCompliance — Mapping Report</font></b>", title_style)
        elements.append(title)
        elements.append(Spacer(1, 4))
        gen_time = Paragraph(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal'])
        elements.append(gen_time)
        elements.append(Spacer(1, 8))

        # KPIs
        kpi_lines = [
            f"Total Clauses: {getattr(self, 'total_clauses', 'N/A')}",
            f"Mapped Clauses: {getattr(self, 'mapped_clauses', 'N/A')}",
            f"High: {getattr(self, 'high_conf', 'N/A')}",
            f"Medium: {getattr(self, 'med_conf', 'N/A')}",
            f"Low: {getattr(self, 'low_conf', 'N/A')}",
            f"Most Frequent SCF: {getattr(self, 'most_common_scf', 'N/A')}",
        ]
        for line in kpi_lines:
            elements.append(Paragraph(line, styles['Normal']))
        elements.append(Spacer(1, 12))

        # Table data with truncation to prevent over-tall rows
        def truncate(text: str, max_chars: int = 700) -> str:
            t = str(text or "")
            if len(t) > max_chars:
                return t[:max_chars - 1] + "…"
            return t

        data = [["Index", "Policy Clause", "SCF Mapped Clauses (Score)"]]
        if not self.export_rows:
            data.append(["-", Paragraph("No data available. Generate the report first.", wrap_style), "-"])
        else:
            for r in self.export_rows:
                idx = str(r.get('Index', ''))
                clause = Paragraph(truncate(r.get('Policy Clause', '')), wrap_style)
                # Color-code mapped items by score
                mapped_raw = str(r.get('SCF Mapped Clauses (Score)', ''))
                def score_to_color(s: float) -> str:
                    try:
                        s = float(s)
                    except Exception:
                        return '#111827'
                    if s >= 0.65:
                        return '#059669'  # green
                    if s >= 0.55:
                        return '#f97316'  # orange
                    return '#c33e88'      # red
                # Build HTML tokens safely; do not truncate inside tags
                import re as _re
                from xml.sax.saxutils import escape as _escape
                tokens = []
                for token in [t.strip() for t in mapped_raw.split(',') if t.strip()]:
                    m = _re.search(r"^(.*?)\s*\(([-+]?[0-9]*\.?[0-9]+)\)$", token)
                    if m:
                        sid = _escape(m.group(1).strip())
                        sc = m.group(2)
                        color = score_to_color(sc)
                        tokens.append(f"<font color='{color}'>{sid} ({_escape(sc)})</font>")
                    else:
                        tokens.append(_escape(token))
                # Safe concatenate within a max length budget to avoid huge paragraphs
                max_len = 3000
                acc = []
                total = 0
                for i, t in enumerate(tokens):
                    sep = '' if i == 0 else ', '
                    add_len = len(sep) + len(t)
                    if total + add_len > max_len:
                        remaining = len(tokens) - i
                        if remaining > 0:
                            acc.append(f" (+{remaining} more)")
                        break
                    acc.append(sep + t)
                    total += add_len
                mapped_html = ''.join(acc) if acc else _escape(mapped_raw)
                mapped = Paragraph(mapped_html, wrap_style)
                data.append([idx, clause, mapped])

        table = Table(data, colWidths=[45, 255, 255], repeatRows=1, splitByRow=1)
        table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e5e7eb')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#111827')),
            ('ALIGN', (0,0), (0,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f9fafb')]),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d1d5db')),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        elements.append(table)

        doc.build(elements)
        messagebox.showinfo("Report Saved", f"PDF saved successfully at:\n{save_path}")

    def download_csv(self):
        import pandas as pd
        from tkinter import messagebox, filedialog

        if not self.export_rows:
            messagebox.showwarning("No Data", "No data to export. Generate the report first.")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="compliance_report.csv",
            title="Save CSV Report"
        )
        if not save_path:
            return

        df = pd.DataFrame(self.export_rows, columns=["Index", "Policy Clause", "SCF Mapped Clauses (Score)"])
        try:
            df.to_csv(save_path, index=False, encoding="utf-8")
        except PermissionError:
            messagebox.showerror("Permission Denied", "Close the CSV if it's open and try again, or choose another location.")
            return
        messagebox.showinfo("CSV Saved", f"CSV saved successfully at:\n{save_path}")

    def _extract_scf_text(self, explanation: str) -> str:
        """Extract the SCF control quoted text robustly, handling apostrophes.
        Strategy:
        1) Find the phrase 'SCF control text that says' (case-insensitive), then
           capture everything between the next opening quote and its matching closer
           (supports straight/smart quotes). Uses the last matching closer to allow
           apostrophes inside the text.
        2) If not found, prefer a double-quoted segment, then smart-double quotes,
           then finally a greedy single-quote capture from first to last single quote.
        """
        if not explanation:
            return ""
        import re

        text = str(explanation)
        phrase = re.search(r"scf\s+control\s+text\s+that\s+says", text, flags=re.IGNORECASE)
        if phrase:
            start = phrase.end()
            # Find first opening quote after phrase
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
                # Use the last closer to allow apostrophes or nested punctuation inside
                closer_idx = text.rfind(closer_char)
                if closer_idx > opener_idx + 1:
                    return text[opener_idx + 1: closer_idx].strip()

        # Fallbacks: prefer double quotes first
        m = re.search(r'"([^\"]+)"', text)
        if m:
            return m.group(1).strip()
        m = re.search(r'“([^”]+)”', text)
        if m:
            return m.group(1).strip()
        # Greedy single-quote capture: from first to last single quote
        first = text.find("'")
        last = text.rfind("'")
        if first != -1 and last > first:
            return text[first + 1:last].strip()
        return text
