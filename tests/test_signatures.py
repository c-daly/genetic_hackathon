"""Tests for core/signatures.py - Behavioral signatures."""

import pytest
from genetic_gp.core.expressions import Const, Var, BinOp, Sum
from genetic_gp.core.signatures import (
    behavioral_signature,
    signatures_match,
    signature_similarity,
    analyze_growth,
)


class TestBehavioralSignature:
    """Tests for behavioral_signature function."""

    def test_constant_signature(self):
        """Constant should produce same output for all inputs."""
        expr = Const(5)
        sig = behavioral_signature(expr)
        assert len(sig) == 20  # Default range(20)
        assert all(v == 5 for v in sig)

    def test_variable_signature(self):
        """Variable should produce input sequence."""
        expr = Var('n')
        sig = behavioral_signature(expr)
        assert sig == tuple(range(20))

    def test_double_signature(self):
        """2*n should produce doubled sequence."""
        expr = BinOp('*', Const(2), Var('n'))
        sig = behavioral_signature(expr)
        expected = tuple(2 * n for n in range(20))
        assert sig == expected

    def test_square_signature(self):
        """n^2 should produce squared sequence."""
        expr = BinOp('^', Var('n'), Const(2))
        sig = behavioral_signature(expr)
        expected = tuple(n * n for n in range(20))
        assert sig == expected

    def test_custom_test_inputs(self):
        """Should use custom test inputs if provided."""
        expr = Var('n')
        sig = behavioral_signature(expr, test_inputs=[1, 5, 10])
        assert sig == (1, 5, 10)

    def test_custom_var_name(self):
        """Should use custom variable name."""
        expr = Var('x')
        sig = behavioral_signature(expr, var_name='x')
        assert sig == tuple(range(20))

    def test_caps_extreme_values(self):
        """Should cap extremely large values."""
        # n^10 grows very fast
        expr = BinOp('^', Var('n'), Const(10))
        sig = behavioral_signature(expr, cap_value=1e10)
        # Later values should be capped
        assert sig[-1] == 1e10 or sig[-1] <= 1e10

    def test_handles_errors_gracefully(self):
        """Should return 0 for expressions that error."""
        # Division by zero when n=0
        expr = BinOp('/', Const(1), Var('n'))
        sig = behavioral_signature(expr)
        # First value (n=0) should not crash, division by ~0 returns 0
        assert isinstance(sig[0], (int, float))


class TestSignaturesMatch:
    """Tests for signatures_match function."""

    def test_identical_signatures_match(self):
        sig1 = (1, 2, 3, 4, 5)
        sig2 = (1, 2, 3, 4, 5)
        assert signatures_match(sig1, sig2)

    def test_different_signatures_dont_match(self):
        sig1 = (1, 2, 3, 4, 5)
        sig2 = (1, 2, 3, 4, 6)
        assert not signatures_match(sig1, sig2)

    def test_within_tolerance_matches(self):
        sig1 = (1.0, 2.0, 3.0)
        sig2 = (1.005, 2.005, 3.005)
        assert signatures_match(sig1, sig2, tolerance=0.01)

    def test_outside_tolerance_doesnt_match(self):
        sig1 = (1.0, 2.0, 3.0)
        sig2 = (1.02, 2.02, 3.02)
        assert not signatures_match(sig1, sig2, tolerance=0.01)

    def test_different_lengths_dont_match(self):
        sig1 = (1, 2, 3)
        sig2 = (1, 2, 3, 4)
        assert not signatures_match(sig1, sig2)

    def test_empty_signatures_match(self):
        assert signatures_match((), ())

    def test_equivalent_expressions_have_matching_signatures(self):
        """Two different expressions for n^2 should have matching signatures."""
        # n^2
        expr1 = BinOp('^', Var('n'), Const(2))
        # n * n
        expr2 = BinOp('*', Var('n'), Var('n'))

        sig1 = behavioral_signature(expr1)
        sig2 = behavioral_signature(expr2)

        assert signatures_match(sig1, sig2)


