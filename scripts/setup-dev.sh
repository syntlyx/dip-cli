#!/usr/bin/env bash
# Development environment setup script

set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
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

echo "🚀 Setting up development environment for dip CLI"

# Check Python
log_step "Checking Python installation"
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
log_info "Found Python $PYTHON_VERSION ✓"

# Check Make
log_step "Checking build tools"
if ! command -v make &> /dev/null; then
    log_warn "Make not found. Install it for easier development workflow."
    USE_MAKE=false
else
    log_info "Make found ✓"
    USE_MAKE=true
fi

# Make scripts executable
log_step "Making scripts executable"
chmod +x build.sh
if [ -f "scripts/release.sh" ]; then
    chmod +x scripts/release.sh
fi
log_info "Scripts are executable ✓"

# Set up Git hooks
log_step "Setting up Git hooks"
if [ -d ".git" ]; then
    mkdir -p .git/hooks

    if [ -f ".github/hooks/pre-push" ]; then
        cp .github/hooks/pre-push .git/hooks/pre-push
        chmod +x .git/hooks/pre-push
        log_info "Pre-push hook installed ✓"
    fi
else
    log_warn "Not a Git repository, skipping Git hooks"
fi

# Create virtual environment
log_step "Creating virtual environment"
if [ -d ".venv" ]; then
    log_warn "Virtual environment already exists"
    read -p "Recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf .venv
    else
        log_info "Keeping existing virtual environment"
    fi
fi

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    log_info "Virtual environment created ✓"
fi

# Activate and install dependencies
log_step "Installing dependencies"
source .venv/bin/activate
pip install --quiet --upgrade pip wheel setuptools
pip install --quiet -e ".[dev]"
log_info "Dependencies installed ✓"

# Verify installation
log_step "Verifying installation"
if command -v dip &> /dev/null; then
    log_info "dip command available ✓"
    dip --version
else
    log_warn "dip command not found. Activate venv: source .venv/bin/activate"
fi

if command -v shiv &> /dev/null; then
    log_info "shiv found ✓"
else
    log_warn "shiv not found"
fi

# Build once to verify
log_step "Running initial build"
if ./build.sh; then
    log_info "Initial build successful ✓"
else
    echo "❌ Initial build failed"
    exit 1
fi

# Summary
echo ""
echo "======================================"
echo "   Development Environment Ready!"
echo "======================================"
echo ""
echo "Next steps:"
echo ""
echo "  1. Activate virtual environment:"
echo "     source .venv/bin/activate"
echo ""
echo "  2. Test the CLI:"
echo "     dip --help"
echo "     dip hello"
echo ""
echo "  3. Make changes to src/dip/__init__.py"
echo ""
echo "  4. Test your changes:"
echo "     dip <command>  # Changes are live!"
echo ""

if [ "$USE_MAKE" = true ]; then
    echo "  5. Build binary:"
    echo "     make build"
    echo ""
    echo "  6. Run tests:"
    echo "     make test"
    echo ""
    echo "Available make targets:"
    make help
else
    echo "  5. Build binary:"
    echo "     ./build.sh"
    echo ""
    echo "  6. Run tests:"
    echo "     ./dist/dip --help"
    echo "     ./dist/dip hello"
fi

echo ""
echo "======================================"
echo ""
log_info "Happy coding! 🎉"
