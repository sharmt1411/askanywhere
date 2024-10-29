# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('icon/Depth_8,_Frame_0explore-角标.png','icon'),
        ('icon/Depth_8,_Frame_0chat.png','icon'),
        ('icon/Depth_9,_Frame_0notes.png','icon'),
        ('icon/Depth_8,_Frame_0explore.png','icon'),],
    hiddenimports=[
                 'markdown2',
                 'openai',
                 'PyAutoGUI',
                 'pynput.keyboard',
                 'pynput.mouse',
                 'pyperclip',
                 'PyQt5',
                 'PyQt5.sip',
                 'tinydb',
                 'tinydb_sqlite',
             ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon\\001.ico'],
)
