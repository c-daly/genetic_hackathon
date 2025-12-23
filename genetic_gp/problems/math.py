"""Mathematical test problems for genetic programming.

Each test function takes a callable f(n) -> float and returns
a fitness score in [0, 1] where 1.0 means perfect accuracy.

NOTE: Functions are named test_* for consistency with problem naming,
but they are fitness functions, not pytest tests.
"""

from __future__ import annotations
from typing import Callable, List, Tuple

# Prevent pytest from collecting functions from this module as tests
__test__ = False


def make_test_fn(
    test_cases: List[Tuple[int, float]],
    tolerance: float = 0.1,
) -> Callable[[Callable[[int], float]], float]:
    """Create a test function from a list of (input, expected_output) pairs.

    Args:
        test_cases: List of (input, expected_output) tuples
        tolerance: Maximum allowed error per test case

    Returns:
        A fitness function that scores candidates against the test cases
    """
    def test_fn(func: Callable[[int], float]) -> float:
        correct = 0
        for n, expected in test_cases:
            try:
                result = func(n)
                if abs(result - expected) < tolerance:
                    correct += 1
            except Exception:
                pass
        return correct / len(test_cases)

    return test_fn


def test_double(func: Callable[[int], float]) -> float:
    """Test f(n) = 2n"""
    tests = [(0, 0), (1, 2), (2, 4), (3, 6), (5, 10), (10, 20)]
    correct = sum(1 for n, exp in tests if abs(func(n) - exp) < 0.1)
    return correct / len(tests)


def test_square(func: Callable[[int], float]) -> float:
    """Test f(n) = n^2"""
    tests = [(0, 0), (1, 1), (2, 4), (3, 9), (4, 16), (5, 25)]
    correct = 0
    for n, expected in tests:
        try:
            result = func(n)
            if abs(result - expected) < 0.1:
                correct += 1
        except Exception:
            pass
    return correct / len(tests)


def test_cube(func: Callable[[int], float]) -> float:
    """Test f(n) = n^3"""
    tests = [(0, 0), (1, 1), (2, 8), (3, 27), (4, 64), (5, 125)]
    correct = 0
    for n, expected in tests:
        try:
            result = func(n)
            if abs(result - expected) < 0.1:
                correct += 1
        except Exception:
            pass
    return correct / len(tests)


def test_sum_to_n(func: Callable[[int], float]) -> float:
    """Test f(n) = 1 + 2 + ... + n = n(n+1)/2"""
    tests = [(1, 1), (2, 3), (3, 6), (4, 10), (5, 15), (10, 55)]
    correct = 0
    for n, expected in tests:
        try:
            result = func(n)
            if abs(result - expected) < 0.1:
                correct += 1
        except Exception:
            pass
    return correct / len(tests)


def test_factorial(func: Callable[[int], float]) -> float:
    """Test f(n) = n!"""
    tests = [(0, 1), (1, 1), (2, 2), (3, 6), (4, 24), (5, 120)]
    correct = 0
    for n, expected in tests:
        try:
            result = func(n)
            if abs(result - expected) < 0.1:
                correct += 1
        except Exception:
            pass
    return correct / len(tests)


def test_sum_of_squares(func: Callable[[int], float]) -> float:
    """Test f(n) = 1^2 + 2^2 + ... + n^2"""
    tests = [(1, 1), (2, 5), (3, 14), (4, 30), (5, 55)]
    correct = 0
    for n, expected in tests:
        try:
            result = func(n)
            if abs(result - expected) < 0.1:
                correct += 1
        except Exception:
            pass
    return correct / len(tests)


def test_integral_x(func: Callable[[int], float]) -> float:
    """Test f(n) = integral from 0 to n of x dx = n^2/2"""
    tests = [(0, 0), (1, 0.5), (2, 2), (3, 4.5), (4, 8), (5, 12.5)]
    correct = 0
    for n, expected in tests:
        try:
            result = func(n)
            if abs(result - expected) < 0.5:  # Looser tolerance for this one
                correct += 1
        except Exception:
            pass
    return correct / len(tests)


def test_fibonacci(func: Callable[[int], float]) -> float:
    """Test f(n) = nth Fibonacci number"""
    tests = [(0, 0), (1, 1), (2, 1), (3, 2), (4, 3), (5, 5), (6, 8), (7, 13)]
    correct = 0
    for n, expected in tests:
        try:
            result = func(n)
            if abs(result - expected) < 0.1:
                correct += 1
        except Exception:
            pass
    return correct / len(tests)


def test_power_of_two(func: Callable[[int], float]) -> float:
    """Test f(n) = 2^n"""
    tests = [(0, 1), (1, 2), (2, 4), (3, 8), (4, 16), (5, 32)]
    correct = 0
    for n, expected in tests:
        try:
            result = func(n)
            if abs(result - expected) < 0.1:
                correct += 1
        except Exception:
            pass
    return correct / len(tests)
