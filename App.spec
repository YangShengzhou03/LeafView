# App.spec 文件内容
block_cipher = None

a = Analysis(
    ['App.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources', 'resources'),  # 应用程序使用的资源文件夹
        ('weight', 'weight'),  # 如果有其他资源或权重文件夹，同样添加在这里
        ('D:\\Code\\python\\LeafView\\venv\\lib\\site-packages\\paddleocr', 'paddleocr'),  # 添加PaddleOCR目录
        ('D:\\Code\\python\\LeafView\\venv\\lib\\site-packages\\paddleocr\\tools', 'paddleocr/tools')  # 特别指定paddleocr的tools目录
    ],
    hiddenimports=[
        # PaddleOCR相关
        'paddleocr',
        'ppocr',
        'tools.infer.utility',
        'tools.infer.predict_system',
        'tools.infer.predict_rec',
        'ppocr.postprocess',
        'ppocr.postprocess.db_postprocess',
        'ppocr.postprocess.pg_postprocess',
        'ppocr.utils.e2e_utils.pgnet_pp_utils',
        'ppocr.utils.e2e_utils.extract_textpoint_slow',

        'albumentations',

        # Shapely
        'shapely',
        'shapely.geometry',

        # Pyclipper
        'pyclipper',

        # Pillow (PIL)
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageFont',

        # NumPy
        'numpy',

        # OpenCV
        'cv2',

        # SciPy
        'scipy',
        'scipy.linalg',
        'scipy.sparse',
        'scipy.special',
        'scipy.stats',
        'scipy.optimize',
        'scipy.ndimage',
        'scipy.signal',
        'scipy.fftpack',
        'scipy.integrate',
        'scipy.interpolate',
        'scipy.spatial',
        'scipy.cluster',
        'scipy.io',
        'scipy.sparse.csgraph',
        'scipy.sparse.linalg',

        # Matplotlib
        'matplotlib',
        'matplotlib.backends.backend_agg',
        'matplotlib.pyplot',
        'matplotlib.figure',
        'matplotlib.axes',
        'matplotlib.cm',
        'matplotlib.colors',
        'matplotlib.ticker',
        'matplotlib.transforms',
        'matplotlib.text',
        'matplotlib.font_manager',
        'matplotlib.lines',
        'matplotlib.patches',
        'matplotlib.path',
        'matplotlib.image',
        'matplotlib.collections',
        'matplotlib.contour',
        'matplotlib.legend',
        'matplotlib.scale',
        'matplotlib.spines',
        'matplotlib.tight_layout',
        'matplotlib.tri',
        'matplotlib.widgets',
        'matplotlib.animation',
        'matplotlib.offsetbox',
        'matplotlib.projections',
        'matplotlib.table',
        'matplotlib.testing',
        'matplotlib.style',
        'matplotlib.colorbar',
        'matplotlib.dates',
        'matplotlib.markers',
        'matplotlib.texmanager',
        'matplotlib.units',
        'matplotlib.quiver',
        'matplotlib.sankey',
        'matplotlib.streamplot',
        'matplotlib.stackplot',
        'matplotlib.rasterize',
        'matplotlib.backends.backend_tkagg',

        # Scikit-image
        'skimage',
        'skimage.morphology',
        'skimage.measure',
        'skimage.filters',
        'skimage.segmentation',
        'skimage.feature',
        'skimage.transform',
        'skimage.color',
        'skimage.exposure',
        'skimage.restoration',
        'skimage.util',
        'skimage.data',
        'skimage.io',
        'skimage.draw',
        'skimage.graph',
        'skimage.future',
        'skimage.metrics',
        'skimage.morphology._skeletonize',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],  # 如果发现不需要的模块可以在此处排除
    noarchive=False,
    optimize=0
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
    icon=['resources\\img\\icon.ico']
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