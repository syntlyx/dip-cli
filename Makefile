.PHONY: help build clean dev-install dev-run
# install

BINARY_NAME = dip
DIST_DIR = dist

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build the binary using shiv
	@echo "Building $(BINARY_NAME)..."
	@./scripts/build.sh

clean: ## Clean build artifacts and virtual environment
	@echo "Cleaning build artifacts..."
	@rm -rf build dist .venv src/*.egg-info *.egg-info
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo "Clean complete."

dev-install: ## Install in development mode
	@echo "Setting up development environment..."
	@python3 -m venv .venv
	@.venv/bin/pip install --upgrade pip wheel setuptools
	@.venv/bin/pip install -e ".[dev]"
	@chmod +x scripts/build.sh
	@chmod +x scripts/release.sh
	@chmod +x scripts/test-workflow.sh
	@echo "Development environment ready. Activate with: source .venv/bin/activate"

dev-run: ## Run the script directly (development mode)
	@python3 src/dip/__init__.py

# TODO: Add install for local devs
#install: build ## Install the binary to /usr/local/bin (requires sudo)
#	@echo "Installing $(BINARY_NAME) to /usr/local/bin..."
#	@sudo cp $(DIST_DIR)/$(BINARY_NAME) /usr/local/bin/
#	@sudo chmod +x /usr/local/bin/$(BINARY_NAME)
#	@echo "Installation complete. Run '$(BINARY_NAME)' from anywhere."
