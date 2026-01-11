# # gui/dashboard.py

#=============================================================================================================
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
import customtkinter as ctk
from pathlib import Path
import threading
from gui.upload_page import UploadPage
from gui.mapping_view import MappingPage
from gui.report_page import ReportPage
from gui.faq_page import FAQPage
from gui.evidence_upload_page import EvidenceUploadPage
from gui.evidence_view_page import EvidenceViewPage


# Import your preprocessing backend
try:
    from backend.policy_preprocessor import preprocess_policy
except ImportError:
    preprocess_policy = None  # fallback for testing


def slide_frames(parent, old_frame, new_frame, direction="left", steps=20, delay=10):
    """Smooth slide animation between frames."""
    if old_frame is None or new_frame is None:
        return

    w = parent.winfo_width() or parent.winfo_reqwidth()
    step = w // steps
    dx = -step if direction == "left" else step

    new_frame.lift()
    new_frame.place(x=w if direction == "left" else -w, y=0, relwidth=1, relheight=1)

    for i in range(steps):
        parent.update_idletasks()
        parent.after(delay)
        old_x = dx * i
        new_x = (w + dx * i) if direction == "left" else (-w + dx * i)
        old_frame.place(x=old_x, y=0, relwidth=1, relheight=1)
        new_frame.place(x=new_x, y=0, relwidth=1, relheight=1)

    old_frame.lower()
    new_frame.place(x=0, y=0, relwidth=1, relheight=1)


