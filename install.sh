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

INSTALL_DIR="$HOME/.local/bin"
mkdir -p "$INSTALL_DIR"

echo -e "${GREEN}==>${NC} Installing PCDeck for Linux..."

# Check Python 3 and dependencies
if command -v python3 &>/dev/null; then
    echo -e "${GREEN}==>${NC} Python 3 detected: $(python3 --version)"
fi

# If uv is installed, launch immediately with uv
if command -v uv &>/dev/null; then
    echo -e "${GREEN}==>${NC} Launching PCDeck via high-speed uv engine..."
    uvx --from git+https://github.com/greson719/pcdeck-pro.git pcdeck || true
    exit 0
fi

# Fallback: clone or run standalone
TARGET_BIN="$INSTALL_DIR/pcdeck"
echo -e "${GREEN}==>${NC} Downloading PCDeck standalone Linux launcher..."
curl -fsSL https://raw.githubusercontent.com/greson719/pcdeck-pro/main/run_linux.sh -o "$TARGET_BIN"
chmod +x "$TARGET_BIN"

echo -e "${GREEN}✔ Installation complete!${NC}"
echo -e "You can start PCDeck anytime by running: ${CYAN}$TARGET_BIN${NC}"
echo ""
echo -e "${YELLOW}Starting PCDeck now...${NC}"
"$TARGET_BIN"
