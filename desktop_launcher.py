import os
import sys
import threading
import time
import webbrowser

# Ensure working directory is the executable directory
if getattr(sys, "frozen", False):
    app_dir = os.path.dirname(sys.executable)
    os.chdir(app_dir)
else:
    app_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(app_dir)

import app
import db

def open_browser():
    time.sleep(1.2)
    webbrowser.open("http://127.0.0.1:5000")

def main():
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 60)
    print("      CYBER TALENT CLUB SMA - Windows Standalone App")
    print("=" * 60)
    print("[*] Initializing database...")
    db.init_db()
    
    print("[*] Starting web server on http://127.0.0.1:5000")
    print("[*] Opening your web browser automatically...")
    threading.Thread(target=open_browser, daemon=True).start()
    
    print("[*] Running! Keep this window open while using the app.")
    print("[*] Press Ctrl+C in this window to stop.")
    print("=" * 60)
    
    app.app.run(host="127.0.0.1", port=5000, debug=False)

if __name__ == "__main__":
    main()
