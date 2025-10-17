#!/usr/bin/env bash
set -euo pipefail

source "./scripts/utils/logging.sh"

##
# Configuration
##
PYTHON="${PYTHON:-python3}"
VENV_DIR=".venv"
BUILD_DIR="build"
DIST_DIR="dist"
SCRIPT_NAME="dip"
ENTRY_POINT="dip:main"
SOURCE_DIR="src"

##
# Cleanup function
##
cleanup() {
    if [ -n "${TEMP_BUILD_DIR:-}" ] && [ -d "$TEMP_BUILD_DIR" ]; then
        rm -rf "$TEMP_BUILD_DIR"
    fi
}

trap cleanup EXIT

##
# Check if Python is available
##
check_python() {
    if ! command -v "$PYTHON" &> /dev/null; then
        error_exit "Python not found. Please install Python 3.8 or higher."
    fi

    PYTHON_VERSION=$($PYTHON --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
        error_exit "Python 3.8 or higher is required. Found: $PYTHON_VERSION"
    fi

    log_info "Using Python $PYTHON_VERSION"
}

##
# Check if pyproject.toml exists
##
check_project_file() {
    if [ ! -f "pyproject.toml" ]; then
        error_exit "pyproject.toml not found. Are you in the project root?"
    fi
}

##
# Check if source directory exists
##
check_source_dir() {
    if [ ! -d "$SOURCE_DIR" ]; then
        error_exit "Source directory '$SOURCE_DIR' not found."
    fi
}

##
# Parse runtime dependencies from pyproject.toml
##
get_runtime_dependencies() {
    if command -v python3 &> /dev/null; then
        python3 -c "
import tomllib
with open('pyproject.toml', 'rb') as f:
    data = tomllib.load(f)
    deps = data.get('project', {}).get('dependencies', [])
    for dep in deps:
        print(dep)
" 2>/dev/null || echo "rich"
    else
        # Fallback if tomllib not available (Python < 3.11)
        grep -A 10 '^\[project\]' pyproject.toml | \
            grep -A 10 'dependencies' | \
            grep '"' | \
            sed 's/.*"\(.*\)".*/\1/' || echo "rich"
    fi
}

##
# Main build process
##
main() {
    log_step "Starting build process..."

    check_python
    check_project_file
    check_source_dir

    log_step "Cleaning previous builds"
    rm -rf "$BUILD_DIR" "$DIST_DIR"
    mkdir -p "$DIST_DIR"
    log_info "Cleaned $BUILD_DIR and $DIST_DIR directories"

    log_step "Setting up virtual environment"
    if [ -d "$VENV_DIR" ]; then
        log_warn "Virtual environment exists at $VENV_DIR"
        log_info "Recreating for clean build..."
        rm -rf "$VENV_DIR"
    fi

    log_info "Creating virtual environment..."
    $PYTHON -m venv "$VENV_DIR" || error_exit "Failed to create virtual environment"

    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate" || error_exit "Failed to activate virtual environment"

    log_step "Upgrading pip and build tools"
    pip install --quiet --upgrade pip wheel setuptools || error_exit "Failed to upgrade pip"
    log_info "pip version: $(pip --version)"

    log_step "Installing project dependencies"
    pip install --quiet -e ".[dev]" || error_exit "Failed to install project dependencies"

    if ! command -v shiv &> /dev/null; then
        error_exit "shiv not found after installation"
    fi
    log_info "shiv version: $(shiv --version)"

    log_step "Preparing build environment"
    TEMP_BUILD_DIR=$(mktemp -d) || error_exit "Failed to create temporary directory"
    log_info "Temporary build directory: $TEMP_BUILD_DIR"

    log_info "Detecting runtime dependencies..."
    RUNTIME_DEPS=$(get_runtime_dependencies)
    log_info "Runtime dependencies: $RUNTIME_DEPS"

    log_step "Installing runtime dependencies for packaging"
    if [ -n "$RUNTIME_DEPS" ]; then
        # shellcheck disable=SC2086
        pip install --target "$TEMP_BUILD_DIR" $RUNTIME_DEPS || \
            error_exit "Failed to install runtime dependencies"
    else
        log_warn "No runtime dependencies found"
    fi

    log_step "Copying source files"
    if [ -d "$SOURCE_DIR" ]; then
        cp -r "$SOURCE_DIR"/* "$TEMP_BUILD_DIR/" || error_exit "Failed to copy source files"
        log_info "Copied files from $SOURCE_DIR to build directory"
    else
        error_exit "Source directory $SOURCE_DIR not found"
    fi

    log_step "Building shiv binary"
    shiv \
        --site-packages "$TEMP_BUILD_DIR" \
        --compressed \
        --entry-point "$ENTRY_POINT" \
        --output-file "$DIST_DIR/$SCRIPT_NAME" \
        --python "/usr/bin/env python3" \
        --reproducible || error_exit "shiv build failed"

    chmod +x "$DIST_DIR/$SCRIPT_NAME"

    BINARY_SIZE=$(du -h "$DIST_DIR/$SCRIPT_NAME" | cut -f1)
    BINARY_MD5=$(md5sum "$DIST_DIR/$SCRIPT_NAME" 2>/dev/null | cut -d' ' -f1 || md5 -q "$DIST_DIR/$SCRIPT_NAME" 2>/dev/null)

    log_info "Build complete!"
    log_info "Binary location: $DIST_DIR/$SCRIPT_NAME"
    log_info "Binary size: $BINARY_SIZE"
    [ -n "$BINARY_MD5" ] && log_info "MD5 checksum: $BINARY_MD5"

    log_step "Testing binary"
    if "$DIST_DIR/$SCRIPT_NAME" --help &> /dev/null; then
        log_info "Binary test: ${GREEN}✓ PASSED${NC}"
    else
        log_error "Binary test: ${RED}✗ FAILED${NC}"
        log_error "The binary was created but the --help test failed"
        exit 1
    fi

    echo ""
    echo "======================================"
    echo "         Build Summary"
    echo "======================================"
    echo "Binary:     $DIST_DIR/$SCRIPT_NAME"
    echo "Size:       $BINARY_SIZE"
    echo "Python:     $PYTHON_VERSION"
    echo "Entry:      $ENTRY_POINT"
    [ -n "$BINARY_MD5" ] && echo "MD5:        $BINARY_MD5"
    echo "======================================"
    echo ""
    log_info "Run the binary with: ./$DIST_DIR/$SCRIPT_NAME"
}

##
# Invoke main
##
main "$@"
