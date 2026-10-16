# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

ROOT_DIR = os.path.abspath(os.path.join(SPECPATH, '..'))

# Collect all complex packages
yt_dlp_datas, yt_dlp_binaries, yt_dlp_hiddenimports = collect_all('yt_dlp')
mutagen_datas, mutagen_binaries, mutagen_hiddenimports = collect_all('mutagen')
pillow_datas, pillow_binaries, pillow_hiddenimports = collect_all('PIL')
heif_datas, heif_binaries, heif_hiddenimports = collect_all('pillow_heif')
p2d_datas, p2d_binaries, p2d_hiddenimports = collect_all('pdf2docx')
fitz_datas, fitz_binaries, fitz_hiddenimports = collect_all('fitz')
docx_datas, docx_binaries, docx_hiddenimports = collect_all('docx')
reportlab_datas, reportlab_binaries, reportlab_hiddenimports = collect_all('reportlab')
openpyxl_datas, openpyxl_binaries, openpyxl_hiddenimports = collect_all('openpyxl')
pypdf_datas, pypdf_binaries, pypdf_hiddenimports = collect_all('pypdf')

# Collect Windows binaries (ffmpeg, ffprobe) if provided
binaries = yt_dlp_binaries + mutagen_binaries + pillow_binaries + heif_binaries + p2d_binaries + fitz_binaries + docx_binaries + reportlab_binaries + openpyxl_binaries + pypdf_binaries

for search_dir in [os.path.join(ROOT_DIR, '1_resources'), os.path.join(ROOT_DIR, 'bin')]:
    for b in ['ffmpeg.exe', 'ffprobe.exe']:
        b_path = os.path.join(search_dir, b)
        if os.path.isfile(b_path):
            binaries.append((b_path, '.'))

datas = [
    (os.path.join(ROOT_DIR, '1_resources', 'AppIcon.ico'), '.'),
] + yt_dlp_datas + mutagen_datas + pillow_datas + heif_datas + p2d_datas + fitz_datas + docx_datas + reportlab_datas + openpyxl_datas + pypdf_datas

hiddenimports = [
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'mutagen',
    'yt_dlp',
    'PIL',
    'pillow_heif',
    'pandas',
    'openpyxl',
    'docx',
    'pdf2docx',
    'pypdf',
    'reportlab',
    'fitz',
] + yt_dlp_hiddenimports + mutagen_hiddenimports + pillow_hiddenimports + heif_hiddenimports + p2d_hiddenimports + fitz_hiddenimports + docx_hiddenimports + reportlab_hiddenimports + openpyxl_hiddenimports + pypdf_hiddenimports

a = Analysis(
    [os.path.join(ROOT_DIR, '2_code', 'gui.py')],
    pathex=[os.path.join(ROOT_DIR, '2_code')],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'pytest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='UniversalMediaConverter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT_DIR, '1_resources', 'AppIcon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='UniversalMediaConverter',
)
