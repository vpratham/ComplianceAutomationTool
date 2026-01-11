import tkinter as tk
from gui.dashboard import DashboardWindow


def main():
    """Main entry point for the SmartCompliance GUI.

    The login window has been disabled to avoid Firebase/pyrebase
    dependencies that are not required for core functionality.
    The app now launches directly into the main dashboard.
    """
    root = tk.Tk()
    root.title("SmartCompliance")

    # Try to start maximized; fallback to a sensible size
    try:
        root.state("zoomed")  # Windows
    except Exception:
        root.geometry("1200x800")  # fallback

    # Prevent default OS styling flicker
    root.configure(bg="#f5f7fb")

    # Launch directly into the dashboard
    DashboardWindow(root)

    root.mainloop()


if __name__ == "__main__":
    main()
