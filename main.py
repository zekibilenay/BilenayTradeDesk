def main():
    try:                                # crisp (non-blurry) text on Windows
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    try:                                # own taskbar identity -> the TradeHub icon (not python.exe's) is shown
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("TradeHub.Desktop")
    except Exception:
        pass
    from tradehub.app import TradeHubApp
    TradeHubApp().mainloop()


if __name__ == "__main__":
    main()
