#!/usr/bin/env bash
# Build a VOXD .deb package.
# Usage: bash installers/linux/build-deb.sh [version]
set -euo pipefail

cd "$(dirname "$0")/../.."
VERSION="${1:-1.0.0}"
PKG="voxd"
ARCH="amd64"

STAGE="build/deb-stage"
rm -rf "$STAGE" "build/${PKG}_${VERSION}_${ARCH}.deb"
mkdir -p "$STAGE/DEBIAN" "$STAGE/usr/bin" "$STAGE/usr/share/applications" \
         "$STAGE/usr/share/icons/hicolor/scalable/apps" \
         "$STAGE/usr/share/${PKG}" "$STAGE/etc/${PKG}"

# --- control file ---
cat > "$STAGE/DEBIAN/control" <<EOF
Package: $PKG
Version: $VERSION
Section: sound
Priority: optional
Architecture: $ARCH
Depends: python3 (>= 3.10), python3-numpy, python3-pip, ydotool, libportaudio2
Maintainer: VOXD contributors <dev@voxd.local>
Description: Local-first AI voice dictation
 Hold a key, speak, and VOXD transcribes your words locally with
 Whisper and types them into any application. Audio never leaves
 your machine.
EOF

cat > "$STAGE/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
echo "VOXD installed. Run 'voxd setup' to build whisper.cpp and download a model."
# Enable GNOME keybinding for dictation toggle.
gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings \
  "['/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/voxd/']" 2>/dev/null || true
exit 0
EOF
chmod 755 "$STAGE/DEBIAN/postinst"

cat > "$STAGE/DEBIAN/prerm" <<'EOF'
#!/bin/sh
set -e
systemctl --user stop voxd.service 2>/dev/null || true
exit 0
EOF
chmod 755 "$STAGE/DEBIAN/prerm"

# --- binary launcher ---
cat > "$STAGE/usr/bin/voxd" <<'EOF'
#!/usr/bin/env bash
exec /usr/share/voxd/venv/bin/python -m app.main "$@"
EOF
chmod 755 "$STAGE/usr/bin/voxd"

# --- desktop entry ---
cat > "$STAGE/usr/share/applications/voxd.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=VOXD
Comment=Local-first AI voice dictation
Exec=voxd gui
Icon=voxd
Terminal=false
Categories=Audio;Utility;
StartupNotify=true
X-GNOME-Autostart-enabled=true
EOF

# --- icon ---
cp assets/icons/voxd.svg "$STAGE/usr/share/icons/hicolor/scalable/apps/voxd.svg"

# --- systemd user service ---
cat > "$STAGE/usr/share/voxd/voxd.service" <<'EOF'
[Unit]
Description=VOXD dictation daemon
After=graphical-session.target

[Service]
Type=simple
ExecStart=/usr/bin/voxd daemon
Restart=on-failure

[Install]
WantedBy=default.target
EOF

# --- app payload ---
cp -r app "$STAGE/usr/share/voxd/app"
cp -r assets "$STAGE/usr/share/voxd/assets"
mkdir -p "$STAGE/usr/share/voxd/config"
cp config/default.yaml "$STAGE/usr/share/voxd/config/default.yaml"
mkdir -p "$STAGE/usr/share/voxd/scripts"
cp scripts/__init__.py "$STAGE/usr/share/voxd/scripts/__init__.py" 2>/dev/null || true
cp scripts/setup_whisper.py "$STAGE/usr/share/voxd/scripts/setup_whisper.py"
cp config/default.yaml "$STAGE/etc/voxd/default.yaml"

# --- build python venv into the package ---
python3 -m venv "$STAGE/usr/share/voxd/venv"
"$STAGE/usr/share/voxd/venv/bin/pip" install --quiet --upgrade pip
"$STAGE/usr/share/voxd/venv/bin/pip" install --quiet \
    numpy sounddevice PySide6 PyYAML pynput

dpkg-deb --build --root-owner-group "$STAGE" "build/${PKG}_${VERSION}_${ARCH}.deb"
echo "Built build/${PKG}_${VERSION}_${ARCH}.deb"
