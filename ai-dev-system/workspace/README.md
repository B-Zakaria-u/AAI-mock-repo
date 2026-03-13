# Workspace sub-project — Calculator (buggy version for pipeline testing)

## Purpose
This sub-project lives in `workspace/` and is fed to the AI dev pipeline as a
ticket target. It deliberately contains **4 bugs** at different severity levels
so the Coding Agent, Linter, and Docker sandbox each have real failures to catch.

## Bug inventory

| # | File | Bug type | Description |
|---|------|----------|-------------|
| 1 | `calculator.py` | Unreachable code / logic error | `subtract()` has a dead `return b - a` after the correct line — swapped operands make the real return wrong |
| 2 | `calculator.py` | `NameError` | `multiply()` references `reslt` instead of `result` |
| 3 | `calculator.py` | `ZeroDivisionError` risk | `divide()` performs no zero guard |
| 4 | `calculator.py` | `NameError` / missing import | `square_root()` calls `math.sqrt()` without importing `math` |

## Test coverage

`test_calculator.py` covers all four bugs with explicit assertions and a
`pytest.raises` check, so **every** bug produces at least one failing test.

## How to run locally (outside the pipeline)

```bash
cd workspace
pip install pytest
pytest test_calculator.py -v
```

Expected result: **4+ failures** before the pipeline fixes them.
