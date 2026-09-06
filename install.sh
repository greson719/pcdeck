#!/usr/bin/env bash
# ==============================================================================
# PCDeck Pro - Universal 1-Line Linux Installer & Launcher
# Usage: curl -sSL https://pcdeck.vercel.app/install.sh | bash
# ==============================================================================
set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}"
echo "  ██████╗  ██████╗██████╗ ███████╗ ██████╗██╗  ██╗"
echo "  ██╔══██╗██╔════╝██╔══██╗██╔════╝██╔════╝██║ ██╔╝"
echo "  ██████╔╝██║     ██║  ██║█████╗  ██║     █████╔╝ "
echo "  ██╔═══╝ ██║     ██║  ██║██╔══╝  ██║     ██╔═██╗ "
echo "  ██║     ╚██████╗██████╔╝███████╗╚██████╗██║  ██╗"
echo "  ╚═╝      ╚═════╝╚═════╝ ╚══════╝ ╚═════╝╚═╝  ╚═╝"
echo "  Wireless Trackpad, Keyboard & Screen for Linux  "
echo -e "${NC}"

APP_DIR="$HOME/.local/share/pcdeck"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$APP_DIR" "$BIN_DIR" "$DESKTOP_DIR"

echo -e "${GREEN}==>${NC} Installing PCDeck v2.7.0 for Linux..."

# Check Python 3
if command -v python3 &>/dev/null; then
    echo -e "${GREEN}==>${NC} Python 3 detected: $(python3 --version)"
else
    echo -e "${RED}❌ Python 3 not found.${NC} Please install python3 (e.g. sudo apt install python3 python3-pip python3-venv)"
    exit 1
fi

# Fetch or update PCDeck repository in ~/.local/share/pcdeck
if [ -d "$APP_DIR/.git" ]; then
    echo -e "${GREEN}==>${NC} Updating existing PCDeck installation..."
    (cd "$APP_DIR" && git pull --ff-only 2>/dev/null || true)
elif command -v git &>/dev/null; then
    echo -e "${GREEN}==>${NC} Cloning PCDeck repository..."
    git clone --depth 1 https://github.com/greson719/pcdeck.git "$APP_DIR"
else
    echo -e "${GREEN}==>${NC} Downloading PCDeck v2.7.0 package..."
    curl -fsSL https://github.com/greson719/pcdeck/archive/refs/heads/main.tar.gz | tar -xz -C "$APP_DIR" --strip-components=1
fi

chmod +x "$APP_DIR/run_linux.sh"

# Create launcher in ~/.local/bin
cat << 'EOF' > "$BIN_DIR/pcdeck"
#!/usr/bin/env bash
exec "$HOME/.local/share/pcdeck/run_linux.sh" "$@"
EOF
chmod +x "$BIN_DIR/pcdeck"

# Create Desktop entry
cat << EOF > "$DESKTOP_DIR/pcdeck.desktop"
[Desktop Entry]
Name=PCDeck
Comment=Wireless Trackpad, Keyboard & Screen Remote
Exec=$BIN_DIR/pcdeck
Icon=$APP_DIR/icon.png
Terminal=true
Type=Application
Categories=Utility;RemoteAccess;
EOF
chmod +x "$DESKTOP_DIR/pcdeck.desktop"

echo -e "${GREEN}✔ Installation complete!${NC}"
echo -e "You can start PCDeck anytime by typing: ${CYAN}pcdeck${NC}"
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo -e "${YELLOW}Note:${NC} Add ${CYAN}$BIN_DIR${NC} to your PATH if not already present:"
    echo -e "      export PATH=\"\$HOME/.local/bin:\$PATH\""
fi
echo ""
echo -e "${YELLOW}Starting PCDeck v2.7.0 now...${NC}"
exec "$BIN_DIR/pcdeck"
