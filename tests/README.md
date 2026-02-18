# Tests

This folder contains all test and validation scripts.

## Test Files
- `test_*.py` - Unit and integration tests (run with pytest)
- `conftest.py` - Pytest configuration and fixtures

## Validation Scripts
- `check_balance.py` - Check Binance account balance
- `check_binance_filters.py` - Validate trading pair filters
- `check_metrics.py` - Check bot performance metrics
- `check_portfolio.py` - Check current portfolio status
- `check_real_balance.py` - Verify real account balance
- `validate_indicators.py` - Validate technical indicators
- `verify_startup.py` - Verify bot startup sequence

## Example Scripts
- `example_usage.py` - Example usage demonstrations
- `example_multi_timeframe_structure.py` - Multi-timeframe data structure examples

## Running Tests

### All tests:
```bash
pytest tests/
```

### Specific test:
```bash
pytest tests/test_binance_client.py
```

### With coverage:
```bash
pytest tests/ --cov=app
```

### Validation scripts:
```bash
python tests/check_balance.py
python tests/validate_indicators.py
```
