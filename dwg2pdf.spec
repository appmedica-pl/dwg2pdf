# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for dwg2pdf.
Produces a single standalone .exe that requires no Python runtime.
External tools (dwg2dxf.exe, libredwg-0.dll) must be placed alongside
the built exe.
"""
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# ezdxf uses dynamic imports in addons — collect everything
ezdxf_hiddenimports = collect_submodules("ezdxf")
ezdxf_datas = collect_data_files("ezdxf")

# PyMuPDF binaries and data
pymupdf_hiddenimports = collect_submodules("pymupdf")
pymupdf_datas = collect_data_files("pymupdf")

a = Analysis(
    ["dwg2pdf.py"],
    pathex=[],
    binaries=[],
    datas=ezdxf_datas + pymupdf_datas,
    hiddenimports=ezdxf_hiddenimports + pymupdf_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # GUI backends — not needed for CLI
        "tkinter",
        "PySide6",
        "PyQt5",
        "PyQt6",
        "matplotlib",
        # CairoSVG — not used
        "cairosvg",
        "cairocffi",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="dwg2pdf",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    icon=None,
)
