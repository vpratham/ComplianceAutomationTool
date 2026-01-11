# gui/login_window.py
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageDraw
import customtkinter as ctk
import pyrebase

from gui.dashboard import DashboardWindow

# ------------------- FIREBASE CONFIG (from your web app) -------------------
firebaseConfig = {
    "apiKey": "AIzaSyBm82zxebOaSAVNZoC94oOQ8hzz58cGy8I",
    "authDomain": "smartcompliance-5dbb9.firebaseapp.com",
    "databaseURL": "",  # optional (only needed if you use Realtime DB)
    "projectId": "smartcompliance-5dbb9",
    "storageBucket": "smartcompliance-5dbb9.firebasestorage.app",
    "messagingSenderId": "1040761393077",
    "appId": "1:1040761393077:web:bd7d28e30a6d6ed62f93fc",
    "measurementId": "G-S1F4TKDQPJ"
}

# Initialize Firebase
firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()

# ------------------- APP THEME SETUP -------------------
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")


class LoginWindow(ctk.CTkFrame):
    """SmartCompliance login screen with Firebase Authentication"""
    def __init__(self, root):
        super().__init__(root)
        self.root = root
        self.pack(fill="both", expand=True)
        self.configure(fg_color="#f3f4f6")
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ---------- LEFT: Gradient panel ----------
        left_canvas = tk.Canvas(self, highlightthickness=0, bd=0)
        left_canvas.grid(row=0, column=0, sticky="nsew")

        W, H = 640, 780
        gradient = Image.new("RGB", (W, H), "#00b4d8")
        draw = ImageDraw.Draw(gradient)
        top_rgb = (37, 99, 235)
        bottom_rgb = (16, 185, 129)
        for y in range(H):
            t = y / (H - 1)
            r = int(top_rgb[0] * (1 - t) + bottom_rgb[0] * t)
            g = int(top_rgb[1] * (1 - t) + bottom_rgb[1] * t)
            b = int(top_rgb[2] * (1 - t) + bottom_rgb[2] * t)
            draw.line([(0, y), (W, y)], fill=(r, g, b))
        self._left_img = ImageTk.PhotoImage(gradient)
        left_canvas.create_image(0, 0, anchor="nw", image=self._left_img)
        left_canvas.create_text(
            64, 80, anchor="nw", text="SmartCompliance",
            font=("Helvetica", 32, "bold"), fill="white"
        )
        left_canvas.create_text(
            64, 160, anchor="nw",
            text="Automate. Map. Prove.\nCompliance done right.",
            font=("Helvetica", 14), fill="#e7fbf8", width=420, justify="left"
        )
        bullets = [
            "✔ Secure compliance mapping",
            "✔ Fast document processing",
            "✔ Explainable RAG insights"
        ]
        start_y = H - 180
        for b in bullets:
            left_canvas.create_text(
                64, start_y, anchor="nw",
                text=b, font=("Helvetica", 12), fill="#dff8f6"
            )
            start_y += 28

        # ---------- RIGHT: login card ----------
        right_container = ctk.CTkFrame(self, fg_color="transparent")
        right_container.grid(row=0, column=1, sticky="nsew", padx=56, pady=56)

        card = ctk.CTkFrame(
            right_container,
            width=520, height=520,
            corner_radius=16,
            fg_color=("white", "#ffffff80")
        )
        card.place(relx=0.5, rely=0.5, anchor="center")

        inner = tk.Frame(card, bg="white")
        inner.pack(fill="both", expand=True, padx=40, pady=40)

        tk.Label(inner, text="Login", font=("Helvetica", 22, "bold"),
                 bg="white", fg="#111827").pack(pady=(4, 6))
        tk.Label(inner, text="Welcome back! Log in to your account:",
                 font=("Helvetica", 11), bg="white", fg="#4b5563").pack(pady=(6, 30))

        # helper for entry fields
        def make_input(parent, placeholder, show=None):
            entry = ctk.CTkEntry(
                parent,
                placeholder_text=placeholder,
                width=380,
                height=48,
                corner_radius=6,
                border_width=1,
                border_color="#eceff1",
                fg_color="#ffffff",
                text_color="#111827",
                show=show
            )
            entry.pack(pady=10)
            return entry

        self.email_entry = make_input(inner, "Email")
        self.password_entry = make_input(inner, "Password", show="*")

        login_btn = ctk.CTkButton(
            inner,
            text="Log in",
            corner_radius=24,
            width=160,
            height=48,
            fg_color="#2563EB",
            hover_color="#1E40AF",
            text_color="white",
            font=("Helvetica", 13, "bold"),
            command=self._on_login_button
        )
        login_btn.pack(pady=(30, 10))

    # ---------- Login Button Action ----------
    def _on_login_button(self):
        email = self.email_entry.get().strip()
        password = self.password_entry.get().strip()

        if not email or not password:
            messagebox.showwarning("Missing Info", "Please enter both email and password.")
            return

        try:
            user = auth.sign_in_with_email_and_password(email, password)
            messagebox.showinfo("Login Successful", f"Welcome {email}!")
            self.destroy()
            DashboardWindow(self.root, username=email)
        except Exception as e:
            error_msg = str(e)
            if "INVALID_PASSWORD" in error_msg:
                messagebox.showerror("Login Failed", "Invalid password. Try again.")
            elif "EMAIL_NOT_FOUND" in error_msg:
                messagebox.showerror("Login Failed", "No account found with this email.")
            elif "INVALID_EMAIL" in error_msg:
                messagebox.showerror("Login Failed", "Invalid email format.")
            else:
                messagebox.showerror("Login Failed", f"Error: {error_msg}")


if __name__ == "__main__":
    root = ctk.CTk()
    root.geometry("1280x800")
    LoginWindow(root)
    root.mainloop()
