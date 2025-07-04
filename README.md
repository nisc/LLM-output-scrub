# 🧹 LLM Output Scrub

A macOS menu bar app that automatically scrubs smart/typographic characters from LLM output,
replacing them with plain ASCII equivalents.

[![Python](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![macOS](https://img.shields.io/badge/macOS-10.12+-green.svg)](https://www.apple.com/macos/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## ✨ Features

- 🔄 **Smart Quotes**: Replaces `"` `"` `'` `'` with straight quotes `"` `'`
- ➖ **Dashes**: Converts em dashes `—` and en dashes `–` to hyphens `-`
- ⚡ **Ellipsis**: Replaces `…` with three dots `...`
- 🎯 **Symbols**: Converts typographic symbols to ASCII equivalents
- 🌍 **Unicode**: Handles accented characters by removing diacritics
- 🔔 **Notifications**: Shows success/error notifications
- 📱 **Menu Bar**: Runs as a clean menu bar app

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)

```bash
# Clone the repository
git clone https://github.com/nisc/LLM-output-scrub.git
cd LLM-output-scrub

# Set up environment (handles Python version compatibility)
make setup

# Run the app
make run
```

### Option 2: Manual Setup

```bash
# Clone the repository
git clone https://github.com/nisc/LLM-output-scrub.git
cd LLM-output-scrub

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .[dev,build]

# Run the app
python -m llm_output_scrub.llm_output_scrub
```

### Option 3: Build Standalone App

```bash
# Build the app
make build

# Install to Applications
make install
```

## 📖 Usage

1. **Copy LLM output** with smart quotes or typographic characters
2. **Click the scrubber icon** 🧹 in your menu bar
3. **Select "Scrub LLM Output"** from the menu
4. **Paste** anywhere - now with plain ASCII characters!

## 🛠️ Development

```bash
# Set up development environment
make setup

# Run tests
make test-unit

# Run the app
make run

# Clean build artifacts
make clean
```

### Common Issues
- **Virtual environment issues**: Run `make clean-venv && make setup` to recreate the environment.
- **Import errors**: The app uses package-style imports. Run with `PYTHONPATH=src python -m llm_output_scrub.llm_output_scrub` or use `make run`.

## 📁 Project Structure

```
LLM-output-scrub/
├── src/llm_output_scrub/     # Source code
│   ├── __init__.py
│   ├── llm_output_scrub.py   # Main application
│   ├── config_manager.py     # Configuration management
│   └── py.typed             # Type hints marker
├── tests/                    # Test suite
├── scripts/                  # Utility scripts
├── assets/                   # App assets (icons, etc.)
├── pyproject.toml           # Project configuration & dependencies
├── setup.py                 # py2app build configuration
├── main.py                  # App entry point
└── Makefile                 # Build commands
```

## 🔧 What Gets Replaced

| Smart Character | ASCII Replacement |
|----------------|-------------------|
| `"` `"` | `"` |
| `'` `'` | `'` |
| `—` `–` | `-` |
| `…` | `...` |
| `•` `·` | *preserved* |
| `™` | `(TM)` |
| `®` | `(R)` |
| `©` | *preserved* |
| `€` `£` `¥` | `EUR` `GBP` `JPY` |
| `≤` `≥` `≠` | `<=` `>=` `!=` |

*See the source code for complete list of replacements*

## 🧪 Testing

The project includes comprehensive testing:

```bash
# Run unit tests
make test-unit

# Run integration test (scrubs example file)
make test

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

## 📦 Dependencies

### Runtime Dependencies
- `rumps>=0.4.0` - macOS menu bar framework
- `pyperclip>=1.8.2` - Cross-platform clipboard access
- `watchdog>=4.0.0` - File system monitoring

### Development Dependencies
- `pytest>=7.0.0` - Testing framework
- `pytest-cov>=4.0.0` - Coverage reporting
- `black>=22.0.0` - Code formatting
- `flake8>=5.0.0` - Linting
- `mypy>=1.0.0` - Type checking

### Build Dependencies
- `py2app>=0.28.0` - macOS app bundling
- `pillow>=9.0.0` - Image processing
- `jaraco.text` - Text utilities

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow the existing code style (Black formatting, 110 character line length)
- Add tests for new features
- Update documentation as needed
- Run `make test-unit` before submitting PRs

## 📞 Getting Help

- **Issues**: Use GitHub Issues for bugs and feature requests
- **Discussions**: Use GitHub Discussions for questions and ideas

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.