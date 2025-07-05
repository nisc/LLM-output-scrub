# Makefile for LLM Output Scrub project
#
# To use parallel builds (where supported):
#   make -j8 build    # Use 8 parallel jobs
#   make -j$(nproc) build  # Use all available cores

.PHONY: all test test-unit test-integration build clean clean-venv distclean run install uninstall tree setup

# Variables
VENV_PYTHON = .venv/bin/python
VENV_PIP = .venv/bin/pip
APP_NAME = LLM Output Scrub.app
APPS_DIR = /Applications

# Main targets
all: test-unit test build

# Initial setup - use this for first-time setup or when having issues
setup: clean-venv install-deps
	@echo "\nSetup complete! Virtual environment is ready."
	@echo "To activate: source .venv/bin/activate"
	@echo "To run the app: make run"

# Virtual environment management
venv:
	@echo "\nCreating virtual environment..."
	python3 -m venv .venv
	$(VENV_PYTHON) -m ensurepip --upgrade
	$(VENV_PIP) install --upgrade pip

# Install spaCy language model (shared function)
install-spacy-model:
	@echo "\nChecking spaCy language model..."
	@if $(VENV_PYTHON) -c "import spacy; nlp = spacy.load('en_core_web_sm'); \
		print('Model already installed')" 2>/dev/null; then \
		echo "spaCy model 'en_core_web_sm' is already installed."; \
	else \
		echo "Installing spaCy language model 'en_core_web_sm'..."; \
		$(VENV_PYTHON) -m spacy download en_core_web_sm; \
	fi

# Install dependencies (robust with fallbacks)
install-deps: venv
	@echo "\nInstalling dependencies..."
	@$(VENV_PIP) install --use-feature=fast-deps .[dev,build,macOS]
	@$(MAKE) install-spacy-model

# Install unit test dependencies only
install-unit-deps: venv
	@echo "\nInstalling unit test dependencies..."
	@$(VENV_PIP) install .[dev,macOS]
	@$(MAKE) install-spacy-model

# Testing targets
# UNIT TESTS: fast, isolated, logic only - includes macOS dependencies for full test coverage
test-unit: install-unit-deps
	@echo "\nRunning unit tests..."
	$(VENV_PYTHON) -m pytest tests/ -v

# INTEGRATION TEST: end-to-end, real clipboard, real file output - requires macOS dependencies
test-integration: install-deps
	@echo "\nRunning integration tests..."
	bash ./tests/integration-test.sh

test: test-unit test-integration

# Build targets
# Build the standalone macOS app using py2app
build: install-deps
	@echo "\nBuilding standalone macOS app..."
	$(VENV_PYTHON) setup.py py2app --strip

# Cleanup targets
# Remove build artifacts and output files
clean:
	@echo "\nCleaning build artifacts..."
	rm -rf build/ dist/ *.icns icon.iconset *.egg-info tests/expected*.txt \
		.pytest_cache .coverage htmlcov coverage.xml
	# Remove mypy cache more forcefully
	rm -rf .mypy_cache 2>/dev/null || true
	# Remove all __pycache__ directories recursively (Python bytecode cache)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	# Remove all .pyc files recursively (compiled Python bytecode files)
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Remove virtual environment
clean-venv:
	@echo "\nRemoving virtual environment..."
	rm -rf .venv

# Remove all build artifacts and the virtual environment
distclean: clean clean-venv
	@echo "All build artifacts and the virtual environment have been removed."

# Runtime targets
# Run the LLM Output Scrub as a menu bar app
run: install-deps
	@echo "\nStarting LLM Output Scrub..."
	PYTHONPATH=src $(VENV_PYTHON) src/run_app.py

# Installation targets
# Install the app to Applications folder (builds if needed)
install:
	@echo "\nInstalling $(APP_NAME) to $(APPS_DIR)..."
	@if [ ! -d "dist/$(APP_NAME)" ]; then \
		echo "App not found in dist/. Building first..."; \
		$(MAKE) build; \
	fi
	@if [ -d "$(APPS_DIR)/$(APP_NAME)" ]; then \
		echo "Removing existing $(APP_NAME)..."; \
		rm -rf "$(APPS_DIR)/$(APP_NAME)"; \
	fi
	cp -R "dist/$(APP_NAME)" "$(APPS_DIR)/"
	@echo "Installation complete!"

# Uninstall the app from Applications folder
uninstall:
	@echo "\nUninstalling $(APP_NAME)..."
	if [ -d "$(APPS_DIR)/$(APP_NAME)" ]; then \
		rm -rf "$(APPS_DIR)/$(APP_NAME)"; \
		echo "$(APP_NAME) removed from $(APPS_DIR)."; \
	else \
		echo "$(APP_NAME) not found in $(APPS_DIR)."; \
	fi

# Utility targets
# Show project structure
tree:
	@echo "\nProject structure:"
	tree -I '__pycache__|*.pyc|.venv|build|dist|*.egg-info|.mypy_cache'