# 🧹 LLM Output Scrub

A customizable macOS menu bar app that automatically scrubs smart/typographic characters from LLM output (or really any text) into plain ASCII, with configurable replacement rules for smart quotes, dashes, and other symbols.

[![Python](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![macOS](https://img.shields.io/badge/macOS-10.12+-green.svg)](https://www.apple.com/macos/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## ✨ Features

- 📱 **Menu Bar**: Runs as a menu bar app
- ⚙️ **Configurable**: All character replacements can be customized via JSON config (more detail below)
  - 🔄 **Smart Quotes**: Replaces `"` `"` `'` `'` with straight quotes `"` `'`
  - ➖ **Smart Dashes**: Converts em dashes `—` and en dashes `–` to hyphens `-` with context-aware logic
  - ⚡ **Ellipsis**: Replaces `…` with three dots `...`
  - 🎯 **Symbols**: Converts typographic symbols to ASCII equivalents
  - 🌍 **Unicode**: Handles accented characters by removing diacritics
  - 🔢 **Various Others**: Supports trademarks, fractions, mathematical symbols, currency, units, and more
- 🔔 **Notifications**: Shows success/error notifications

## 🚀 Quick Start

### Option 1: Build Standalone App (Recommended)

```bash
# Clone the repository
git clone https://github.com/nisc/LLM-output-scrub.git
cd LLM-output-scrub

# Build and install the app
make build
make install
```

### Option 2: Automated Development Setup

```bash
# Clone the repository
git clone https://github.com/nisc/LLM-output-scrub.git
cd LLM-output-scrub

# Set up environment (handles Python version compatibility)
make setup

# Run the app
make run
```

### Option 3: Manual Development Setup

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

## 📖 Usage

1. **Copy LLM output** with smart quotes or typographic characters
2. **Click the scrubber icon** 🧹 in your menu bar
3. **Select "Scrub LLM Output"** from the menu
4. **Paste** anywhere - now with plain ASCII characters!

## ⚙️ Configuration

The app uses a JSON configuration file located at `~/.llm_output_scrub/config.json` that allows you to customize all character replacements. The configuration includes:

### Character Replacement Categories

- **Smart Quotes**: `"` `"` `'` `'` → `"` `'`
- **Dashes**: EN dashes `–` → `-` (simple replacement)
- **Ellipsis**: `…` → `...`
- **Angle Quotes**: `‹` `›` `«` `»` → `<` `>` `<<` `>>`
- **Trademarks**: `™` `®` → `(TM)` `(R)`
- **Mathematical**: `≤` `≥` `≠` `≈` `±` → `<=` `>=` `!=` `~` `+/-`
- **Fractions**: `¼` `½` `¾` → `1/4` `1/2` `3/4`
- **Footnotes**: `†` `‡` → `*` `**`
- **Units**: `×` `÷` `‰` `‱` → `*` `/` `per thousand` `per ten thousand`
- **Currency**: `€` `£` `¥` `¢` → `EUR` `GBP` `JPY` `cents`

### Special EM Dash Handling

EM dashes (`—`) use advanced context-aware replacement logic rather than simple character substitution:

- **Ranges**: `1—10` → `1-10`
- **Parenthetical**: `text—additional info—more text` → `text, additional info, more text`
- **Sentence boundaries**: `He stopped—what was that?` → `He stopped... what was that?`
- **Compound words**: `self—driving` → `self-driving`
- **Lists**: `1—self—driving cars` → `1: self-driving cars`
- **Dialogue**: `"Hello"—she said` → `"Hello", she said`

### Configuration File Structure

```json
{
  "general": {
    "normalize_unicode": true,
    "normalize_whitespace": true,
    "remove_combining_chars": false,
    "remove_non_ascii": false
  },
  "character_replacements": {
    "smart_quotes": {
      "enabled": true,
      "replacements": {
        "\u201c": "\"",
        "\u201d": "\"",
        "\u2018": "'",
        "\u2019": "'"
      }
    }
  }
}
```

Each category can be enabled/disabled independently, and you can add custom replacements to any category.

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
│   ├── dash_nlp.py          # Context-aware dash replacement
│   └── py.typed             # Type hints marker
├── tests/                    # Test suite
├── scripts/                  # Utility scripts
├── assets/                   # App assets (icons, etc.)
├── pyproject.toml           # Project configuration & dependencies
├── setup.py                 # py2app build configuration
├── main.py                  # App entry point
└── Makefile                 # Build commands
```

## 🧪 Testing

The project includes both integration and unit testing:

- **Integration Test:**
  - Run with `make test`
  - This is a full end-to-end test: it scrubs a real example file using the actual clipboard and writes the output to files.
  - It verifies the output automatically and checks both the default config and a config with all categories enabled.
  - Use this to ensure the app works as expected in a real environment.

- **Unit Tests:**
  - Run with `make test-unit`
  - These are fast, isolated tests that check individual functions and edge cases.
  - Use this for rapid development and to verify logic changes.

```bash
# Run integration test (end-to-end)
make test

# Run unit tests
make test-unit

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