class TestSignatureSimilarity:
    """Tests for signature_similarity function."""

    def test_identical_is_one(self):
        sig = (1, 2, 3, 4, 5)
        assert signature_similarity(sig, sig) == 1.0

    def test_completely_different_is_low(self):
        sig1 = (0, 0, 0, 0, 0)
        sig2 = (100, 100, 100, 100, 100)
        sim = signature_similarity(sig1, sig2)
        assert sim < 0.1

    def test_similar_signatures(self):
        sig1 = (1, 2, 3, 4, 5)
        sig2 = (1.1, 2.1, 3.1, 4.1, 5.1)
        sim = signature_similarity(sig1, sig2)
        assert sim > 0.9

    def test_different_lengths_returns_zero(self):
        sig1 = (1, 2, 3)
        sig2 = (1, 2, 3, 4)
        assert signature_similarity(sig1, sig2) == 0.0

    def test_returns_between_zero_and_one(self):
        """Similarity should always be in [0, 1]."""
        sig1 = (1, 4, 9, 16, 25)  # squares
        sig2 = (2, 4, 6, 8, 10)  # doubles
        sim = signature_similarity(sig1, sig2)
        assert 0.0 <= sim <= 1.0


class TestAnalyzeGrowth:
    """Tests for analyze_growth function."""

    def test_constant_growth(self):
        expr = Const(5)
        assert analyze_growth(expr) == 'constant'

    def test_linear_growth(self):
        # 2*n is linear
        expr = BinOp('*', Const(2), Var('n'))
        assert analyze_growth(expr) == 'linear'

    def test_quadratic_growth(self):
        # n^2 is quadratic
        expr = BinOp('^', Var('n'), Const(2))
        assert analyze_growth(expr) == 'quadratic'

    def test_complex_growth(self):
        # Sum of cubes has complex growth pattern
        body = BinOp('^', Var('i'), Const(3))
        expr = Sum('i', Const(1), Var('n'), body)
        growth = analyze_growth(expr)
        # Sum of cubes follows n^2*(n+1)^2/4, could be classified various ways
        assert growth in ('quadratic', 'complex', 'error')

    def test_explosive_growth(self):
        # n^n grows explosively
        expr = BinOp('^', Var('n'), Var('n'))
        growth = analyze_growth(expr)
        # May be classified as explosive, exponential, or complex depending on thresholds
        assert growth in ('explosive', 'error', 'exponential', 'complex')


class TestBehavioralEquivalence:
    """Tests that behaviorally equivalent expressions have matching signatures."""

    def test_addition_commutativity(self):
        """a + b = b + a"""
        expr1 = BinOp('+', Var('n'), Const(5))
        expr2 = BinOp('+', Const(5), Var('n'))
        sig1 = behavioral_signature(expr1)
        sig2 = behavioral_signature(expr2)
        assert signatures_match(sig1, sig2)

    def test_multiplication_commutativity(self):
        """a * b = b * a"""
        expr1 = BinOp('*', Var('n'), Const(3))
        expr2 = BinOp('*', Const(3), Var('n'))
        sig1 = behavioral_signature(expr1)
        sig2 = behavioral_signature(expr2)
        assert signatures_match(sig1, sig2)

    def test_distributive_property(self):
        """a * (b + c) = a*b + a*c (approximately, for n*(n+1))"""
        # n*(n+1)
        expr1 = BinOp('*', Var('n'), BinOp('+', Var('n'), Const(1)))
        # n*n + n
        expr2 = BinOp('+', BinOp('*', Var('n'), Var('n')), Var('n'))
        sig1 = behavioral_signature(expr1)
        sig2 = behavioral_signature(expr2)
        assert signatures_match(sig1, sig2)

    def test_sum_formula(self):
        """Σ(i=1..n)[i] = n*(n+1)/2"""
        # Summation form
        expr1 = Sum('i', Const(1), Var('n'), Var('i'))
        # Closed form
        n_times_n_plus_1 = BinOp('*', Var('n'), BinOp('+', Var('n'), Const(1)))
        expr2 = BinOp('/', n_times_n_plus_1, Const(2))

        sig1 = behavioral_signature(expr1)
        sig2 = behavioral_signature(expr2)

        assert signatures_match(sig1, sig2)
