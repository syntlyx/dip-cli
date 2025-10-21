#!/usr/bin/env bash
# Installation script for dip CLI

set -euo pipefail

##
# Colors
##
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

##
# Version
##
VERSION="${DIP_VERSION:-latest}"
TARGET_PY="3.12"

##
# Repo info
##
REPO_OWNER="syntlyx"
REPO_NAME="dip-cli"


##
# Installation directories following XDG directory specifications
##
BIN_DIR="${HOME}/.local/bin"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/dip"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/dip"
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/dip"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_step() {
    echo -e "\n${BLUE}==>${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

##
# Detect OS and architecture
##
detect_platform() {
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH=$(uname -m)

    case "$OS" in
        linux*)
            OS_TYPE="linux"
            ;;
        darwin*)
            OS_TYPE="macos"
            # Detect ARM vs Intel
            if [ "$ARCH" = "arm64" ]; then
                ARCH_TYPE="arm64"
            else
                ARCH_TYPE="x86_64"
            fi
            ;;
        *)
            log_error "Unsupported OS: $OS"
            exit 1
            ;;
    esac

    log_info "${CYAN}Detected:${NC} $OS_TYPE ($ARCH)"
}

##
# Create directories
##
create_directories() {
    log_step "Creating directories"

    mkdir -p "$BIN_DIR"
    mkdir -p "$DATA_DIR"
    mkdir -p "$CACHE_DIR"
    mkdir -p "$CONFIG_DIR/traefik"
    mkdir -p "$CONFIG_DIR/templates"

    log_info "Directories created ✓"
}

##
# Download or copy binary
##
install_binary() {
    log_step "Installing ${CYAN}dip${NC} binary"

    if [ -f "dist/dip" ]; then
        # Local installation (building from source)
        log_info "Installing from local build"
        cp "dist/dip" "${BIN_DIR}/dip"
        chmod +x "${BIN_DIR}/dip"
    else
        # Download from GitHub releases
        log_info "Downloading from GitHub releases"

        # Compound target bin filename
        TARGET_NAME="dip-${OS_TYPE}"
        if [ "$OS_TYPE" = "macos" ]; then
            TARGET_NAME="${TARGET_NAME}-${ARCH_TYPE}"
        fi
        TARGET_NAME="${TARGET_NAME}-py${TARGET_PY}"

        if [ "$VERSION" = "latest" ]; then
            DOWNLOAD_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}/releases/latest/download/${TARGET_NAME}"
        else
            DOWNLOAD_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}/releases/download/v${VERSION}/${TARGET_NAME}"
        fi

        log_info "Downloading: $DOWNLOAD_URL"

        TEMP_FILE=$(mktemp)
        if command -v curl &> /dev/null; then
            curl -fsSL "$DOWNLOAD_URL" -o "$TEMP_FILE"
        elif command -v wget &> /dev/null; then
            wget -q "$DOWNLOAD_URL" -O "$TEMP_FILE"
        else
            log_error "Neither curl nor wget found. Please install one."
            exit 1
        fi

        mv "$TEMP_FILE" "${BIN_DIR}/dip"
        chmod +x "${BIN_DIR}/dip"
    fi

    log_info "Binary installed ✓"
}

##
# Install configuration files
##
install_configs() {
    log_step "Installing configuration files"

    cat > /tmp/traefik-compose.yml << 'EOF'
services:
  traefik:
    image: traefik:v3
    container_name: traefik
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
    networks:
      - traefik_proxy
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"
    volumes:
      - /etc/localtime:/etc/localtime:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./traefik.yml:/traefik.yml:ro
      - ./certs:/certs:ro
      - ./dynamic:/dynamic:ro
    labels:
      - "traefik.enable=true"

networks:
  traefik_proxy:
    external: true

EOF

    # Create traefik.yml
    cat > /tmp/traefik.yml << 'EOF'
api:
  dashboard: true

entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https
          permanent: true
    observability:
      accessLogs: false
      metrics: false
      tracing: false
  websecure:
    address: ":443"

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
    network: traefik_proxy
  file:
    directory: /dynamic
    watch: true

log:
  filePath: "/var/log/traefik.log"
  level: INFO

accessLog:
  filePath: "/var/log/traefik-access.log"
EOF

    # Create dynamic middlewares
    cat > /tmp/middlewares.yml << 'EOF'
http:
  middlewares:
    default-headers:
      headers:
        frameDeny: true
        browserXssFilter: true
        contentTypeNosniff: true

    secure-headers:
      headers:
        sslRedirect: true
        stsSeconds: 31536000
        stsIncludeSubdomains: true
        stsPreload: true
EOF

    # Copy config files
    mkdir -p "${CONFIG_DIR}/traefik/dynamic"
    cp /tmp/traefik-compose.yml "${CONFIG_DIR}/traefik/docker-compose.yml"
    cp /tmp/traefik.yml "${CONFIG_DIR}/traefik/traefik.yml"
    cp /tmp/middlewares.yml "${CONFIG_DIR}/traefik/dynamic/middlewares.yml"

    # Clean up temp files
    rm -f /tmp/traefik-compose.yml /tmp/traefik.yml /tmp/middlewares.yml

    log_info "Configuration files installed ✓"
}

