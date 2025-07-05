#!/bin/bash

# INTEGRATION TEST for llm_output_scrub.py
# This script tests the full end-to-end pipeline using the real clipboard and file output.
# It is NOT a unit test; see 'make test-unit' for unit tests.
# Usage: ./tests/integration-test.sh

set -e

# Check for virtual environment
if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

# Input and output files
INPUT_FILE="tests/input.txt"
OUTPUT_FILE_DEFAULT="tests/expected_default.txt"
OUTPUT_FILE_ALL="tests/expected_all.txt"

echo "=== Testing LLM Output Scrub ==="
echo "Input file: $INPUT_FILE"
echo ""

# Create a temporary config file for the test
TEMP_CONFIG=$(mktemp /tmp/llm_output_scrub_test_config.XXXXXX.json)
# Do not copy any user config; let the app create defaults as needed
trap 'rm -f "$TEMP_CONFIG"' EXIT

# Test 1: Default configuration
echo "Test 1: Default configuration (smart quotes, dashes, ellipsis only)"
cat "$INPUT_FILE" | pbcopy

python3 -c "import sys; sys.path.insert(0, 'src'); \
  from llm_output_scrub import LLMOutputScrub; \
  LLMOutputScrub(config_file='$TEMP_CONFIG').scrub_llm_output(None)"

pbpaste > "$OUTPUT_FILE_DEFAULT"
echo "✓ Default config output written to $OUTPUT_FILE_DEFAULT"

# Verify default config results
echo "Verifying default config results..."
DEFAULT_CONTENT=$(cat "$OUTPUT_FILE_DEFAULT")

# Check that smart quotes were converted
if echo "$DEFAULT_CONTENT" | grep -q '"smart quotes"' && echo "$DEFAULT_CONTENT" | grep -q "'curly apostrophes'"; then
    echo "  ✓ Smart quotes converted correctly"
else
    echo "  ❌ Smart quotes not converted properly"
    exit 1
fi

# Check that dashes were converted
if echo "$DEFAULT_CONTENT" | grep -q "em dash, which creates emphasis" && echo "$DEFAULT_CONTENT" | grep -q "2010-2020"; then
    echo "  ✓ Dashes converted correctly"
else
    echo "  ❌ Dashes not converted properly"
    exit 1
fi

# Check that ellipsis was converted
if echo "$DEFAULT_CONTENT" | grep -q "Ellipsis... indicates"; then
    echo "  ✓ Ellipsis converted correctly"
else
    echo "  ❌ Ellipsis not converted properly"
    exit 1
fi

echo "  ✓ Default config test PASSED"
echo ""

# Test 2: All categories enabled
echo "Test 2: All categories enabled"
cat "$INPUT_FILE" | pbcopy

python3 -c "
import sys
sys.path.insert(0, 'src')
from llm_output_scrub import LLMOutputScrub
scrubber = LLMOutputScrub(config_file='$TEMP_CONFIG')
for cat in scrubber.config.get_categories():
    scrubber.config.config['character_replacements'][cat]['enabled'] = True
scrubber.config.config['general']['normalize_whitespace'] = True
scrubber.scrub_llm_output(None)
"

pbpaste > "$OUTPUT_FILE_ALL"
echo "✓ All categories output written to $OUTPUT_FILE_ALL"

# Verify all categories results
echo "Verifying all categories results..."
ALL_CONTENT=$(cat "$OUTPUT_FILE_ALL")

# Check that mathematical symbols were converted
if echo "$ALL_CONTENT" | grep -q "2 \* 3" && echo "$ALL_CONTENT" | grep -q "10 / 2" && \
   echo "$ALL_CONTENT" | grep -q "5 +/- 2"; then
    echo "  ✓ Mathematical symbols converted correctly"
else
    echo "  ❌ Mathematical symbols not converted properly"
    exit 1
fi

# Check that currency symbols were converted
if echo "$ALL_CONTENT" | grep -q "EUR50" && echo "$ALL_CONTENT" | grep -q "GBP30" && \
   echo "$ALL_CONTENT" | grep -q "JPY1000"; then
    echo "  ✓ Currency symbols converted correctly"
else
    echo "  ❌ Currency symbols not converted properly"
    exit 1
fi

# Check that fractions were converted
if echo "$ALL_CONTENT" | grep -q "1/4" && echo "$ALL_CONTENT" | grep -q "1/2" && \
   echo "$ALL_CONTENT" | grep -q "3/4"; then
    echo "  ✓ Fractions converted correctly"
else
    echo "  ❌ Fractions not converted properly"
    exit 1
fi

# Check that trademarks were converted
if echo "$ALL_CONTENT" | grep -q "(TM)" && echo "$ALL_CONTENT" | grep -q "(R)"; then
    echo "  ✓ Trademarks converted correctly"
else
    echo "  ❌ Trademarks not converted properly"
    exit 1
fi

# Check that angle quotes were converted
if echo "$ALL_CONTENT" | grep -q "<See reference>" && \
   echo "$ALL_CONTENT" | grep -A1 "<<Important" | grep -q "note>>"; then
    echo "  ✓ Angle quotes converted correctly"
else
    echo "  ❌ Angle quotes not converted properly"
    exit 1
fi

# Check that per mille symbols were converted
if echo "$ALL_CONTENT" | grep -q "per thousand" && \
   echo "$ALL_CONTENT" | grep -q "per ten thousand"; then
    echo "  ✓ Per mille symbols converted correctly"
else
    echo "  ❌ Per mille symbols not converted properly"
    exit 1
fi

# Check whitespace normalization behavior
echo "Verifying whitespace normalization behavior..."

# Check that multiple spaces are normalized to single spaces
if echo "$ALL_CONTENT" | grep -q "Multiple    spaces" && \
   echo "$ALL_CONTENT" | grep -q "Multiple spaces"; then
    echo "  ❌ Multiple spaces not normalized properly"
    exit 1
else
    echo "  ✓ Multiple spaces normalized correctly"
fi

# Check that empty lines are preserved (not all stripped)
EMPTY_LINE_COUNT=$(echo "$ALL_CONTENT" | grep -c "^$" || echo "0")
if [ "$EMPTY_LINE_COUNT" -eq 0 ]; then
    echo "  ❌ All empty lines were stripped (should preserve some)"
    exit 1
else
    echo "  ✓ Empty lines preserved correctly ($EMPTY_LINE_COUNT empty lines)"
fi

# Check that excessive empty lines are trimmed (not multiple consecutive empty lines)
if awk 'prev=="" && $0==""{exit 1} {prev=$0}' tests/expected_all.txt; then
    echo "  ✓ Excessive empty lines trimmed correctly"
else
    echo "  ❌ Multiple consecutive empty lines not trimmed properly"
    exit 1
fi

echo "  ✓ All categories test PASSED"
echo ""

echo "=== Test Results Summary ==="
echo "✅ All tests PASSED!"
echo "Default config file: $OUTPUT_FILE_DEFAULT"
echo "All categories file: $OUTPUT_FILE_ALL"
echo ""
echo "You can compare the files to see the difference between default and full scrubbing."