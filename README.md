# 🧹 LLM Output Scrub

A macOS menu bar app that scrubs smart/typographic characters from LLM output into plain ASCII.
LLMs often ignore instructions to avoid smart quotes, dashes, and other symbols. This app
uses spaCy NLP for context-aware processing and rule-based replacement.

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![macOS](https://img.shields.io/badge/macOS-10.12+-green.svg)](https://www.apple.com/macos/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-41%20passed-brightgreen.svg)](https://github.com/nisc/LLM-output-scrub)

## ✨ Features

- 📱 **Menu Bar**: Runs as a menu bar app
- 🧠 **NLP Processing**: Uses spaCy for context detection
- ⚙️ **Configurable**: All character replacements can be customized via JSON config
  - 🔄 **Smart Quotes**: Replaces `"` `"` `'` `'` with straight quotes `"` `'`
  - ➖ **Smart Dashes**: Converts em dashes `—` and en dashes `–` to hyphens `-` with context-aware logic
  - ⚡ **Ellipsis**: Replaces `…` with three dots `...`
  - 🎯 **Symbols**: Converts typographic symbols to ASCII equivalents
  - 🌍 **Unicode**: Handles accented characters by removing diacritics
  - 🔢 **Various Others**: Supports trademarks, fractions, mathematical symbols, currency, units, and more
- 🔔 **Notifications**: Shows success/error notifications
- 📊 **NLP Stats**: Built-in performance monitoring and statistics

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

# Set up environment (handles Python version compatibility and spaCy model)
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

# Install dependencies (includes spaCy and English language model)
pip install -e .[dev,build]

# Run the app
PYTHONPATH=src python src/run_app.py
```

## 📖 Usage

1. **Copy LLM output** with smart quotes or typographic characters
2. **Click the scrubber icon** 📝 in your menu bar
3. **Select "Scrub Clipboard"** from the menu
4. **Paste** anywhere - now with plain ASCII characters!

## 🧠 Advanced EM Dash Processing

The app uses spaCy's natural language processing for context-aware EM dash replacement:

### NLP-Based Approach

The system uses spaCy's linguistic analysis instead of hardcoded wordlists:

- **Part-of-Speech (POS) Analysis**: Identifies nouns, verbs, adjectives, etc.
- **Dependency Parsing**: Understands grammatical relationships
- **Sentence Structure Analysis**: Detects boundaries and context
- **Token-level Processing**: Analyzes individual words and their roles

### Context Detection

The system detects and handles these EM dash contexts:

- **Compound Words**: `self—driving` → `self-driving`
- **Parenthetical/Appositive**: `text—additional info—more text` → `text, additional info, more text`
- **Emphasis**: `The result—amazingly—was perfect` → `The result, amazingly, was perfect`
- **Dialogue**: `"Hello"—she said` → `"Hello", she said`
- **Conjunctions**: `A—or B` → `A, or B`
- **Default Cases**: `simple—text` → `simple-text`

## ⚙️ Configuration

The app uses a JSON configuration file located at `~/.llm_output_scrub/config.json` that allows you to
customize all character replacements. The configuration includes:

### Character Replacement Categories

- **Smart Quotes**: `"` `"` `'` `'` → `"` `'`
- **Dashes**: EN dashes `–` → `-` (simple replacement)
- **Ellipsis**: `…` → `...`
- **Angle Quotes**: `‹` `›` `«` `»` → `<` `>` `<<` `>>`
- **Trademarks**: `™` `®` → `(TM)` `(R)`
- **Mathematical**: `≤` `≥` `≠` `≈` `±` → `<=` `>=` `!=` `~` `+/-`
- **Fractions**: `¼` `½` `¾` → `1/4` `1/2` `3/4`
- **Footnotes**: `†` `‡` → `*` `**`
- **Units**: `×` `÷` `‰` `‱` → `*` `/` ` per thousand` ` per ten thousand`
- **Currency**: `€` `£` `¥` `¢` → `EUR` `GBP` `JPY` `cents`

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
# Set up development environment (includes spaCy model)
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
- **spaCy model issues**: The setup automatically installs the English language model.
- **Import errors**: The app uses package-style imports. Run with `make run` or manually with `PYTHONPATH=src python src/run_app.py`.

## 📁 Project Structure

```
LLM-output-scrub/
├── src/llm_output_scrub/     # Source code
│   ├── __init__.py           # Python init
│   ├── app.py                # Main application
│   ├── config_manager.py     # Configuration management
│   ├── nlp.py                # spaCy-based NLP processing
│   └── py.typed              # Type hints marker
├── src/run_app.py            # Entry point script
├── tests/                    # Test suite
│   ├── test_scrub.py         # Unit tests
│   ├── integration-test.sh   # Integration test script
│   ├── input.txt             # Test input data
│   └── expected*.txt         # Expected test outputs
├── assets/                   # App assets (icons, etc.)
├── pyproject.toml            # Project configuration & dependencies
├── setup.py                  # py2app build configuration
└── Makefile                  # Build commands
```

## 🧪 Testing

The project includes comprehensive testing:

- **Unit Tests:**
  - Run with `make test-unit`
  - Tests all EM dash contexts, edge cases, and configurations

- **Integration Test:**
  - Run with `make test`
  - Full end-to-end test using actual clipboard
  - Verifies output automatically with multiple configurations

```bash
# Run unit tests
make test-unit

# Run integration test (end-to-end)
make test

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

## 📦 Dependencies

### Runtime Dependencies
- `rumps>=0.4.0` - macOS menu bar framework
- `pyperclip>=1.8.2` - Cross-platform clipboard access
- `watchdog>=4.0.0` - File system monitoring
- `spacy>=3.7.0` - Natural language processing for context-aware EM dash replacement
- `en-core-web-sm` - spaCy English language model (automatically installed)

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
- Use spaCy features for any new context detection

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
