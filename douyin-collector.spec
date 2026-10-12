# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置：douyin-collector Windows EXE。"""
import os
from pathlib import Path

block_cipher = None

# Playwright driver（含 node 二进制）
import playwright
_pw_dir = str(Path(playwright.__file__).parent)

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("app/templates", "app/templates"),
        ("app/static", "app/static"),
        ("config.example.yaml", "."),
        ("README.md", "."),
        (_pw_dir + "/driver", "playwright/driver"),
    ],
    hiddenimports=[
        "playwright",
        "peewee",
        "pandas",
        "openpyxl",
        "yaml",
        "flask",
        "werkzeug",
        "jinja2",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib"],
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
    name="douyin-collector",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,  # 保留控制台看日志
    icon=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="douyin-collector",
)
