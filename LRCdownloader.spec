# -*- mode: python ; coding: utf-8 -*-
"""Canonical PyInstaller spec: onedir, windowed, cross-platform.

Build locally via `python scripts/build.py` (preferred — passes matching
flags) or directly with `pyinstaller LRCdownloader.spec`.
"""
block_cipher = None

a = Analysis(
    ['lrcdownloader/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'PySide6',
        'mutagen',
        'httpx',
        'syncedlyrics',
        'rapidfuzz',
        'platformdirs',
        'keyring',
        'keyring.backends',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LRCdownloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # windowed GUI app; use scripts/build.py --debug for a console build
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='LRCdownloader',
)
