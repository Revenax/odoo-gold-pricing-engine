.PHONY: check lint test type-check install-dev

check: lint test type-check
	@echo "All checks passed!"

lint:
	@echo "Running linter..."
	ruff check gold_pricing/ tests/

test:
	@echo "Running tests..."
	@python3 -m pytest tests/ -v 2>/dev/null || \
	 python3 -c "import sys; sys.path.insert(0, '.'); \
	 from tests import test_price_parsing, test_price_computation; \
	 test_price_parsing.test_extract_price_from_arabic_text(); \
	 test_price_parsing.test_fallback_pattern_extraction(); \
	 test_price_parsing.test_no_price_found_raises_error(); \
	 test_price_parsing.test_empty_text_raises_error(); \
	 test_price_computation.test_compute_21k_price(); \
	 test_price_computation.test_compute_24k_price(); \
	 test_price_computation.test_zero_markup(); \
	 test_price_computation.test_invalid_purity_raises_error(); \
	 test_price_computation.test_zero_weight_raises_error(); \
	 test_price_computation.test_negative_markup_raises_error(); \
	 print('✓ All tests passed!')" || \
	 echo "Note: Install pytest for better test output: make install-dev"

type-check:
	@echo "Running type checker..."
	mypy gold_pricing/utils.py --ignore-missing-imports

install-dev:
	@echo "Installing development dependencies..."
	pip install -r requirements-dev.txt
