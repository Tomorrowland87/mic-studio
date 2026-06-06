#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Detect distribution
DISTRO=""
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO="$ID"
fi

echo "=== MicStudio Installer ==="
echo "Detected: $DISTRO"
echo ""

install_pkg() {
    case "$DISTRO" in
        arch|cachyos|endeavouros|manjaro|artix)
            sudo pacman -S --noconfirm "$@"
            ;;
        ubuntu|debian|linuxmint|pop|elementary|zorin)
            sudo apt update && sudo apt install -y "$@"
            ;;
        fedora)
            sudo dnf install -y "$@"
            ;;
        opensuse*)
            sudo zypper install -y "$@"
            ;;
        *)
            echo "Unknown distro. Please install manually: $*"
            ;;
    esac
}

pkg_exists() {
    case "$DISTRO" in
        arch|cachyos|endeavouros|manjaro|artix)
            pacman -Qi "$1" &>/dev/null
            ;;
        ubuntu|debian|linuxmint|pop|elementary|zorin)
            dpkg -l "$1" 2>/dev/null | grep -q "^ii"
            ;;
        fedora)
            rpm -q "$1" &>/dev/null
            ;;
        opensuse*)
            rpm -q "$1" &>/dev/null
            ;;
        *)
            return 1
            ;;
    esac
}

echo "[1/5] Checking system dependencies..."

case "$DISTRO" in
    arch|cachyos|endeavouros|manjaro|artix)
        PKGS=(pipewire pipewire-pulse easyeffects python-pyqt6 python-dbus)
        PM="pacman"
        ;;
    ubuntu|debian|linuxmint|pop|elementary|zorin)
        PKGS=(pipewire pipewire-pulse easyeffects python3-pyqt6 python3-dbus)
        PM="apt"
        ;;
    fedora)
        PKGS=(pipewire pipewire-pulse easyeffects python3-qt6 python3-dbus)
        PM="dnf"
        ;;
    opensuse*)
        PKGS=(pipewire pipewire-pulse easyeffects python3-qt6 python3-dbus)
        PM="zypper"
        ;;
    *)
        echo "Unsupported distribution: $DISTRO"
        echo "Please install manually: pipewire, pipewire-pulse, easyeffects, python3-pyqt6, python3-dbus"
        PKGS=()
        PM=""
        ;;
esac

missing=()
for pkg in "${PKGS[@]}"; do
    if ! pkg_exists "$pkg"; then
        missing+=("$pkg")
    fi
done

if [ ${#missing[@]} -gt 0 ]; then
    echo "Missing packages: ${missing[*]}"
    echo "Installing via $PM..."
    install_pkg "${missing[@]}"
else
    echo "All dependencies satisfied."
fi

INSTALL_DIR="$HOME/.local/share/mic-studio"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
AUTOSTART_DIR="$HOME/.config/autostart"

echo "[2/5] Installing MicStudio to $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
rm -rf "$INSTALL_DIR/presets" "$INSTALL_DIR/src" "$INSTALL_DIR/engine.py" 2>/dev/null
cp -r "$SCRIPT_DIR/presets" "$INSTALL_DIR/"
cp -r "$SCRIPT_DIR/src" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/engine.py" "$INSTALL_DIR/"

echo "[3/5] Creating launcher"
mkdir -p "$BIN_DIR"

cat > "$BIN_DIR/mic-studio" << 'LAUNCHER'
#!/usr/bin/env bash
DIR="$HOME/.local/share/mic-studio"
cd "$DIR"
exec python3 "$DIR/src/main.py"
LAUNCHER
chmod +x "$BIN_DIR/mic-studio"

echo "[4/5] Creating desktop entry"
mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_DIR/mic-studio.desktop" << DESKTOP
[Desktop Entry]
Name=MicStudio
Comment=MicStudio — Microphone Audio Processor
Exec=$BIN_DIR/mic-studio
Icon=audio-input-microphone
Terminal=false
Type=Application
Categories=Audio;AudioVideo;
DESKTOP

echo "[5/5] Configuring EasyEffects autostart"
mkdir -p "$AUTOSTART_DIR"
cat > "$AUTOSTART_DIR/com.github.wwmm.easyeffects.desktop" << EEAS
[Desktop Entry]
Name=Easy Effects
Comment=Easy Effects Service
Exec=easyeffects --hide-window
Icon=com.github.wwmm.easyeffects
StartupNotify=false
Terminal=false
Type=Application
X-GNOME-Autostart-Phase=Application
X-KDE-autostart-phase=2
EEAS

echo ""
echo "=== Installation complete! ==="
echo ""
echo "Run: mic-studio"
echo ""
echo "In Discord / games select: Easy Effects Source"
echo ""
