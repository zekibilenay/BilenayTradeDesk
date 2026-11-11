@echo off
REM Builds BilenayTradeDesk.exe  ->  dist\BilenayTradeDesk\BilenayTradeDesk.exe
REM Requires Python 3.10+ from python.org (keep the "tcl/tk and IDLE" option ticked).
cd /d "%~dp0"
py -m pip install --upgrade pip
py -m pip install -r requirements.txt pyinstaller
py -m PyInstaller --noconfirm --clean --onedir --windowed --name BilenayTradeDesk --icon assets\icon.ico --add-data "assets;assets" --hidden-import PIL._tkinter_finder main.py
echo.
echo Done. Your app: dist\BilenayTradeDesk\BilenayTradeDesk.exe
pause