# 
# ---------------------------------------------------------
# Dashboard Window
# ---------------------------------------------------------
class DashboardWindow(ctk.CTkFrame):
    def __init__(self, root, username="demo"):
        super().__init__(root)
        self.root = root
        self.pack(fill="both", expand=True)
        self.configure(fg_color="#f3f4f6")

        self.username = username
        self.current_page = None

        self._build_ui()

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ---------- Sidebar ----------
        self.sidebar_width = 260
        sidebar_frame = ctk.CTkFrame(self, width=self.sidebar_width, fg_color="transparent")
        sidebar_frame.grid(row=0, column=0, sticky="ns")
        sidebar_frame.grid_propagate(False)

        self.sidebar_canvas = tk.Canvas(sidebar_frame, width=self.sidebar_width, highlightthickness=0, bd=0)
        self.sidebar_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.gradient_img_id = self.sidebar_canvas.create_image(0, 0, anchor="nw")
        self._sidebar_img = None

        welcome = ctk.CTkLabel(
            sidebar_frame,
            text=f"Welcome,\n{self.username}",
            font=("Helvetica", 20, "bold"),
            text_color="white",
            anchor="w",
            justify="left",
            fg_color="#1c4589"
        )
        welcome.pack(padx=20, pady=(40, 10), anchor="w")

        ttk.Separator(sidebar_frame, orient="horizontal").pack(fill="x", padx=15, pady=10)

        def make_nav_button(text, command):
            btn = ctk.CTkButton(
                sidebar_frame,
                text=text,
                width=200,
                height=42,
                corner_radius=0,
                fg_color="white",
                hover_color="#c6c6c6",
                text_color="#1e3a8a",
                font=("Helvetica", 13, "bold"),
                command=command,
            )
            btn.pack(pady=10, padx=30)
            return btn

        make_nav_button("Upload", self.show_upload)
        make_nav_button("Mapping", self.show_mapping)
        
        make_nav_button("Report", self.show_report)
        make_nav_button("Evidence Upload", self.show_evidence_upload)
        make_nav_button("Evidence View", self.show_evidence_view)
        make_nav_button("FAQs", self.show_faq)

        # ----------------- Logout button placed at the bottom with custom color -----------------
        logout_btn = ctk.CTkButton(
            sidebar_frame,
            text="Logout",
            width=100,
            height=42,
            corner_radius=0,
            fg_color="#f87171",          # red background for logout
            hover_color="#f04242",       # lighter red on hover
            text_color="white",
            font=("Helvetica", 13, "bold"),
            command=self._logout,
        )
        # Pack at the bottom of the sidebar with padding
        logout_btn.pack(side="bottom", pady=24, padx=30)
        # ---------------------------------------------------------------------------------------

        self.sidebar_canvas.bind("<Configure>", self._draw_gradient)

        # ---------- Main Content ----------
        self.content_holder = ctk.CTkFrame(self, fg_color="#f9fafb")
        self.content_holder.grid(row=0, column=1, sticky="nsew")

        # Progress bar (shared across pages)
        self.progress = ttk.Progressbar(self.content_holder, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", padx=20, pady=10)
        self.progress["value"] = 0

        # Pages
        self.blank_page = self._make_blank_page(self.content_holder)
        self.upload_page = UploadPage(self.content_holder)
        self.mapping_page = MappingPage(self.content_holder)
        self.faq_page = FAQPage(self.content_holder)
        self.evidence_upload_page = EvidenceUploadPage(self.content_holder)
        self.evidence_view_page = None  # Lazy load
        self.report_page = None  # <-- Ensure not created here

        for p in (self.blank_page, self.upload_page, self.mapping_page, self.faq_page, self.evidence_upload_page):
            p.place(in_=self.content_holder, x=0, y=0, relwidth=1, relheight=1)
            p.lower()

        self.current_page = self.blank_page
        self.current_page.lift()

    def _draw_gradient(self, event):
        W = self.sidebar_width
        H = event.height
        if H <= 1 or W <= 1:
            return
        gradient = Image.new("RGB", (W, H))
        draw = ImageDraw.Draw(gradient)
        top_rgb, bottom_rgb = (30, 58, 138), (16, 185, 129)
        for y in range(H):
            t = y / (H - 1) if H > 1 else 0
            r = int(top_rgb[0] * (1 - t) + bottom_rgb[0] * t)
            g = int(top_rgb[1] * (1 - t) + bottom_rgb[1] * t)
            b = int(top_rgb[2] * (1 - t) + bottom_rgb[2] * t)
            draw.line([(0, y), (W, y)], fill=(r, g, b))
        self._sidebar_img = ImageTk.PhotoImage(gradient)
        self.sidebar_canvas.itemconfig(self.gradient_img_id, image=self._sidebar_img)

    def _make_page(self, parent, title, color):
        frame = ctk.CTkFrame(parent, fg_color=color)
        lbl = ctk.CTkLabel(frame, text=title, font=("Helvetica", 20, "bold"), text_color="#111827")
        lbl.pack(pady=40)
        return frame

    def _make_blank_page(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="#f9fafb")
        lbl = ctk.CTkLabel(
            frame,
            text="Welcome to SmartCompliance Dashboard",
            font=("Helvetica", 20, "bold"),
            text_color="#4b5563",
        )
        lbl.place(relx=0.5, rely=0.5, anchor="center")
        return frame

    def show_upload(self):
        self._switch_page(self.upload_page)

    def show_mapping(self):
        self._switch_page(self.mapping_page)

    def show_faq(self):
        self._switch_page(self.faq_page)

    def show_report(self):
        if self.report_page is None:
            self.report_page = ReportPage(self.content_holder)
            self.report_page.place(in_=self.content_holder, x=0, y=0, relwidth=1, relheight=1)
            self.report_page.lower()
        self.report_page.load_data_and_render()
        self._switch_page(self.report_page)

    def show_evidence_upload(self):
        self._switch_page(self.evidence_upload_page)

    def show_evidence_view(self):
        if self.evidence_view_page is None:
            self.evidence_view_page = EvidenceViewPage(self.content_holder)
            self.evidence_view_page.place(in_=self.content_holder, x=0, y=0, relwidth=1, relheight=1)
            self.evidence_view_page.lower()
        self.evidence_view_page.load_evidence_data()
        self._switch_page(self.evidence_view_page)

    def _switch_page(self, new_page):
        if new_page == self.current_page:
            return
        slide_frames(self.content_holder, self.current_page, new_page, direction="left")
        self.current_page = new_page

    # ----------------- Updated logout handler -----------------
    def _logout(self):
        """Logout current user and return to the project's login window."""
        try:
            # remove dashboard UI
            self.pack_forget()
            self.destroy()
        finally:
            # Prefer the project's login window if available
            try:
                # Expecting a LoginWindow class in gui/login_window.py that accepts the root
                from gui.login_window import LoginWindow
                # instantiate the project's login window
                LoginWindow(self.root)
            except Exception:
                # Fallback: use the simple in-file LoginFrame if the project's login window isn't present
                LoginFrame(self.root)
    # ---------------------------------------------------------


# ------------------ Added: simple LoginFrame to return to on logout ------------------
class LoginFrame(ctk.CTkFrame):
    """Minimal login UI used when user logs out (replaces Dashboard)."""
    def __init__(self, root):
        super().__init__(root)
        self.root = root
        self.pack(fill="both", expand=True)
        self.configure(fg_color="#f9fafb")

        lbl = ctk.CTkLabel(self, text="SmartCompliance - Login", font=("Helvetica", 20, "bold"))
        lbl.pack(pady=(80, 20))

        self.username_var = tk.StringVar(value="demo")
        entry = ctk.CTkEntry(self, textvariable=self.username_var, width=300)
        entry.pack(pady=(10, 10))

        btn = ctk.CTkButton(self, text="Login", width=200, command=self._on_login)
        btn.pack(pady=(10, 10))

    def _on_login(self):
        username = self.username_var.get().strip() or "demo"
        # Destroy login frame and create dashboard
        self.pack_forget()
        self.destroy()
        DashboardWindow(self.root, username=username)
# -----------------------------------------------------------------------------------

if __name__ == "__main__":

    root = ctk.CTk()
    root.title("SmartCompliance Dashboard")
    root.geometry("1200x800")
    DashboardWindow(root, username="cg@capstone.test")
    root.mainloop()
