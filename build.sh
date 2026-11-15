#!/usr/bin/env sh
# Builds the app for the system you are on (macOS or Linux)  ->  release/
# Needs Python 3.10+ with Tk (macOS: python.org installer; Linux: sudo apt install python3-tk).
cd "$(dirname "$0")" || exit 1
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt pyinstaller
python3 build.py
