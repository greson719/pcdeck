# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('static', 'static'), ('drivers', 'drivers'), ('PCDeck.apk', '.'), ('app_icon.ico', '.'), ('PCDeck.ico', '.'), ('icon.ico', '.'), ('PCDeck_Mouse_Logo.png', '.'), ('PCDeck_Master_Logo.png', '.'), ('PCDeck_Logo.png', '.'), ('icon.png', '.'), ('icon-512.png', '.')]
binaries = []
hiddenimports = ['server.gui', 'server.main', 'server.binary_protocol', 'server.license_manager', 'server.screen_streamer', 'server.wifi_manager', 'server.wifi_latency_manager', 'server.gamepad_manager', 'server.audio_streamer', 'server.camera_streamer', 'cv2', 'simplejpeg', 'numpy', 'vgamepad', 'pystray', 'sounddevice', 'pyaudiowpatch', 'pyvirtualcam', 'qrcode', 'tkinter', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets.auto', 'uvicorn.lifespan.on', 'pynput', 'mss', 'PIL']
tmp_ret = collect_all('vgamepad')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pystray')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['server/gui.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    version='version_info.txt',
    uac_admin=True,
    icon=['app_icon.ico'],
)
