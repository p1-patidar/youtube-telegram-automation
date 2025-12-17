#!/usr/bin/env python3
"""
Launcher script for YouTube Shorts Automation GUI
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from automation_gui import main
    main()
except ImportError as e:
    print(f"Error: Missing required module - {e}")
    print("\nPlease install dependencies:")
    print("  pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"Error starting GUI: {e}")
    sys.exit(1)
