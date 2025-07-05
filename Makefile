# Makefile for LLM Output Scrub project

.PHONY: all test test-unit build clean clean-venv run install install-deps tree setup venv

all: test-unit test build

# Initial setup - use this for first-time setup or when having issues
setup:
	@echo "Setting up LLM Output Scrub development environment..."
	@if [ -d ".venv" ]; then \
		echo "Removing existing virtual environment..."; \
		rm -rf .venv; \
	fi
	$(MAKE) venv
	$(MAKE) install-deps
	@echo "Setup complete! Virtual environment is ready."
	@echo "To activate: source .venv/bin/activate"
	@echo "To run the app: make run"

VENV_PYTHON = .venv/bin/python
VENV_PIP = .venv/bin/pip

# Create virtual environment if it doesn't exist
venv:
	@echo "Creating virtual environment..."
	python3 -m venv .venv
	$(VENV_PYTHON) -m ensurepip --upgrade
	$(VENV_PIP) install --upgrade pip

# Install dependencies (robust with fallbacks)
install-deps: venv
	@echo "Installing dependencies..."
	@$(VENV_PIP) install .[dev,build]

# Run the test script to scrub the example file
# INTEGRATION TEST: end-to-end, real clipboard, real file output
test: install-deps
	bash ./scripts/test_llm_output_scrub.sh

# Run unit tests
# UNIT TESTS: fast, isolated, logic only
test-unit: install-deps
	$(VENV_PYTHON) -m pytest tests/ -v

# Build the standalone macOS app using py2app
build: install-deps
	$(VENV_PYTHON) setup.py py2app

# Remove build artifacts and output files
clean:
	rm -rf build/ dist/ *.icns icon.iconset *.egg-info tests/test_smart_text_scrubbed*.txt \
		.pytest_cache .coverage htmlcov coverage.xml .mypy_cache
	# Remove all __pycache__ directories recursively (Python bytecode cache)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	# Remove all .pyc files recursively (compiled Python bytecode files)
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Remove virtual environment
clean-venv:
	rm -rf .venv

# Run the LLM Output Scrub as a menu bar app
run: install-deps
	PYTHONPATH=src $(VENV_PYTHON) -m llm_output_scrub.llm_output_scrub

# Install the app to Applications folder
install: build
	if [ -d "/Applications/LLM Output Scrub.app" ]; then \
		rm -rf "/Applications/LLM Output Scrub.app"; \
	fi
	cp -R dist/LLM\ Output\ Scrub.app /Applications/

# Uninstall the app from Applications folder
uninstall:
	if [ -d "/Applications/LLM Output Scrub.app" ]; then \
		rm -rf "/Applications/LLM Output Scrub.app"; \
		echo "LLM Output Scrub.app removed from /Applications."; \
	else \
		echo "LLM Output Scrub.app not found in /Applications."; \
	fi

# Show project structure
tree:
	tree -I '__pycache__|*.pyc|.venv|build|dist|*.egg-info|.mypy_cache'