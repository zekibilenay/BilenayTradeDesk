import sys


def main():
    if sys.platform.startswith("win"):
        try:                            # crisp (non-blurry) text on Windows
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        try:                            # own taskbar identity -> the Trade Desk icon (not python.exe's) is shown
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Bilenay.TradeDesk")
        except Exception:
            pass
    from tradedesk.app import TradeDeskApp
    TradeDeskApp().mainloop()


if __name__ == "__main__":
    main()
