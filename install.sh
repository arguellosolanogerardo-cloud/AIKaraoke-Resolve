#!/bin/bash
# AIKaraoke Resolve - Mac/Linux Installer

echo ""
echo "================================================"
echo " AIKaraoke Resolve - Mac/Linux Installer"
echo "================================================"
echo ""

# Check Python
echo "[1/4] Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 not found. Install from https://python.org"
    exit 1
fi
python3 --version
echo "OK"
echo ""

# Check ffmpeg
echo "[2/4] Checking ffmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo "WARNING: ffmpeg not found."
    echo "Mac: brew install ffmpeg"
    echo "Ubuntu: sudo apt install ffmpeg"
else
    echo "OK - $(ffmpeg -version 2>&1 | head -1)"
fi
echo ""

# Install dependencies
echo "[3/4] Installing Python dependencies..."
pip3 install -r requirements.txt
echo ""

# Copy to Resolve Scripts
echo "[4/4] Installing to DaVinci Resolve..."

# Mac path
RESOLVE_SCRIPTS_MAC="$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Support/Developer/Scripting/Scripts"
# Linux path
RESOLVE_SCRIPTS_LINUX="$HOME/.local/share/DaVinciResolve/Developer/Scripting/Scripts"

if [ -d "$RESOLVE_SCRIPTS_MAC" ]; then
    cp scripts/aikaraoke_main.py "$RESOLVE_SCRIPTS_MAC/AIKaraoke Resolve.py"
    echo "OK - Installed to Mac Resolve Scripts folder"
elif [ -d "$RESOLVE_SCRIPTS_LINUX" ]; then
    cp scripts/aikaraoke_main.py "$RESOLVE_SCRIPTS_LINUX/AIKaraoke Resolve.py"
    echo "OK - Installed to Linux Resolve Scripts folder"
else
    echo "WARNING: DaVinci Resolve scripts folder not found."
    echo "Copy scripts/aikaraoke_main.py manually to your Resolve Scripts folder."
fi

echo ""
echo "================================================"
echo " INSTALLATION COMPLETE!"
echo " In DaVinci Resolve: Workspace > Scripts > AIKaraoke Resolve"
echo "================================================"
