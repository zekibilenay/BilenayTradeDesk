#!/usr/bin/env python3
"""Builds Bilenay Trade Desk for the system you run it on and packs it into release/.

    python build.py

  Windows -> release/BilenayTradeDesk-v<ver>-windows.zip          (BilenayTradeDesk\\BilenayTradeDesk.exe)
  macOS   -> release/BilenayTradeDesk-v<ver>-macos-arm64.zip      (BilenayTradeDesk.app, Apple Silicon)
             release/BilenayTradeDesk-v<ver>-macos-intel.zip      (BilenayTradeDesk.app, Intel Macs)
  Linux   -> release/BilenayTradeDesk-v<ver>-linux.tar.gz         (BilenayTradeDesk/BilenayTradeDesk)

PyInstaller can not cross-compile: every system has to be built on that system. The GitHub workflow
(.github/workflows/build.yml) does exactly that on four runners when you push a version tag.
Needs Python 3.10+ with Tk, and:  pip install -r requirements.txt pyinstaller
"""
import os
import platform
import plistlib
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from tradedesk import APP_VERSION  # noqa: E402

NAME = "BilenayTradeDesk"
DIST, BUILD, RELEASE = ROOT / "dist", ROOT / "build", ROOT / "release"


def target() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos-arm64" if platform.machine().lower() in ("arm64", "aarch64") else "macos-intel"
    return "linux"


def run(cmd):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], cwd=ROOT, check=True)


def check_tk():
    try:
        import tkinter
    except ImportError:
        sys.exit("tkinter is missing. Windows/macOS: use the python.org installer (keep 'tcl/tk'). "
                 "Linux: install python3-tk.")
    if tkinter.TkVersion < 8.6:
        sys.exit(f"Tk {tkinter.TkVersion} is too old, Tk 8.6 or newer is needed.")
    print(f"Tk {tkinter.TkVersion}")


def pyinstaller(tgt: str):
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed",
           "--name", NAME, "--add-data", f"assets{os.pathsep}assets", "--hidden-import", "PIL._tkinter_finder"]
    if tgt == "windows":
        cmd += ["--icon", "assets/icon.ico"]
    elif tgt.startswith("macos"):
        cmd += ["--icon", "assets/icon.icns", "--osx-bundle-identifier", "com.bilenay.tradedesk"]
    run(cmd + ["main.py"])


def finish_mac_app():
    """Version in the Finder's info window, then an ad-hoc signature (Apple Silicon refuses unsigned code)."""
    app = DIST / f"{NAME}.app"
    plist_path = app / "Contents" / "Info.plist"
    with open(plist_path, "rb") as fh:
        info = plistlib.load(fh)
    info.update({"CFBundleShortVersionString": APP_VERSION, "CFBundleVersion": APP_VERSION,
                 "CFBundleDisplayName": "Bilenay Trade Desk", "NSHighResolutionCapable": True,
                 "LSApplicationCategoryType": "public.app-category.finance"})
    with open(plist_path, "wb") as fh:
        plistlib.dump(info, fh)
    run(["codesign", "--force", "--deep", "--sign", "-", app])
    return app


def pack(tgt: str) -> Path:
    RELEASE.mkdir(exist_ok=True)
    stem = f"{NAME}-v{APP_VERSION}-{tgt}"
    if tgt == "windows":
        exe = DIST / NAME / f"{NAME}.exe"
        if not exe.exists():
            sys.exit(f"{exe} was not built")
        out = RELEASE / f"{stem}.zip"
        out.unlink(missing_ok=True)
        shutil.make_archive(str(out.with_suffix("")), "zip", root_dir=DIST, base_dir=NAME)
        return out
    if tgt.startswith("macos"):
        app = finish_mac_app()
        if not (app / "Contents" / "MacOS" / NAME).exists():
            sys.exit(f"{app} was not built")
        out = RELEASE / f"{stem}.zip"
        out.unlink(missing_ok=True)
        run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", app, out])   # keeps links and permissions
        return out
    folder = DIST / NAME                                                           # linux
    if not (folder / NAME).exists():
        sys.exit(f"{folder / NAME} was not built")
    shutil.copy2(ROOT / "packaging" / "linux" / "install-linux.sh", folder / "install-linux.sh")
    shutil.copy2(ROOT / "assets" / "icon.png", folder / "icon.png")
    (folder / "install-linux.sh").chmod(0o755)
    out = RELEASE / f"{stem}.tar.gz"
    out.unlink(missing_ok=True)
    with tarfile.open(out, "w:gz") as tar:
        tar.add(folder, arcname=NAME)
    return out


def main():
    tgt = target()
    print(f"Bilenay Trade Desk {APP_VERSION} for {tgt}")
    check_tk()
    for d in (DIST, BUILD):
        shutil.rmtree(d, ignore_errors=True)
    pyinstaller(tgt)
    out = pack(tgt)
    print(f"\nDone: {out}  ({out.stat().st_size / 1_048_576:.1f} MB)")


if __name__ == "__main__":
    main()
