# DIP CLI

> A Python-based PROTOTYPE tool for simplifying Docker development workflows

[![Builds](https://github.com/syntlyx/dip-cli/actions/workflows/build-and-release.yml/badge.svg)](https://github.com/syntlyx/dip-cli/actions/workflows/build-and-release.yml)
[![Latest Release](https://img.shields.io/github/v/release/syntlyx/dip-cli)](https://github.com/syntlyx/dip-cli/releases/latest)
[![License](https://img.shields.io/github/license/syntlyx/dip-cli)](LICENSE.md)

**⚠️ Warning**: This is a prototype implemented for personal and educational use-case. Use at your own risk! 

## Features

- 📦 Single binary distribution with [shiv](https://github.com/linkedin/shiv)
- ✨ Built with [Rich](https://github.com/Textualize/rich) for beautiful terminal output
- 🚀 Fast and lightweight
- 🔒 Secure with SHA256 checksums
- 🐍 Supports Python 3.12+

## Installation

### Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/syntlyx/dip-cli/main/scripts/install.sh | bash
```

### From Source

```bash
git clone https://github.com/syntlyx/dip-cli.git
cd dip-cli
make install
```

## Usage

```bash
# Show help
dip --help

# Show version
dip --version

# Run commands
dip sysinfo
dip start
dip stop
dip restart
dip logs [container name]
dip build
dip shell --type=bash
dip bash # Alias for shell --type=bash
dip exec [custom command]
```

### Generate CA Certificate

To generate certificate for the traefik proxy:

```bash
dip mkcert --help

# Generate certificate for you domain
dip mkcert *.your-domain.lan

# Install generated CA certificate on client devices (requires only the first time)

# Generate certificate for another domain
dip mkcert *.another-domain.lan
# No need to to install another certificate

# Get docker-compose config for your container
dip traefik-label --help

dip traefik-label myapp myapp.your-domain.lan
```

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/syntlyx/dip-cli.git
cd dip-cli

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
# Direct execution
python3 src/dip/__init__.py [arguments...]

# Using venv
source .venv/bin/activate
dip [arguments...]

# Installing local build
make install
```

## MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
