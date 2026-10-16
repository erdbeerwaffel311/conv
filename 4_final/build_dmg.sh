#!/usr/bin/env bash
set -e
# Script to rebuild the standalone macOS .app and .dmg installer

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

echo "=== Erstelle Universal Media Converter DMG ==="

export PYINSTALLER_CONFIG_DIR="/tmp/pyinstaller_cache"

echo "1. Baue .app mit PyInstaller..."
.venv/bin/pyinstaller --noconfirm --distpath 4_final/dist --workpath 4_final/build 1_resources/UniversalMediaConverter.spec

echo "2. Bereite DMG-Staging vor..."
rm -rf 4_final/dmg_staging
mkdir -p 4_final/dmg_staging
cp -R "4_final/dist/Universal Media Converter.app" 4_final/dmg_staging/
ln -s /Applications 4_final/dmg_staging/Applications

echo "3. Erstelle UniversalMediaConverter.dmg..."
rm -f 4_final/UniversalMediaConverter.dmg
hdiutil create -srcfolder 4_final/dmg_staging -volname "Universal Media Converter" -format UDZO -ov 4_final/UniversalMediaConverter.dmg

rm -rf 4_final/dmg_staging

echo "=== Fertig! DMG liegt in: 4_final/UniversalMediaConverter.dmg ==="
