# PyInstaller spec file for AI Data Analyst desktop app
# Build with:  pyinstaller build.spec
#
# Produces:   dist/AIDataAnalyst/          (directory bundle)
#             dist/AIDataAnalyst.exe       (Windows)
#             dist/AIDataAnalyst.app       (macOS — then wrap in .dmg)

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_all

block_cipher = None

# Collect all streamlit resources (templates, static files, etc.)
streamlit_datas, streamlit_binaries, streamlit_hiddenimports = collect_all("streamlit")

# Other package data
altair_datas,   _, altair_hidden   = collect_all("altair")
plotly_datas,   _, plotly_hidden   = collect_all("plotly")
pyarrow_datas,  _, pyarrow_hidden  = collect_all("pyarrow")
pandas_datas,   _, pandas_hidden   = collect_all("pandas")
pydeck_datas,   _, pydeck_hidden   = collect_all("pydeck")

all_datas = (
    streamlit_datas + altair_datas + plotly_datas +
    pyarrow_datas + pandas_datas + pydeck_datas +
    # Bundle app source files
    [("app.py",            "."),
     ("analyst.py",        "."),
     ("bedrock_client.py", "."),
     ("model_discovery.py","."),
     ("vector_store.py",   "."),
     ("db_base.py",        "."),
     ("fabric_client.py",  "."),
     ("snowflake_client.py","."),
     ("postgres_client.py","."),
     ("mysql_client.py",   "."),
     ("config.py",         ".")]
)

all_hidden = (
    streamlit_hiddenimports + altair_hidden + plotly_hidden +
    pyarrow_hidden + pandas_hidden + pydeck_hidden + [
        # DB connectors
        "psycopg2",
        "psycopg2.extras",
        "snowflake.connector",
        "snowflake.connector.pandas_tools",
        "mysql.connector",
        "pyodbc",
        # AWS
        "boto3",
        "botocore",
        "botocore.exceptions",
        "botocore.auth",
        "botocore.awsrequest",
        # Vector / ML
        "pgvector",
        "numpy",
        # Misc streamlit deps
        "tornado",
        "tornado.websocket",
        "click",
        "rich",
        "toml",
        "validators",
        "packaging",
        "importlib_metadata",
        "watchdog",
        "gitpython",
        "pydantic",
        "google.protobuf",
        "tzlocal",
        "tzdata",
        "pyarrow.vendored",
        # Webview
        "webview",
    ]
)

a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=streamlit_binaries,
    datas=all_datas,
    hiddenimports=all_hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "test", "unittest", "distutils"],
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
    name="AIDataAnalyst",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # no terminal window
    icon="assets/icon.ico" if sys.platform == "win32" else "assets/icon.icns",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AIDataAnalyst",
)

# macOS .app bundle
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="AIDataAnalyst.app",
        icon="assets/icon.icns",
        bundle_identifier="ai.lakefront.dataanalyst",
        info_plist={
            "NSPrincipalClass": "NSApplication",
            "NSHighResolutionCapable": True,
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleName": "AI Data Analyst",
        },
    )
