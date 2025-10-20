# Quick Reference

## 🛠️ Development Commands

```bash
# Setup (once)
make dev-install             # Setup dev environment
source .venv/bin/activate

# Development loop
dip sysinfo                  # Test (instant, no rebuild)
nano src/dip/__init__.py     # Edit code
dip sysinfo                  # Test again

make build                   # Build binary
make clean                   # Clean artifacts if necessary
```

## 🚀 Release Process

```bash
# 1. Update version
nano pyproject.toml           # Update version = "1.2.3"
nano src/dip/__init__.py      # Update __version__ = "1.2.3"

# 2. Commit
git add .
git commit -m "Bump version to 1.2.3"
git push origin main

# 3. Release
./scripts/release.sh         # Creates tag and triggers CI/CD
```

## 📦 Make Targets

```bash
make help                    # Show all targets
make build                   # Build binary
make clean                   # Clean artifacts
make dev-install             # Setup dev environment
make install                 # Install build on local machine
make uninstall               # Uninstall dip and all related files
```

## 🏷️ Version Tags

```bash
# Stable release
git tag -a v1.2.3 -m "Release 1.2.3"
git push origin v1.2.3

# Pre-release
git tag -a v1.3.0-beta.1 -m "Beta 1"
git push origin v1.3.0-beta.1

# Delete tag (if needed)
git tag -d v1.2.3
git push --delete origin v1.2.3
```

## 📝 File Locations

```
Key files:
├── src/dip/
│   ├── __init__.py             # Main source code
│   └── __main__.py             # Main export
├── scripts/
│   ├── build.sh                # Build script
│   ├── install.sh              # Downloads and install the latest version
│   ├── release.sh              # Creates and publishes release with the current version
│   ├── setup-dev.sh            # Development environment setup script
│   ├── test-workflow.sh        # Test Github Workflow locally
│   └── update.sh               # Downloads and install the latest version
├── Makefile                    # Development scripts orchestration
├── pyproject.toml              # Project config, version, deps
└── .github/workflows/          # CI/CD workflows
    ├── build-and-release.yml
    └── version-check.yml

Documentation:
├── README.md                   # User guide
├── RELEASING.md                # Release process
├── CHANGELOG.md                # Version history
└── QUICK_REFERENCE.md          # This file
```

## 🎬 GitHub Actions Testing

Helper utility script uses `act` to test Github Workflow locally.

Available platforms: `macos-latest`, `macos-14`, `ubuntu-latest`

```bash
# Helper script
./scripts/test-workflow.sh --platform macos-latest build                # Test build
./scripts/test-workflow.sh --platform ubuntu-latest -v build            # Verbose
./scripts/test-workflow.sh --platform macos-14 --dry-run build          # Dry run
./scripts/test-workflow.sh --platform ubuntu-latest --skip-check build  # Skip uncommitted check
```

## 🎯 Release Checklist

- [ ] Update version in `pyproject.toml`
- [ ] Update version in `src/dip/__init__.py`
- [ ] Update `CHANGELOG.md`
- [ ] Test locally
- [ ] Commit changes
- [ ] Push to main
- [ ] Run `./scripts/release.sh`
- [ ] Wait for CI/CD (watch GitHub Actions)
- [ ] Verify the release on GitHub
- [ ] Test released binary
- [ ] Announce release

## 🔗 Quick Links

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [Shiv Documentation](https://shiv.readthedocs.io/)
- [Rich Documentation](https://rich.readthedocs.io/)
