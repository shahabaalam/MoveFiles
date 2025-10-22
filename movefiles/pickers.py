from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path


def _ask_directory_gui(title: str) -> Path | None:
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askdirectory(title=title)
        root.destroy()
        if path:
            return Path(path)
        return None
    except Exception:
        return None


def _ask_directory_cli(prompt: str) -> Path | None:
    try:
        raw = input(prompt).strip().strip('"')
    except EOFError:
        return None
    if not raw:
        return None
    return Path(raw)


def _pick_directory(title_gui: str, prompt_cli: str) -> Path:
    path = _ask_directory_gui(title_gui)
    if path is None:
        path = _ask_directory_cli(prompt_cli)
    if path is None:
        print("No directory selected.")
        sys.exit(1)
    return path


def _pick_directories_multiple_gui(first_title: str, next_title: str) -> list[Path] | None:
    paths: list[Path] = []
    while True:
        title = first_title if not paths else next_title
        p = _ask_directory_gui(title)
        if p is None:
            break
        if p not in paths:
            paths.append(p)
    return paths if paths else None


def _pick_directories_multiple_cli(prompt: str) -> list[Path] | None:
    print(prompt)
    print("Tip: Separate multiple paths with ';'")
    try:
        raw = input(": ").strip()
    except EOFError:
        return None
    if not raw:
        return None
    parts = [r.strip().strip('"') for r in raw.split(";")]
    paths = [Path(p) for p in parts if p]
    return paths if paths else None


def _pick_directories() -> list[Path]:
    # Prefer native Windows dialog that supports multi-select of folders
    if os.name == "nt":
        paths = _ask_directories_windows()
        if paths:
            return paths

    # Fallback: repeated single-folder selection via GUI
    paths = _pick_directories_multiple_gui(
        "Select a source folder (Cancel when done)",
        "Select another source folder (Cancel when done)",
    )
    if paths is None:
        paths = _pick_directories_multiple_cli(
            "Enter one or more source folder paths"
        )
    if not paths:
        print("No source folders selected.")
        sys.exit(1)
    return paths


