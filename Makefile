.PHONY: help build clean dev-install install uninstall

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build the binary
	@echo "Building dip..."
	@./scripts/build.sh

clean: ## Clean build artifacts and virtual environment
	@echo "Cleaning build artifacts..."
	@rm -rf build dist .venv src/*.egg-info *.egg-info
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo "Clean complete."

dev-install: ## Install in development mode
	@./scripts/setup-dev.sh

install: build ## Install tool
	@./scripts/install.sh

uninstall: ## Uninstall dip and related files
	@./scripts/install.sh --uninstall
