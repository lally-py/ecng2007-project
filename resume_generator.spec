# resume_generator.spec
# -*- mode: python ; coding: utf-8 -*-
# Try building wthouth one file

import sys
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files, collect_dynamic_libs
import comtypes  # Ensure comtypes is imported
import comtypes.client  # Ensure comtypes.client is imported

# Define a function to locate resource files
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# Specify the main script
main_script = 'resume_maker_v2.9.py'  # Replace with your actual script name

# Collect data files and directories
datas = [
    ('questions.json', '.'),                   # Copy to root
    ('trinidad_locations.txt', '.'),           # Copy to root
    ('resume_prompt.txt', '.'),                # Copy to root
    ('beep.mp3', '.'),                         # Copy to root
    ('icons/manual_icon.png', 'icons'),        # Copy to icons folder
    ('icons/voice_icon.png', 'icons'),
    ('icons/start_icon.png', 'icons'),
    ('icons/stop_icon.png', 'icons'),
    ('icons/next_icon.png', 'icons'),
    ('icons/prev_icon.png', 'icons'),
    ('icons/save_icon.png', 'icons'),
    ('icons/skip_icon.png', 'icons'),
    ('icons/accept_icon.png', 'icons'),
    ('icons/redo_icon.png', 'icons'),
    ('icons/add_more_icon.png', 'icons'),
    ('icons/pause_icon.png', 'icons'),
    ('icons/logo.png', 'icons'),                # Assuming you have a logo.png
    ('.env', '.'),                              # Copy .env to root
]

# Collect Python DLL and other necessary binaries
python_dll = os.path.join(sys.base_prefix, "python312.dll")
if not os.path.exists(python_dll):
    python_dll = os.path.join(sys.exec_prefix, "python312.dll")
    if not os.path.exists(python_dll):
        raise FileNotFoundError("python312.dll not found. Please verify your Python installation.")

binaries = [
    (python_dll, "."),  # Include python312.dll in the root of the executable
]

# Hidden imports (if any)
hiddenimports = [
    'customtkinter',
    'pyaudio',
    'wave',
    'tempfile',
    'threading',
    'requests',
    'pyttsx3',
    'speech_recognition',
    'openai',
    'PIL',
    'whisper',
    'numpy',
    'sounddevice',
    'time',
    'io',
    'webrtcvad',
    'collections',
    'fuzzywuzzy',
    'json',
    'dotenv',
    'docx',
    'docx.shared',
    'docx.enum.text',
    'docx.enum.style',
    'docx2pdf',
    'datetime',
    'tkinter',
    'tkinter.filedialog',
    'playsound',
    'comtypes',
    'pyttsx3.drivers',
    'pyttsx3.drivers.sapi5',
    'PIL.Image',
    'PIL._imagingtk',
    'win32com',
    'win32com.client',
    'comtypes.client',
    'comtypes.gen',
    'comtypes.client._generate',
]

# Collect all submodules and data files for comtypes
comtypes_submodules = collect_submodules('comtypes')
comtypes_data_files = collect_data_files('comtypes')

hiddenimports += comtypes_submodules
datas += comtypes_data_files

# Include comtypes.gen directory
comtypes_gen_dir = os.path.join(os.path.dirname(comtypes.__file__), 'gen')
datas += [(comtypes_gen_dir, 'comtypes/gen')]

# Collect all dependencies for webrtcvad
webrtcvad_datas, webrtcvad_binaries, webrtcvad_hiddenimports = collect_all('webrtcvad')
datas += webrtcvad_datas
binaries += webrtcvad_binaries
hiddenimports += webrtcvad_hiddenimports

# Collect all dependencies for pyaudio
pyaudio_datas, pyaudio_binaries, pyaudio_hiddenimports = collect_all('pyaudio')
datas += pyaudio_datas
binaries += pyaudio_binaries
hiddenimports += pyaudio_hiddenimports

# Analysis
a = Analysis(
    [main_script],
    pathex=[],  # PyInstaller will auto-detect, or specify the path if necessary
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# PYZ
pyz = PYZ(a.pure, a.zipped_data,
          cipher=None)

# EXE
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ResumeGenerator',  # Name of the executable
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to False if you don't want a console window
    icon=resource_path('icons/logo.ico'),  # Path to your executable icon (optional)
    onefile=True  # Add this line to compile into a single file
)

# COLLECT
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ResumeGenerator'
)