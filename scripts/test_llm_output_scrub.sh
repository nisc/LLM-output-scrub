#!/bin/bash

# INTEGRATION TEST for llm_output_scrub.py
# This script tests the full end-to-end pipeline using the real clipboard and file output.
# It is NOT a unit test; see 'make test-unit' for unit tests.
# Usage: ./scripts/test_llm_output_scrub.sh

set -e

# Check for virtual environment
if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

# Input and output files
INPUT_FILE="tests/test_smart_text_input.txt"
OUTPUT_FILE_DEFAULT="tests/test_smart_text_scrubbed_default.txt"
OUTPUT_FILE_ALL="tests/test_smart_text_scrubbed_all.txt"

echo "=== Testing LLM Output Scrub ==="
echo "Input file: $INPUT_FILE"
echo ""

# Test 1: Default configuration
echo "Test 1: Default configuration (smart quotes, dashes, ellipsis only)"
cat "$INPUT_FILE" | pbcopy

python3 -c "import sys; sys.path.insert(0, 'src'); \
  from llm_output_scrub import LLMOutputScrub; \
  LLMOutputScrub().scrub_llm_output(None)"

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

# Check that mathematical symbols were converted (units category is enabled by default)
if echo "$DEFAULT_CONTENT" | grep -q "2 \* 3" && echo "$DEFAULT_CONTENT" | grep -q "10 / 2"; then
    echo "  ✓ Mathematical symbols converted correctly (units category enabled)"
else
    echo "  ❌ Mathematical symbols not converted properly"
    exit 1
fi

echo "  ✓ Default config test PASSED"
echo ""

# Test 2: All categories enabled
echo "Test 2: All categories enabled"
cat "$INPUT_FILE" | pbcopy

python3 -c "import sys; sys.path.insert(0, 'src'); \
  from llm_output_scrub import LLMOutputScrub; \
  scrubber = LLMOutputScrub(); \
  [scrubber.config.set_category_enabled(cat, True) for cat in scrubber.config.get_categories()]; \
  scrubber.scrub_llm_output(None)"

pbpaste > "$OUTPUT_FILE_ALL"
echo "✓ All categories output written to $OUTPUT_FILE_ALL"

# Verify all categories results
echo "Verifying all categories results..."
ALL_CONTENT=$(cat "$OUTPUT_FILE_ALL")

# Check that mathematical symbols were converted
if echo "$ALL_CONTENT" | grep -q "2 \* 3" && echo "$ALL_CONTENT" | grep -q "10 / 2" && echo "$ALL_CONTENT" | grep -q "5 +/- 2"; then
    echo "  ✓ Mathematical symbols converted correctly"
else
    echo "  ❌ Mathematical symbols not converted properly"
    exit 1
fi

# Check that currency symbols were converted
if echo "$ALL_CONTENT" | grep -q "EUR50" && echo "$ALL_CONTENT" | grep -q "GBP30" && echo "$ALL_CONTENT" | grep -q "JPY1000"; then
    echo "  ✓ Currency symbols converted correctly"
else
    echo "  ❌ Currency symbols not converted properly"
    exit 1
fi

# Check that fractions were converted
if echo "$ALL_CONTENT" | grep -q "1/4" && echo "$ALL_CONTENT" | grep -q "1/2" && echo "$ALL_CONTENT" | grep -q "3/4"; then
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
if echo "$ALL_CONTENT" | grep -q "<See reference>" && echo "$ALL_CONTENT" | grep -q "<<Important note>>"; then
    echo "  ✓ Angle quotes converted correctly"
else
    echo "  ❌ Angle quotes not converted properly"
    exit 1
fi

# Check that per mille symbols were converted
if echo "$ALL_CONTENT" | grep -q "per thousand" && echo "$ALL_CONTENT" | grep -q "per ten thousand"; then
    echo "  ✓ Per mille symbols converted correctly"
else
    echo "  ❌ Per mille symbols not converted properly"
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