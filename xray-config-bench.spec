# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build specification for Xray Config Bench standalone executable."""

import sys
from PyInstaller.utils.hooks import collect_all

block_cipher = None

datas = []
binaries = []
hiddenimports = [
    'platformdirs',
    'requests',
    'socks',
    'sqlite3',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
]

# Collect platformdirs and PySide6 metadata
pdirs_datas, pdirs_binaries, pdirs_hiddenimports = collect_all('platformdirs')
datas += pdirs_datas
binaries += pdirs_binaries
hiddenimports += pdirs_hiddenimports

pyside_datas, pyside_binaries, pyside_hidden = collect_all('PySide6')
datas += pyside_datas
binaries += pyside_binaries
hiddenimports += pyside_hidden

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='xray-config-bench',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Windowed GUI application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
