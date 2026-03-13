"""Tests for the calculator module.

These tests are intentionally strict so that every bug in calculator.py
triggers at least one failure, giving the pipeline clear targets to fix.
"""
import pytest
from calculator import add, subtract, multiply, divide, square_root


# ── add ──────────────────────────────────────────────────────────────────────

def test_add_positive():
    assert add(2, 3) == 5


def test_add_negative():
    assert add(-1, -1) == -2


def test_add_zero():
    assert add(0, 7) == 7


# ── subtract ─────────────────────────────────────────────────────────────────

def test_subtract_basic():
    # BUG in calculator.py makes this fail: returns b - a instead of a - b
    assert subtract(10, 3) == 7


def test_subtract_result_negative():
    assert subtract(1, 5) == -4


# ── multiply ─────────────────────────────────────────────────────────────────

def test_multiply_basic():
    # BUG in calculator.py: NameError on 'reslt' causes this to crash
    assert multiply(3, 4) == 12


def test_multiply_by_zero():
    assert multiply(0, 999) == 0


# ── divide ───────────────────────────────────────────────────────────────────

def test_divide_basic():
    assert divide(10, 2) == 5.0


def test_divide_by_zero_raises():
    # BUG: calculator.py has no guard — should raise ZeroDivisionError cleanly
    with pytest.raises(ZeroDivisionError):
        divide(5, 0)


# ── square_root ──────────────────────────────────────────────────────────────

def test_square_root_basic():
    # BUG: calculator.py forgot to import math — NameError expected
    assert square_root(9) == 3.0


def test_square_root_zero():
    assert square_root(0) == 0.0
