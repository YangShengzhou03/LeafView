block_cipher = None

a = Analysis(
    ['App.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources', 'resources'),
        ('weight', 'weight'),
        ('D:\\Code\\python\\LeafView\\venv\\lib\\site-packages\\paddleocr', 'paddleocr'),
        ('D:\\Code\\python\\LeafView\\venv\\lib\\site-packages\\paddleocr\\tools', 'paddleocr/tools')
    ],
hiddenimports=[
    'framework_pb2',
    'scipy.special.cython_special',
    'skimage',
    'skimage.feature._orb_descriptor_positions',
    'skimage.filters.edges',
    'skimage.data._fetchers',
    # 添加 PaddlePaddle 相关的隐式导入
    'paddle',
    'paddle.fluid',
    'paddle.fluid.core',
    'paddle.fluid.framework',
    'paddle.fluid.executor',
    'paddle.fluid.layers',
    'paddle.nn',
    'paddle.nn.functional',
    'paddle.vision',
    'paddle.vision.transforms',
    'paddleocr',  # 如果 paddleocr 不是自动包含的话
    # 根据需要添加更多 PaddlePaddle 模块或其它依赖
],
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
    name='App',
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