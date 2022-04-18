# -*- mode: python ; coding: utf-8 -*-
# for M1 macOS

block_cipher = None


a = Analysis(
    ['__main__.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('peekingduck_studio/peekingduckstudio.kv', 'peekingduck_studio'),
        ('../peekingduck/peekingduck','peekingduck'),
        ('/opt/homebrew/Caskroom/miniforge/base/envs/temp/lib/libprotobuf.31.dylib', '.'),
        ('/opt/homebrew/Caskroom/miniforge/base/envs/temp/lib/python3.9/lib-dynload/cmath.cpython-39-darwin.so', 'lib-dynload'),
#        ('/opt/homebrew/Caskroom/miniforge/base/envs/temp/lib/python3.9/logging', 'logging'),
#        ('/opt/homebrew/Caskroom/miniforge/base/envs/temp/lib/python3.9/site-packages', 'site-packages'),
        ('/opt/homebrew/Caskroom/miniforge/base/envs/temp/lib/python3.9/site-packages/PIL', 'PIL'),
        ('/opt/homebrew/Caskroom/miniforge/base/envs/temp/lib/python3.9/site-packages/absl', 'absl'),
        ('/opt/homebrew/Caskroom/miniforge/base/envs/temp/lib/python3.9/site-packages/astunparse', 'astunparse'),
#        ('/opt/homebrew/Caskroom/miniforge/base/envs/temp/lib/python3.9/site-packages/charset_normalizer', 'charset_normalizer'),
#        ('/opt/homebrew/Caskroom/miniforge/base/envs/temp/lib/python3.9/site-packages/click', 'click'),
#        ('/opt/homebrew/Caskroom/miniforge/base/envs/temp/lib/python3.9/site-packages/colorama', 'colorama'),
        ('/opt/homebrew/Caskroom/miniforge/base/envs/temp/lib/python3.9/site-packages/flatbuffers', 'flatbuffers'),
        ('/opt/homebrew/Caskroom/miniforge/base/envs/temp/lib/python3.9/site-packages/gast', 'gast'),
        ('/opt/homebrew/Caskroom/miniforge/base/envs/temp/lib/python3.9/site-packages/google', 'google'),
        ('/opt/homebrew/Caskroom/miniforge/base/envs/temp/lib/python3.9/html', 'html'),
        ('/opt/homebrew/Caskroom/miniforge/base/envs/temp/lib/python3.9/site-packages/keras', 'keras'),
        ('/opt/homebrew/Caskroom/miniforge/base/envs/temp/lib/python3.9/site-packages/keras_preprocessing', 'keras_preprocessing'),
        ('/opt/homebrew/Caskroom/miniforge/base/envs/temp/lib/python3.9/site-packages/opt_einsum', 'opt_einsum'),
#        ('/opt/homebrew/Caskroom/miniforge/base/envs/temp/lib/python3.9/site-packages/requests', 'requests'),
        ('/opt/homebrew/Caskroom/miniforge/base/envs/temp/lib/python3.9/site-packages/scipy', 'scipy'),
        ('/opt/homebrew/Caskroom/miniforge/base/envs/temp/lib/python3.9/site-packages/tensorboard', 'tensorboard'),
        ('/opt/homebrew/Caskroom/miniforge/base/envs/temp/lib/python3.9/site-packages/tensorflow', 'tensorflow'),
        ('/opt/homebrew/Caskroom/miniforge/base/envs/temp/lib/python3.9/site-packages/tensorflow-plugins', 'tensorflow-plugins'),
        ('/opt/homebrew/Caskroom/miniforge/base/envs/temp/lib/python3.9/site-packages/tensorflow_estimator', 'tensorflow_estimator'),
        ('/opt/homebrew/Caskroom/miniforge/base/envs/temp/lib/python3.9/site-packages/torch', 'torch'),
        ('/opt/homebrew/Caskroom/miniforge/base/envs/temp/lib/python3.9/site-packages/torchvision', 'torchvision'),
#        ('/opt/homebrew/Caskroom/miniforge/base/envs/temp/lib/python3.9/site-packages/tqdm', 'tqdm'),
        ('/opt/homebrew/Caskroom/miniforge/base/envs/temp/lib/python3.9/unittest', 'unittest'),
#        ('/opt/homebrew/Caskroom/miniforge/base/envs/temp/lib/python3.9/site-packages/urllib3', 'urllib3'),
    ],
    hiddenimports=[
        "absl",
        "click",
        "colorama",
        "dataclasses",
        "google",
        "google.protobuf",
        "logging",
        "_markupbase",
        "pickletools",
        "requests",
        "scipy",
        "shapely",
        "termcolor",
        "timeit",
        "tqdm",
        "wrapt",
        "yaml",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='PeekingDuckStudio',
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
    icon='pkds_mac.icns',
)
app = BUNDLE(
    exe,
    name='PeekingDuckStudio.app',
    icon='pkds_mac.icns',
    bundle_identifier=None,
)
