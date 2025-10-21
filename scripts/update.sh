#!/usr/bin/env bash
# Update script for dip CLI

set -euo pipefail


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

##
# Colors
##
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_step() {
    echo -e "\n${BLUE}==>${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

##
# Detect installation location
##
detect_installation() {
    if ! command -v dip &> /dev/null; then
        log_warn "dip not found. Please install first."
        echo "Run: curl -fsSL https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/main/scripts/install.sh | bash"
        exit 1
    fi
}

##
# Get current version
##
get_current_version() {
    CURRENT_VERSION=$(dip --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z]+\.[0-9]+)?' || echo "unknown")
    log_info "Current version: $CURRENT_VERSION"
}

##
# Get latest version from GitHub
##
get_latest_version() {
    log_step "Checking for updates"

    LATEST_VERSION=$(curl -fsSL "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/releases/latest" | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/')

    if [ -z "$LATEST_VERSION" ]; then
        log_warn "Could not fetch latest version"
        exit 1
    fi

    log_info "Latest version: $LATEST_VERSION"
}

##
# Compare versions
##
compare_versions() {
    if [ "$CURRENT_VERSION" = "$LATEST_VERSION" ]; then
        log_info "Already up to date! ✓"
        exit 0
    fi

    log_info "Update available: $CURRENT_VERSION → $LATEST_VERSION"
}

##
# Backup current installation
##
backup_current() {
    log_step "Creating backup"

    BACKUP_DIR="/tmp/dip-backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$BACKUP_DIR"

    cp -r "$CONFIG_DIR" "$BACKUP_DIR/dip"

    log_info "Backup created: $BACKUP_DIR/dip"
}

##
# Update binary
##
update_binary() {
    log_step "Updating dip binary"

    # Download installer
    curl -fsSL "https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/main/scripts/install.sh" -o /tmp/dip-install.sh
    chmod +x /tmp/dip-install.sh

    # Run installer
    /tmp/dip-install.sh --version "$LATEST_VERSION"

    rm -f /tmp/dip-install.sh

    log_info "Update complete ✓"
}

##
# Verify update
##
verify_update() {
    log_step "Verifying update"

    NEW_VERSION=$(dip --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z]+\.[0-9]+)?' || echo "unknown")

    if [ "$NEW_VERSION" = "$LATEST_VERSION" ]; then
        log_info "Successfully updated to v$NEW_VERSION ✓"
    else
        log_warn "Update verification failed"
        log_warn "Expected: $LATEST_VERSION, Got: $NEW_VERSION"
    fi
}

##
# Main update process
##
main() {
    log_step "Starting dip update"

    detect_installation
    get_current_version
    get_latest_version
    compare_versions
    backup_current
    update_binary
    verify_update

    echo ""
    echo "======================================"
    echo "    Update Complete!"
    echo "======================================"
    echo ""
    echo "  Old version: $CURRENT_VERSION"
    echo "  New version: $LATEST_VERSION"
    echo ""
    echo "Run: dip --version"
    echo ""
    echo "======================================"
}

##
# Invoke main
##
main "$@"
