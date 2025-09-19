block_cipher = None

a = Analysis(
    ['App.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources', 'resources')
    ],
    hiddenimports=['numpy.core._multiarray_tests', 'numpy.core._multiarray_umath'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LeafView',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='LeafView_version_info.txt',
    icon='resources\\img\\icon.ico',
    optimize=0
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='App'
)