##
# Update PATH if needed
##
update_path() {
    # Check if BIN_DIR is in PATH
    if ! [[ "${PATH//\~/$HOME}" == *"$BIN_DIR"* ]]; then
        log_step "Updating PATH"

        SHELL_NAME=$(basename "$SHELL")
        case "$SHELL_NAME" in
            bash)
                RC_FILE="$HOME/.bashrc"
                ;;
            zsh)
                RC_FILE="$HOME/.zshrc"
                ;;
            fish)
                RC_FILE="$HOME/.config/fish/config.fish"
                ;;
            *)
                RC_FILE="$HOME/.profile"
                ;;
        esac

        if [ ! -f "$RC_FILE" ]; then
            touch "$RC_FILE"
        fi

        echo "" >> "$RC_FILE"
        echo "# Added by dip installer" >> "$RC_FILE"
        echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$RC_FILE"

        log_info "Added ${CYAN}${BIN_DIR}${NC} to ${CYAN}PATH${NC} in ${RC_FILE}"
        log_warn "Please restart your shell or run: ${CYAN}source ${RC_FILE}${NC}"
    fi
}

##
# Save version info
##
save_version() {
    VERSION_FILE="$CONFIG_DIR/version"
    INSTALLED_VERSION=$("${BIN_DIR}/dip" --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z]+\.[0-9]+)?' || echo "unknown")

    echo "$INSTALLED_VERSION" > "$VERSION_FILE"

    log_info "Installed version: ${CYAN}${INSTALLED_VERSION}${NC}"
}

##
# Verify installation
##
verify_installation() {
    log_step "Verifying installation"

#    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
#        export PATH="$BIN_DIR:$PATH"
#    fi

    if command -v "$BIN_DIR/dip" &> /dev/null; then
        log_info "${GREEN}dip command found ✓${NC}"
        eval "$BIN_DIR/dip --version"
    else
        log_warn "${CYAN}dip${NC} command not found in ${CYAN}PATH${NC}"
        log_info "Binary location: ${BIN_DIR}/dip"
    fi

    log_info "Configuration: $CONFIG_DIR"
}

##
# Show usage instructions
##
show_instructions() {
    echo -e ""
    echo -e "======================================"
    echo -e "    ${GREEN}Installation Complete!${NC}"
    echo -e "======================================"
    echo -e ""
    echo -e "${CYAN}Installed files:${NC}"
    echo -e "  Binary:      ${BIN_DIR}/dip"
    echo -e "  Config:      $CONFIG_DIR"
    echo -e ""

    if ! [[ "${PATH//\~/$HOME}" == *"$BIN_DIR"* ]]; then
        echo -e "⚠️  ${YELLOW}Please restart your shell or run:${NC} ${CYAN}source ~/.$(basename $SHELL)rc${NC}"
        echo -e ""
    fi

    echo "Get started:"
    echo "  dip --help"
    echo ""
#    echo "Traefik setup:"
#    echo "  cd $CONFIG_DIR/traefik"
#    echo "  docker network create traefik_proxy"
#    echo "  docker-compose up -d"
#    echo ""
    echo "======================================"
}

##
# Show usage
##
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Install dip CLI tool with configuration files.

OPTIONS:
    -h, --help          Show this help message
    -v, --version VER   Install specific version (default: latest)
    --uninstall         Uninstall dip

EXAMPLES:
    # User installation (recommended)
    $0

    # Install specific version
    $0 --version 1.2.3

    # Uninstall
    $0 --uninstall

EOF
}

##
# Uninstall function
##
uninstall() {
    log_step "Uninstalling ${CYAN}dip${NC}"

    log_info "Removed directories and files:"

    rm -f "${BIN_DIR}/dip"
    log_info "  ${CYAN}Binary:${NC}  ${BIN_DIR}/dip"

    rm -rf "$CONFIG_DIR"
    log_info "  ${CYAN}Config:${NC}  $CONFIG_DIR"

    rm -rf "$DATA_DIR"
    log_info "  ${CYAN}Data:${NC}    $DATA_DIR"

    rm -rf "$CACHE_DIR"
    log_info "  ${CYAN}Cache:${NC}   $CACHE_DIR"

    log_info "${GREEN}dip uninstalled successfully${NC}"
    exit 0
}

##
# Parse arguments
##
UNINSTALL=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        --uninstall)
            UNINSTALL=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

##
# Main installation
##
main() {
    if [ "$UNINSTALL" = true ]; then
        uninstall
    fi

    log_step "Starting ${CYAN}dip${NC} installation"

    detect_platform

    log_info "${CYAN}Installation directories:${NC}"
    log_info "  Binary:  $BIN_DIR"
    log_info "  Config:  $CONFIG_DIR"
    log_info "  Data:    $DATA_DIR"

    create_directories
    install_binary
    install_configs
    update_path
    save_version
    verify_installation
    show_instructions
}

##
# Invoke main
##
main "$@"
