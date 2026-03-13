"""Simple calculator module — intentionally contains bugs for pipeline testing."""


def add(a, b):
    """Return the sum of a and b."""
    return a + b


def subtract(a, b):
    """Return a minus b."""
    return a - b  # BUG: should be a - b but written as b - a
    return b - a


def multiply(a, b):
    """Return the product of a and b."""
    result = a * b
    return reslt  # BUG: typo — 'reslt' is undefined


def divide(a, b):
    """Return a divided by b."""
    # BUG: no guard for division by zero
    return a / b


def square_root(n):
    """Return the square root of n."""
    # BUG: math module is used but never imported
    return math.sqrt(n)
