# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['server/gui.py'],
    pathex=[],
    binaries=[],
    datas=[('static', 'static'), ('app_icon.ico', '.'), ('PCDeck.ico', '.'), ('icon.ico', '.'), ('PCDeck_Mouse_Logo.png', '.'), ('PCDeck_Master_Logo.png', '.'), ('PCDeck_Logo.png', '.'), ('icon.png', '.'), ('icon-512.png', '.')],
    hiddenimports=['server.gui', 'server.main', 'server.screen_streamer', 'server.gamepad_manager', 'server.audio_streamer', 'server.camera_streamer', 'cv2', 'simplejpeg', 'numpy', 'vgamepad', 'sounddevice', 'pyaudiowpatch', 'pyvirtualcam', 'qrcode', 'tkinter', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets.auto', 'uvicorn.lifespan.on', 'pynput', 'mss', 'PIL'],
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
    name='PCDeck',
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
    icon=['app_icon.ico'],
)
