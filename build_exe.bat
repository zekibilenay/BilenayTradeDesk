@echo off
REM Builds the Windows app  ->  release\BilenayTradeDesk-v<version>-windows.zip  (and dist\BilenayTradeDesk\BilenayTradeDesk.exe)
REM Requires Python 3.10+ from python.org (keep the "tcl/tk and IDLE" option ticked).
cd /d "%~dp0"
py -m pip install --upgrade pip
py -m pip install -r requirements.txt pyinstaller
py build.py
echo.
echo Your app: dist\BilenayTradeDesk\BilenayTradeDesk.exe
pause
