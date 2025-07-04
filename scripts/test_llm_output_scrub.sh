#!/bin/bash

# Test script for llm_output_scrub.py
# Usage: ./scripts/test_llm_output_scrub.sh

set -e

# Check for virtual environment
if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

# Input and output files
INPUT_FILE="tests/test_smart_text_input.txt"
OUTPUT_FILE="tests/test_smart_text_scrubbed.txt"

# Copy input file to clipboard
cat "$INPUT_FILE" | pbcopy

# Run the LLM Output Scrub (simulate menu click)
python3 -c "import sys; sys.path.insert(0, 'src'); \
  from llm_output_scrub import LLMOutputScrub; \
  LLMOutputScrub().scrub_llm_output(None)"

# Paste scrubbed clipboard to output file
pbpaste > "$OUTPUT_FILE"

echo "Scrubbed text written to $OUTPUT_FILE"