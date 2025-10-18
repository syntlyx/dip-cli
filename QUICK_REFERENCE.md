# Quick Reference

## 🚀 Release Process (TL;DR)

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

## 🛠️ Development Commands

```bash
# Setup (once)
make dev-install             # Setup dev environment
source .venv/bin/activate

# Development loop
dip system                   # Test (instant, no rebuild)
nano src/dip/__init__.py     # Edit code
dip system                   # Test again

# Build and test
make build                   # Build binary
make clean                   # Clean everything
```

## 📦 Make Targets

```bash
make help                    # Show all targets
make dev-install             # Setup dev environment
make build                   # Build binary
make clean                   # Clean artifacts
make install                 # Install to ~/.dip
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
├── pyproject.toml              # Project config, version, deps
├── src/dip/
│   ├── __init__.py             # Main source code
│   └── __main__.py             # Main export
├── scripts/
│   ├── build.sh                # Build script
│   ├── release.sh              # Creates and publishes release
│   └── test-workflow.sh        # Test Github Workflow locally
├── Makefile                    # Dev commands
└── .github/workflows/          # CI/CD workflows
    ├── build-and-release.yml
    └── version-check.yml

Documentation:
├── README.md                   # User guide
├── RELEASING.md                # Release process
├── CHANGELOG.md                # Version history
└── QUICK_REFERENCE.md          # This file
```

## 🎬 act Commands (Local GitHub Actions Testing)

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
