# DIP CLI

> A Python-based PROTOTYPE tool for simplifying Docker development workflows

[![Build and Release](https://github.com/syntlyx/dip-cli/actions/workflows/build-and-release.yml/badge.svg)](https://github.com/syntlyx/dip-cli/actions/workflows/build-and-release.yml)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/syntlyx/dip-cli)](https://github.com/syntlyx/dip-cli/releases/latest)
[![License](https://img.shields.io/github/license/syntlyx/dip-cli)](LICENSE)

## Features

- ✨ Built with [Rich](https://github.com/Textualize/rich) for beautiful terminal output
- 📦 Single binary distribution with [shiv](https://github.com/linkedin/shiv)
- 🚀 Fast and lightweight
- 🔒 Secure with SHA256 checksums
- 🐍 Supports Python 3.9+

## Installation

### Quick Install (Recommended)

**Linux:**
```bash
curl -L https://github.com/syntlyx/dip-cli/releases/latest/download/dip-linux-py3.12 -o dip
chmod +x dip
sudo mv dip /usr/local/bin/
```

**macOS (Intel):**
```bash
curl -L https://github.com/syntlyx/dip-cli/releases/latest/download/dip-macos-x86_64-py3.12 -o dip
chmod +x dip
sudo mv dip /usr/local/bin/
```

**macOS (Apple Silicon):**
```bash
curl -L https://github.com/syntlyx/dip-cli/releases/latest/download/dip-macos-arm64-py3.12 -o dip
chmod +x dip
sudo mv dip /usr/local/bin/
```

### From Source

```bash
git clone https://github.com/syntlyx/dip-cli.git
cd dipcli
make install
```

## Usage

```bash
# Show help
dip --help

# Show version
dip --version

# Run commands
dip system
dip start
dip stop
dip restart
dip logs [container name]
dip build
dip shell --type=bash
dip bash # Alias for shell --type=bash
dip exec [custom command]
```

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/syntlyx/dip-cli.git
cd dipcli

# Set up development environment
make dev-install
source .venv/bin/activate
```

### Building

```bash
# Build binary
make build

# Clean build artifacts
make clean
```

### Testing During Development

```bash
# Quick test (no build needed)
make dev-run

# Or run directly
python3 src/dip/__init__.py [arguments...]

# With editable install (changes reflected immediately)
source .venv/bin/activate
dip [arguments...]
```

## Release Process

See [RELEASING.md](RELEASING.md) for detailed release instructions.

**Quick release:**
```bash
# 1. Update version in pyproject.toml
# 2. Commit changes
git add pyproject.toml src/dip/__init__.py
git commit -m "Bump version to 1.2.3"
git push origin main

# 3. Create release
./scripts/release.sh
```

## License

[MIT License](LICENSE)
