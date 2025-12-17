# Platform-Specific Setup Guide

## macOS

### Prerequisites
```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3 (recommended over default Python)
brew install python@3.11

# Verify installation
python3 --version
```

### Running the GUI
```bash
# Navigate to project directory
cd "/Users/pp/Desktop/YOUTUBE TELEGRAM"

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the GUI
python run_gui.py
```

### Troubleshooting macOS
- **"python: command not found"** → Use `python3` instead
- **tkinter error** → Usually included with Python 3
- **Cannot connect to GUI** → Check System Preferences > Security & Privacy

---

## Windows

### Prerequisites
```bash
# Download Python 3.11+ from https://www.python.org
# During installation:
# ✓ Check "Add Python to PATH"
# ✓ Check "Install tcl/tk and IDLE"

# Verify installation
python --version
pip --version
```

### Running the GUI
```bash
# Open Command Prompt or PowerShell

# Navigate to project directory
cd "C:\Users\YourName\Desktop\YOUTUBE TELEGRAM"

# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the GUI
python run_gui.py
```

### Troubleshooting Windows
- **pip not found** → Reinstall Python with "Add to PATH" option
- **Module not found** → Ensure virtual environment is activated
- **Cannot find tkinter** → Reinstall Python, ensure tcl/tk is selected

---

## Linux (Ubuntu/Debian)

### Prerequisites
```bash
# Update package manager
sudo apt update
sudo apt upgrade

# Install Python and dependencies
sudo apt install python3 python3-pip python3-tk python3-dev

# Verify installation
python3 --version
pip3 --version
```

### Running the GUI
```bash
# Navigate to project directory
cd ~/Desktop/"YOUTUBE TELEGRAM"

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the GUI
python run_gui.py
```

### Troubleshooting Linux
- **tkinter not found** → Run: `sudo apt install python3-tk`
- **Permission denied** → Make executable: `chmod +x run_gui.py`
- **Display issues** → Ensure X11 is running or use WSL2 with WSLg on Windows

---

## Using Virtual Environments (Recommended)

### Why Use Virtual Environment?
- Isolates project dependencies
- Prevents version conflicts
- Easy cleanup (just delete folder)
- Safe testing environment

### Setup (All Platforms)
```bash
# Create virtual environment
python -m venv venv

# Activate it
# macOS/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Your terminal should show (venv) prefix
```

### Deactivate When Done
```bash
deactivate
```

---

## Running as a Service/Scheduled Task

### macOS (LaunchAgent)
Create `~/Library/LaunchAgents/com.youtube.automation.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.youtube.automation</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/Users/pp/Desktop/YOUTUBE TELEGRAM/run_gui.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <array>
        <dict>
            <key>Hour</key>
            <integer>9</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
    </array>
</dict>
</plist>
```

Then load it:
```bash
launchctl load ~/Library/LaunchAgents/com.youtube.automation.plist
```

### Windows (Task Scheduler)
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (time or event)
4. Set action to run: `python C:\path\to\run_gui.py`
5. Enable "Run with highest privileges"

### Linux (cron)
```bash
# Edit crontab
crontab -e

# Add entry (run daily at 9 AM)
0 9 * * * /home/user/YOUTUBE\ TELEGRAM/venv/bin/python /home/user/YOUTUBE\ TELEGRAM/run_gui.py
```

---

## Environment Variables Setup

### Create .env File

#### macOS/Linux
```bash
cd "/Users/pp/Desktop/YOUTUBE TELEGRAM"
cat > .env << EOF
GEMINI_API_KEY=your_api_key_here
EOF
```

#### Windows (PowerShell)
```powershell
cd "C:\Users\YourName\Desktop\YOUTUBE TELEGRAM"
@'
GEMINI_API_KEY=your_api_key_here
'@ | Out-File -Encoding UTF8 .env
```

#### Windows (Command Prompt)
```batch
cd C:\Users\YourName\Desktop\YOUTUBE TELEGRAM
(echo GEMINI_API_KEY=your_api_key_here) > .env
```

---

## Updating Dependencies

### Check for Updates
```bash
pip list --outdated
```

### Update Single Package
```bash
pip install --upgrade package_name
```

### Update All Packages
```bash
pip install --upgrade -r requirements.txt
```

### Create Updated Requirements
```bash
pip freeze > requirements.txt
```

---

## Python Version Management

### Using pyenv (macOS/Linux)
```bash
# Install pyenv
brew install pyenv  # macOS
# or follow: https://github.com/pyenv/pyenv

# List available versions
pyenv versions

# Install specific version
pyenv install 3.11.5

# Use for project
pyenv local 3.11.5
```

### Using conda (All Platforms)
```bash
# Install conda from https://www.anaconda.com/download

# Create environment
conda create -n youtube-automation python=3.11

# Activate
conda activate youtube-automation

# Install requirements
pip install -r requirements.txt

# Run
python run_gui.py
```

---

## Performance Tips

1. **Use SSD storage** - Faster file operations
2. **Close other apps** - More RAM available
3. **Good internet connection** - Smooth API calls
4. **Run during off-peak hours** - Better YouTube API performance

---

## Debugging Tips

### Enable Verbose Output
```bash
# macOS/Linux
PYTHONVERBOSE=1 python run_gui.py

# Windows
set PYTHONVERBOSE=1
python run_gui.py
```

### Check Python Path
```bash
python -c "import sys; print('\n'.join(sys.path))"
```

### List Installed Packages
```bash
pip list
```

### Test Specific Import
```bash
python -c "import googleapiclient; print(googleapiclient.__version__)"
```

---

## Getting Help

### Check Python Version
```bash
python --version
python -c "import sys; print(sys.executable)"
```

### Verify Dependencies
```bash
pip check
```

### Generate System Info
```bash
python -c "import platform; print(platform.platform())"
```

---

**Note**: Some GUI features require display capabilities. If running headless (no display), consider using the terminal version or setting up X11 forwarding.
