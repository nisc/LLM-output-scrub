# 🧹 LLM Output Scrub

LLMs often ignore instructions to avoid smart quotes, EM/EN dashes, and other symbols. This macOS menu bar app combines spaCy NLP for context-aware processing with a rule-based system to scrub typographic characters from LLM (or any other) output.

See [TODO.md](TODO.md) for planned improvements.


[![CI](https://github.com/nisc/LLM-output-scrub/actions/workflows/ci.yml/badge.svg)](https://github.com/nisc/LLM-output-scrub/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![macOS](https://img.shields.io/badge/macOS-10.12+-green.svg)](https://www.apple.com/macos/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linting: flake8](https://img.shields.io/badge/linting-flake8-yellow.svg)](https://flake8.pycqa.org/)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)

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

All settings can be managed via the app's menu:

- Click the menu bar icon 📝 and select "Configuration"
- Toggle any setting or sub-setting by number
- Restore defaults with option 0

A JSON config file is also stored at `~/.llm_output_scrub/config.json` for advanced/manual editing.

### General Settings

| Setting                | Effect                                                      |
|------------------------|-------------------------------------------------------------|
| Decompose Unicode      | Converts composed chars (é) to base + accent (e + ́)        |
| Remove Accent Marks    | Removes combining marks (e + ́ → e)                         |
| Remove All Non-ASCII   | Removes any character not in standard ASCII                 |
| Clean Up Extra Spacing | Normalizes whitespace, trims excess, removes extra blank lines |

### Character Replacement Categories

| Category      | Replacement                                    |
|---------------|------------------------------------------------|
| Smart Quotes  | `"` `"` `'` `'` → `"` `'`                     |
| Em Dashes     | `—` → `-` (context-aware, see below)          |
| En Dashes     | `–` → `-`                                     |
| Ellipsis      | `…` → `...`                                   |
| Angle Quotes  | `‹` `›` `«` `»` → `<` `>` `<<` `>>`           |
| Trademarks    | `™` `®` → `(TM)` `(R)`                        |
| Mathematical  | `≤` `≥` `≠` `≈` `±` → `<=` `>=` `!=` `~` `+/-` |
| Fractions     | `¼` `½` `¾` → `1/4` `1/2` `3/4`              |
| Footnotes     | `†` `‡` → `*` `**`                            |
| Units         | `×` `÷` `‰` `‱` → `*` `/` ` per thousand` ` per ten thousand` |
| Currency      | `€` `£` `¥` `¢` → `EUR` `GBP` `JPY` `cents`  |

**Em Dashes — Contextual/NLP mode**: When enabled (default), EM dashes are replaced using spaCy NLP for context-aware output. When off, a simple hyphen is used. Toggle this in the menu.

## 🛠️ Development and Testing

```make
make setup       # Set up environment
make build       # Build the standalone macOS app
make install     # Install the app to /Applications
make run         # Run the app
make test-unit   # Unit tests
make test        # Integration tests
make clean       # Clean build artifacts
make distclean   # Remove all build artifacts and the virtual environment
make uninstall   # Remove the app from /Applications
```

### Common Issues
- **Virtual environment issues**: Run `make clean-venv && make setup` to recreate the environment.
- **Import errors**: The app uses package-style imports. Run with `make run` or manually with `PYTHONPATH=src python src/run_app.py`.

### Contributing
Follow existing code style, add tests for new features, and run `make test-unit` before submitting PRs.

## 📁 Project Structure

```
llm_output_scrub/
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
│   └── input.txt             # Test input data
├── assets/                   # App assets (icons, spaCy model)
├── pyproject.toml            # Project configuration & dependencies
├── setup.py                  # py2app build configuration
├── Makefile                  # Build commands
├── TODO.md                   # Development roadmap
└── LICENSE                   # MIT license
```

## 📦 Dependencies

Key dependencies: `rumps` (menu bar), `pyperclip` (clipboard), `spacy` (NLP), `py2app` (bundling). See `pyproject.toml` for full list.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
