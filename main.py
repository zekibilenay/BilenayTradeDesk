def main():
    try:                                # crisp (non-blurry) text on Windows
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    from tradehub.app import TradeHubApp
    TradeHubApp().mainloop()


if __name__ == "__main__":
    main()
