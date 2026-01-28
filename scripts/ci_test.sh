#!/bin/bash
# CI test script - runs all checks that CI would run
set -euo pipefail

echo "=== CI Test Script ==="
echo "Working directory: $(pwd)"
echo ""

# Test 1: Python syntax
echo "1. Checking Python syntax..."
python3 -m py_compile gold_pricing/utils.py gold_pricing/models/*.py tests/*.py
echo "   ✓ Syntax check passed"
echo ""

# Test 2: Test imports
echo "2. Testing module imports..."
python3 -c "
import sys
sys.path.insert(0, '.')
from tests import test_price_parsing, test_price_computation
print('   ✓ Test modules imported')
"
echo ""

# Test 3: Run all tests
echo "3. Running all tests..."
python3 -c "
import sys
sys.path.insert(0, '.')

from tests import test_price_parsing, test_price_computation

tests_run = 0
for module_name, module in [('parsing', test_price_parsing), ('computation', test_price_computation)]:
    test_funcs = [f for f in dir(module) if f.startswith('test_')]
    for test_name in test_funcs:
        getattr(module, test_name)()
        tests_run += 1

print(f'   ✓ All {tests_run} tests passed')
"
echo ""

echo "=== All CI checks passed ==="
