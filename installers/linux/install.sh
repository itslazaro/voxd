#!/usr/bin/env bash
# Install VOXD (Linux) from a source tree or packaged AppImage/deb.
# Usage: bash installers/linux/install.sh [--prefix /usr/local]
set -euo pipefail

PREFIX="${1:-/usr/local}"
cd "$(dirname "$0")/../.."

echo "==> VOXD Linux installer (prefix=$PREFIX)"

# 1. Install system deps
echo "==> Installing system dependencies"
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq ydotool python3 python3-venv python3-pip \
    portaudio19-dev libportaudio2 git cmake build-essential
elif command -v dnf >/dev/null 2>&1; then
  sudo dnf install -y ydotool python3 python3-virtualenv python3-pip \
    portaudio-devel git cmake gcc-c++ make
else
  echo "WARNING: unsupported package manager; install deps manually."
fi

# 2. Copy payload
echo "==> Installing VOXD to $PREFIX/share/voxd"
sudo install -d "$PREFIX/share/voxd"
sudo cp -r app "$PREFIX/share/voxd/app"
sudo cp -r assets "$PREFIX/share/voxd/assets"
sudo cp -r config "$PREFIX/share/voxd/config"
sudo cp -r scripts "$PREFIX/share/voxd/scripts"
sudo install -d "$PREFIX/bin"
sudo tee "$PREFIX/bin/voxd" >/dev/null <<EOF
#!/usr/bin/env bash
export PYTHONPATH="$PREFIX/share/voxd"
exec python3 -m app.main "\$@"
EOF
sudo chmod 755 "$PREFIX/bin/voxd"

# 3. Desktop entry + icon
echo "==> Installing desktop entry"
sudo install -d "$PREFIX/share/applications"
sudo cp installers/linux/voxd.desktop "$PREFIX/share/applications/voxd.desktop"
sudo install -d "$PREFIX/share/icons/hicolor/scalable/apps"
sudo cp assets/icons/voxd.svg "$PREFIX/share/icons/hicolor/scalable/apps/voxd.svg"

# 4. systemd user services
echo "==> Installing systemd user services"
install -d "$HOME/.config/systemd/user"
cp installers/linux/voxd.service "$HOME/.config/systemd/user/voxd.service"
cp installers/linux/ydotool.service "$HOME/.config/systemd/user/ydotool.service"
systemctl --user daemon-reload || true

# 5. GNOME keybinding
echo "==> Registering GNOME keybinding (Super+V)"
gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings \
  "['/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/voxd/']" 2>/dev/null || true
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/voxd/ name "VOXD Dictate" 2>/dev/null || true
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/voxd/ command "voxd --toggle" 2>/dev/null || true
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/voxd/ binding "<Super>v" 2>/dev/null || true

echo "==> Done. Next steps:"
echo "   1. voxd setup        # build whisper.cpp + download model"
echo "   2. systemctl --user enable --now ydotool voxd"
echo "   3. voxd gui"