def _ask_directories_windows() -> list[Path] | None:
    """Use Windows IFileOpenDialog to select multiple folders via Ctrl/Cmd."""
    try:
        # GUID struct
        class GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", ctypes.c_uint32),
                ("Data2", ctypes.c_uint16),
                ("Data3", ctypes.c_uint16),
                ("Data4", ctypes.c_ubyte * 8),
            ]

        # COM interface base
        class IUnknown(ctypes.Structure):
            _fields_ = [("lpVtbl", ctypes.POINTER(ctypes.c_void_p))]

        class IFileOpenDialog(IUnknown):
            pass

        class IShellItem(IUnknown):
            pass

        class IShellItemArray(IUnknown):
            pass

        # Prebuilt GUIDs
        CLSID_FileOpenDialog = GUID(0xDC1C5A9C, 0xE88A, 0x4DDE, (ctypes.c_ubyte * 8)(0xA5, 0xA1, 0x60, 0xF8, 0x2A, 0x20, 0xAE, 0xF7))
        IID_IFileOpenDialog = GUID(0xD57C7288, 0xD4AD, 0x4768, (ctypes.c_ubyte * 8)(0xBE, 0x02, 0x9D, 0x96, 0x95, 0x32, 0xD9, 0x60))
        IID_IShellItem = GUID(0x43826D1E, 0xE718, 0x42EE, (ctypes.c_ubyte * 8)(0xBC, 0x55, 0xA1, 0xE2, 0x61, 0xC3, 0x7B, 0xFE))
        IID_IShellItemArray = GUID(0xB63EA76D, 0x1F85, 0x456F, (ctypes.c_ubyte * 8)(0xA1, 0x9C, 0x48, 0x15, 0x9E, 0xFA, 0x85, 0x8B))

        # Flags
        CLSCTX_INPROC_SERVER = 0x1
        COINIT_APARTMENTTHREADED = 0x2
        FOS_PICKFOLDERS = 0x00000020
        FOS_ALLOWMULTISELECT = 0x00000200
        FOS_FORCEFILESYSTEM = 0x00000040
        SIGDN_FILESYSPATH = 0x80058000

        ole32 = ctypes.OleDLL('ole32')
        ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        ole32.CoInitializeEx.restype = ctypes.c_long
        ole32.CoUninitialize.argtypes = []
        ole32.CoUninitialize.restype = None
        ole32.CoCreateInstance.argtypes = [
            ctypes.POINTER(GUID), ctypes.c_void_p, ctypes.c_uint32,
            ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)
        ]
        ole32.CoCreateInstance.restype = ctypes.c_long
        ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
        ole32.CoTaskMemFree.restype = None

        def SUCCEEDED(hr: int) -> bool:
            return hr >= 0

        hr = ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED)
        # Proceed even if already initialized (RPC_E_CHANGED_MODE), we'll still uninit safely

        dlg_ptr = ctypes.c_void_p()
        hr = ole32.CoCreateInstance(
            ctypes.byref(CLSID_FileOpenDialog), None, CLSCTX_INPROC_SERVER,
            ctypes.byref(IID_IFileOpenDialog), ctypes.byref(dlg_ptr)
        )
        if not SUCCEEDED(hr):
            ole32.CoUninitialize()
            return None

        dlg = ctypes.cast(dlg_ptr.value, ctypes.POINTER(IFileOpenDialog))

        def com_method(iface, index, restype, *argtypes):
            vtbl = iface.contents.lpVtbl
            func_ptr = ctypes.c_void_p(vtbl[index])
            func = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)(func_ptr.value)
            return lambda *args: func(ctypes.cast(iface, ctypes.c_void_p), *args)

        # GetOptions, SetOptions
        GetOptions = com_method(dlg, 10, ctypes.c_long, ctypes.POINTER(ctypes.c_uint))
        SetOptions = com_method(dlg, 9, ctypes.c_long, ctypes.c_uint)
        Show = com_method(dlg, 3, ctypes.c_long, ctypes.c_void_p)
        ReleaseDlg = com_method(dlg, 2, ctypes.c_ulong)

        opts = ctypes.c_uint(0)
        hr = GetOptions(ctypes.byref(opts))
        if SUCCEEDED(hr):
            new_opts = opts.value | FOS_PICKFOLDERS | FOS_ALLOWMULTISELECT | FOS_FORCEFILESYSTEM
            hr = SetOptions(new_opts)
            if not SUCCEEDED(hr):
                ReleaseDlg()
                ole32.CoUninitialize()
                return None
        else:
            ReleaseDlg()
            ole32.CoUninitialize()
            return None

        hr = Show(None)
        if not SUCCEEDED(hr):
            ReleaseDlg()
            ole32.CoUninitialize()
            return None

        # GetResults -> IShellItemArray
        GetResults = com_method(dlg, 27, ctypes.c_long, ctypes.POINTER(ctypes.c_void_p))
        arr_ptr = ctypes.c_void_p()
        hr = GetResults(ctypes.byref(arr_ptr))
        if not SUCCEEDED(hr) or not arr_ptr.value:
            ReleaseDlg()
            ole32.CoUninitialize()
            return None

        arr = ctypes.cast(arr_ptr.value, ctypes.POINTER(IShellItemArray))
        ReleaseArr = com_method(arr, 2, ctypes.c_ulong)
        GetCount = com_method(arr, 7, ctypes.c_long, ctypes.POINTER(ctypes.c_uint))
        GetItemAt = com_method(arr, 8, ctypes.c_long, ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p))

        count = ctypes.c_uint(0)
        hr = GetCount(ctypes.byref(count))
        if not SUCCEEDED(hr):
            ReleaseArr(); ReleaseDlg(); ole32.CoUninitialize()
            return None

        results: list[Path] = []
        for i in range(count.value):
            item_ptr = ctypes.c_void_p()
            hr = GetItemAt(i, ctypes.byref(item_ptr))
            if not SUCCEEDED(hr) or not item_ptr.value:
                continue
            item = ctypes.cast(item_ptr.value, ctypes.POINTER(IShellItem))
            ReleaseItem = com_method(item, 2, ctypes.c_ulong)
            GetDisplayName = com_method(item, 5, ctypes.c_long, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p))
            name_ptr = ctypes.c_void_p()
            hr = GetDisplayName(SIGDN_FILESYSPATH, ctypes.byref(name_ptr))
            if SUCCEEDED(hr) and name_ptr.value:
                try:
                    path_str = ctypes.wstring_at(name_ptr.value)
                    if path_str:
                        p = Path(path_str)
                        if p.exists() and p.is_dir():
                            results.append(p)
                finally:
                    ole32.CoTaskMemFree(name_ptr)
            ReleaseItem()

        ReleaseArr()
        ReleaseDlg()
        ole32.CoUninitialize()
        return results if results else None
    except Exception:
        return None

