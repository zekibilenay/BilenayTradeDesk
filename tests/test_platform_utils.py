from pathlib import Path

from tradedesk import platform_utils as pu

HOME = Path("/home/zeki")
ALWAYS, NEVER = (lambda p: True), (lambda p: False)


def test_data_folder_is_next_to_the_app_on_windows_and_linux_and_from_source():
    app = Path("/apps/BilenayTradeDesk")
    for platform in ("win32", "linux"):
        for frozen in (True, False):
            assert pu.choose_data_dir(app, frozen, platform, HOME, {}, ALWAYS) == app / "data"
    assert pu.choose_data_dir(app, False, "darwin", HOME, {}, ALWAYS) == app / "data"      # source run on a Mac


def test_macos_app_keeps_its_data_outside_the_bundle():
    app = Path("/Applications/BilenayTradeDesk.app/Contents/MacOS")
    got = pu.choose_data_dir(app, True, "darwin", HOME, {}, ALWAYS)
    assert got == HOME / "Library" / "Application Support" / "BilenayTradeDesk"


def test_read_only_install_falls_back_to_the_user_folder():
    app = Path("/opt/BilenayTradeDesk")
    assert pu.choose_data_dir(app, True, "linux", HOME, {}, NEVER) == HOME / ".local" / "share" / "BilenayTradeDesk"
    assert pu.choose_data_dir(app, True, "linux", HOME, {"XDG_DATA_HOME": "/x/share"}, NEVER) == \
        Path("/x/share/BilenayTradeDesk")
    assert pu.choose_data_dir(Path("C:/Program Files/B"), True, "win32", HOME, {"APPDATA": "C:/Users/z/AppData/Roaming"},
                              NEVER) == Path("C:/Users/z/AppData/Roaming/BilenayTradeDesk")
    assert pu.choose_data_dir(app, True, "win32", HOME, {}, NEVER) == HOME / "AppData" / "Roaming" / "BilenayTradeDesk"


def test_only_the_chosen_folder_is_probed():
    probed = []
    pu.choose_data_dir(Path("/a"), True, "linux", HOME, {}, lambda p: probed.append(p) or True)
    assert probed == [Path("/a/data")]
    probed.clear()
    pu.choose_data_dir(Path("/a"), True, "darwin", HOME, {}, lambda p: probed.append(p) or True)
    assert probed == []                                                  # the bundle is never touched on a Mac


def test_wheel_notches_per_system():
    assert pu.wheel_notches("??", 120, "win32") == 1.0 and pu.wheel_notches("??", -240, "win32") == -2.0
    assert pu.wheel_notches("??", 30, "win32") == 0.25                   # touchpad fraction
    assert pu.wheel_notches(4, 0, "linux") == 1.0 and pu.wheel_notches(5, 0, "linux") == -1.0
    assert pu.wheel_notches("??", 120, "linux") == 1.0                   # Tk 9 on X11 sends MouseWheel
    assert pu.wheel_notches("??", 4, "darwin") == 1.0 and pu.wheel_notches("??", -2, "darwin") == -0.5
    assert pu.wheel_notches("??", "??", "win32") == 0.0 and pu.wheel_notches(None, None, "darwin") == 0.0


def test_texts_name_the_right_shortcut():
    assert pu.paste_shortcut("win32") == "Ctrl+V" and pu.paste_shortcut("linux") == "Ctrl+V"
    assert pu.paste_shortcut("darwin") == "⌘V"
    assert pu.screenshot_hint("win32") == "Win+Shift+S" and "Shift" in pu.screenshot_hint("darwin")
    assert "clipboard" in pu.screenshot_hint("linux")
    assert "xclip" in pu.clipboard_help("linux") and pu.clipboard_help("win32") == "" == pu.clipboard_help("darwin")
    assert pu.is_mac("darwin") and not pu.is_mac("linux") and pu.is_windows("win32") and not pu.is_windows("darwin")


def test_writable_check_leaves_no_folders_behind(tmp_path):
    from tradedesk import paths
    deep = tmp_path / "a" / "b" / "data"
    assert paths._writable(deep) is True
    assert not (tmp_path / "a").exists()                                 # everything it created is removed again
    (tmp_path / "keep").mkdir()
    assert paths._writable(tmp_path / "keep") is True and (tmp_path / "keep").exists()
    assert not (tmp_path / "keep" / ".write_test").exists()
    blocker = tmp_path / "file"
    blocker.write_text("x")
    assert paths._writable(blocker / "data") is False                    # a folder can not be made inside a file
