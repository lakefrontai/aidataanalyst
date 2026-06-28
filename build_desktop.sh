#!/usr/bin/env bash
# Local build script for the AI Data Analyst desktop app.
# Run from the repo root with the venv activated.
#
# Usage:
#   chmod +x build_desktop.sh
#   ./build_desktop.sh          # build for current platform
#   ./build_desktop.sh --dmg    # macOS: also wrap in .dmg (requires create-dmg)

set -e

echo "==> Installing build deps..."
pip install pyinstaller pywebview --quiet

echo "==> Cleaning previous build..."
rm -rf build dist

echo "==> Running PyInstaller..."
pyinstaller build.spec --noconfirm

echo "==> Build complete: dist/AIDataAnalyst/"

# macOS .dmg
if [[ "$1" == "--dmg" && "$(uname)" == "Darwin" ]]; then
    echo "==> Creating .dmg..."
    if ! command -v create-dmg &> /dev/null; then
        echo "  Installing create-dmg..."
        brew install create-dmg
    fi
    create-dmg \
        --volname "AI Data Analyst" \
        --window-size 600 400 \
        --icon-size 100 \
        --icon "AIDataAnalyst.app" 150 190 \
        --app-drop-link 450 190 \
        "dist/AIDataAnalyst.dmg" \
        "dist/AIDataAnalyst.app"
    echo "==> dist/AIDataAnalyst.dmg ready"
fi
