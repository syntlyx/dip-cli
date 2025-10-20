#!/usr/bin/env bash
# Development environment setup script

set -euo pipefail

source "./scripts/utils/logging.sh"

##
# Version
##
TARGET_PY="3.12"

echo "Setting up development environment"

log_step "Checking Python installation"
if ! command -v python3 &> /dev/null; then
    log_error "❌ Python 3 not found. Please install Python $TARGET_PY or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
log_info "Found Python $PYTHON_VERSION ✓"

log_step "Checking build tools"
if ! command -v make &> /dev/null; then
    log_error "❌ Make not found, install make to proceed with development workflow."
    exit 1
fi

#log_step "Setting up Git hooks"
#if [ -d ".git" ]; then
#    mkdir -p .git/hooks
#
#    if [ -f ".github/hooks/pre-push" ]; then
#        cp .github/hooks/pre-push .git/hooks/pre-push
#        chmod +x .git/hooks/pre-push
#        log_info "Pre-push hook installed ✓"
#    fi
#else
#    log_warn "Not a Git repository, skipping Git hooks"
#fi

log_step "Creating virtual environment"
python3 -m venv .venv
log_info "Virtual environment created ✓"

log_step "Installing dependencies"
source .venv/bin/activate
pip install --quiet --upgrade pip wheel setuptools
pip install --quiet -e ".[dev]"
log_info "Dependencies installed ✓"

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

log_info "Development Environment Ready!"
