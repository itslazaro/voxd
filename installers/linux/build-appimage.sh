#!/usr/bin/env bash
# Build a VOXD AppImage using linuxdeploy + AppDir layout.
# Downloads linuxdeploy if not present. Run from CI or a Linux host.
# Usage: bash installers/linux/build-appimage.sh [version]
set -euo pipefail

cd "$(dirname "$0")/../.."
VERSION="${1:-1.0.0}"
ARCH="x86_64"
APPIMAGE="build/VOXD-${VERSION}-${ARCH}.AppImage"

TOOLS="build/tools"
mkdir -p "$TOOLS"

LDDEPLOY_BIN="$TOOLS/linuxdeploy-x86_64.AppImage"
APPDIR="build/AppDir"

if [ ! -f "$LDDEPLOY_BIN" ]; then
  echo "Downloading linuxdeploy..."
  curl -L -o "$LDDEPLOY_BIN" \
    "https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage"
  chmod +x "$LDDEPLOY_BIN"
fi

echo "Preparing AppDir..."
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" \
         "$APPDIR/usr/share/icons/hicolor/scalable/apps" \
         "$APPDIR/usr/lib/voxd"

# Payload
cp -r app "$APPDIR/usr/lib/voxd/app"
cp -r assets "$APPDIR/usr/lib/voxd/assets"
cp config/default.yaml "$APPDIR/usr/lib/voxd/config-default.yaml"
cp scripts/setup_whisper.py "$APPDIR/usr/lib/voxd/setup_whisper.py"

cat > "$APPDIR/usr/bin/voxd" <<EOF
#!/usr/bin/env bash
export VOXD_APP_DIR="\$(dirname "\$(readlink -f "\${BASH_SOURCE[0]}")")/../lib/voxd"
export PYTHONPATH="\$VOXD_APP_DIR"
exec python3 -m app.main "\$@"
EOF
chmod 755 "$APPDIR/usr/bin/voxd"

cat > "$APPDIR/usr/share/applications/voxd.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=VOXD
Comment=Local-first AI voice dictation
Exec=voxd gui
Icon=voxd
Terminal=false
Categories=Audio;Utility;
StartupNotify=true
EOF
cp assets/icons/voxd.svg "$APPDIR/usr/share/icons/hicolor/scalable/apps/voxd.svg"

cat > "$APPDIR/AppRun" <<'EOF'
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "$0")")"
export VOXD_APP_DIR="$HERE/usr/lib/voxd"
export PYTHONPATH="$VOXD_APP_DIR"
export LD_LIBRARY_PATH="$HERE/usr/lib:$HERE/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"
exec python3 -m app.main "$@"
EOF
chmod 755 "$APPDIR/AppRun"

echo "Running linuxdeploy..."
"$LDDEPLOY_BIN" --appdir "$APPDIR" \
  --desktop-file "$APPDIR/usr/share/applications/voxd.desktop" \
  --icon-file "$APPDIR/usr/share/icons/hicolor/scalable/apps/voxd.svg" \
  --output appimage
echo "Built $APPIMAGE"
