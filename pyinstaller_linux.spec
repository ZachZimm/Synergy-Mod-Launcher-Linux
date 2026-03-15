# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all


datas = [("recovered_launcher", "recovered_launcher")]
binaries = []
hiddenimports = []

for package in (
    "PyQt5",
    "requests",
    "bs4",
    "certifi",
    "charset_normalizer",
    "idna",
    "urllib3",
    "psutil",
):
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hiddenimports

hiddenimports += [
    "PyQt5.QtCore",
    "PyQt5.QtGui",
    "PyQt5.QtNetwork",
    "PyQt5.QtWidgets",
    "bs4",
    "collections",
    "hashlib",
    "json",
    "logging",
    "logging.handlers",
    "os",
    "pathlib",
    "psutil",
    "requests",
    "requests.adapters",
    "subprocess",
    "urllib3.util.retry",
    "uuid",
]

a = Analysis(
    ["run_sc2campaignlauncher.py"],
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
    [],
    exclude_binaries=True,
    name="SC2CampaignLauncherLinux",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SC2CampaignLauncherLinux",
)
