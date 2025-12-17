#!/usr/bin/env python3
"""
Launcher for YouTube Automation Web Terminal
Auto-starts server and opens browser
"""

import sys
import os
import time
import webbrowser
import subprocess
from pathlib import Path

def main():
    print("=" * 70)
    print("   🎬 YouTube Automation Web Terminal Launcher")
    print("=" * 70)
    print()
    
    # Get the directory of this script
    script_dir = Path(__file__).parent
    
    # Check for virtual environment and use its Python
    venv_python = script_dir / ".venv" / "bin" / "python"
    if venv_python.exists():
        python_executable = str(venv_python)
        print(f"📦 Using virtual environment: .venv")
    else:
        python_executable = sys.executable
        print(f"⚠️  No .venv found, using: {python_executable}")
    print()
    
    # Start the web terminal server
    print("🚀 Starting web terminal server...")
    print("   URL: http://localhost:8000")
    print()
    print("   Press Ctrl+C to stop the server")
    print("─" * 70)
    print()
    
    # Wait a moment for server to start, then open browser
    def open_browser():
        time.sleep(2)
        print("🌐 Opening browser...")
        webbrowser.open("http://localhost:8000")
    
    import threading
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # Run the server using venv Python
    try:
        os.chdir(script_dir)
        subprocess.run([python_executable, "web_terminal.py"])
    except KeyboardInterrupt:
        print()
        print("─" * 70)
        print("👋 Server stopped. Goodbye!")
        print("=" * 70)

if __name__ == "__main__":
    main()
