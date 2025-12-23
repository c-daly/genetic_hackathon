"""Tests for core/expressions.py - Expression eval and complexity."""

import pytest
from genetic_gp.core.expressions import Const, Var, BinOp, Sum, Product, ToolCall, Expression


class TestConst:
    """Tests for Const expression type."""

    def test_eval_returns_value(self):
        c = Const(42)
        assert c.eval({}) == 42

    def test_eval_ignores_env(self):
        c = Const(5)
        assert c.eval({'n': 100, 'x': 200}) == 5

    def test_complexity_is_one(self):
        c = Const(999)
        assert c.complexity() == 1

    def test_float_values(self):
        c = Const(3.14)
        assert abs(c.eval({}) - 3.14) < 0.01

    def test_repr_integer(self):
        c = Const(5.0)
        assert repr(c) == '5'

    def test_repr_float(self):
        c = Const(3.14159)
        assert '3.14' in repr(c)


class TestVar:
    """Tests for Var expression type."""

    def test_eval_returns_env_value(self):
        v = Var('n')
        assert v.eval({'n': 10}) == 10

    def test_eval_returns_zero_for_missing(self):
        v = Var('x')
        assert v.eval({'n': 10}) == 0

    def test_complexity_is_one(self):
        v = Var('anything')
        assert v.complexity() == 1

    def test_repr(self):
        v = Var('myvar')
        assert repr(v) == 'myvar'


class TestBinOp:
    """Tests for BinOp expression type."""

    def test_addition(self):
        expr = BinOp('+', Const(3), Const(4))
        assert expr.eval({}) == 7

    def test_subtraction(self):
        expr = BinOp('-', Const(10), Const(4))
        assert expr.eval({}) == 6

    def test_multiplication(self):
        expr = BinOp('*', Const(3), Const(4))
        assert expr.eval({}) == 12

    def test_division(self):
        expr = BinOp('/', Const(10), Const(4))
        assert expr.eval({}) == 2.5

    def test_division_by_near_zero_returns_zero(self):
        expr = BinOp('/', Const(10), Const(0.0001))
        assert expr.eval({}) == 0

    def test_power(self):
        expr = BinOp('^', Const(2), Const(3))
        assert expr.eval({}) == 8

    def test_power_capped_at_10(self):
        expr = BinOp('^', Const(2), Const(100))
        # Should cap exponent to 10, so 2^10 = 1024
        assert expr.eval({}) == 1024

    def test_nested_expression(self):
        # (3 + 4) * 2 = 14
        inner = BinOp('+', Const(3), Const(4))
        outer = BinOp('*', inner, Const(2))
        assert outer.eval({}) == 14

    def test_with_variables(self):
        # n * 2
        expr = BinOp('*', Var('n'), Const(2))
        assert expr.eval({'n': 5}) == 10

    def test_complexity_sum_of_children_plus_one(self):
        # BinOp(Const, Const) = 1 + 1 + 1 = 3
        expr = BinOp('+', Const(1), Const(2))
        assert expr.complexity() == 3

    def test_complexity_nested(self):
        # BinOp(BinOp(Const, Const), Const) = 1 + (1+1+1) + 1 = 5
        inner = BinOp('+', Const(1), Const(2))
        outer = BinOp('*', inner, Const(3))
        assert outer.complexity() == 5

    def test_repr(self):
        expr = BinOp('+', Var('n'), Const(1))
        assert repr(expr) == '(n+1)'

    def test_handles_overflow(self):
        # Very large exponent should not crash
        expr = BinOp('^', Const(10), Const(10))
        result = expr.eval({})
        assert isinstance(result, (int, float))


class TestSum:
    """Tests for Sum expression type."""

    def test_sum_1_to_5(self):
        # Σ(i=1..5)[i] = 1+2+3+4+5 = 15
        expr = Sum('i', Const(1), Const(5), Var('i'))
        assert expr.eval({}) == 15

    def test_sum_1_to_n(self):
        # Σ(i=1..n)[i] = n(n+1)/2
        expr = Sum('i', Const(1), Var('n'), Var('i'))
        assert expr.eval({'n': 5}) == 15
        assert expr.eval({'n': 10}) == 55

    def test_sum_of_squares(self):
        # Σ(i=1..n)[i^2]
        body = BinOp('^', Var('i'), Const(2))
        expr = Sum('i', Const(1), Var('n'), body)
        # 1 + 4 + 9 = 14 for n=3
        assert expr.eval({'n': 3}) == 14

    def test_empty_sum(self):
        # Σ(i=5..1)[i] = 0 (empty range)
        expr = Sum('i', Const(5), Const(1), Var('i'))
        assert expr.eval({}) == 0

    def test_iteration_capped_at_100(self):
        # Σ(i=1..1000)[i] should cap at 100 iterations
        expr = Sum('i', Const(1), Const(1000), Var('i'))
        # Sum of 1..100 = 5050
        assert expr.eval({}) == 5050

    def test_complexity(self):
        # 3 + start + end + body = 3 + 1 + 1 + 1 = 6
        expr = Sum('i', Const(1), Var('n'), Var('i'))
        assert expr.complexity() == 6

    def test_repr(self):
        expr = Sum('i', Const(1), Var('n'), Var('i'))
        r = repr(expr)
        assert 'Σ' in r
        assert 'i=' in r


class TestProduct:
    """Tests for Product expression type."""

    def test_product_1_to_5(self):
        # ∏(i=1..5)[i] = 1*2*3*4*5 = 120
        expr = Product('i', Const(1), Const(5), Var('i'))
        assert expr.eval({}) == 120

    def test_factorial(self):
        # ∏(i=1..n)[i] = n!
        expr = Product('i', Const(1), Var('n'), Var('i'))
        assert expr.eval({'n': 5}) == 120
        assert expr.eval({'n': 3}) == 6

    def test_empty_product(self):
        # ∏(i=5..1)[i] = 1 (empty range, multiplicative identity)
        expr = Product('i', Const(5), Const(1), Var('i'))
        assert expr.eval({}) == 1

    def test_complexity(self):
        # 3 + start + end + body = 3 + 1 + 1 + 1 = 6
        expr = Product('i', Const(1), Var('n'), Var('i'))
        assert expr.complexity() == 6

    def test_repr(self):
        expr = Product('i', Const(1), Var('n'), Var('i'))
        r = repr(expr)
        assert '∏' in r


class TestExpressionProtocol:
    """Tests that expression types implement the Protocol correctly."""

    def test_const_is_expression(self):
        assert isinstance(Const(1), Expression)

    def test_var_is_expression(self):
        assert isinstance(Var('n'), Expression)

    def test_binop_is_expression(self):
        assert isinstance(BinOp('+', Const(1), Const(2)), Expression)

    def test_sum_is_expression(self):
        assert isinstance(Sum('i', Const(1), Const(5), Var('i')), Expression)

    def test_product_is_expression(self):
        assert isinstance(Product('i', Const(1), Const(5), Var('i')), Expression)


class TestComplexExpressions:
    """Tests for more complex expression compositions."""

    def test_double_expression(self, double_expr):
        """2*n should double the input."""
        assert double_expr.eval({'n': 0}) == 0
        assert double_expr.eval({'n': 5}) == 10
        assert double_expr.eval({'n': -3}) == -6

    def test_square_expression(self, square_expr):
        """n^2 should square the input."""
        assert square_expr.eval({'n': 0}) == 0
        assert square_expr.eval({'n': 3}) == 9
        assert square_expr.eval({'n': 5}) == 25

    def test_sum_1_to_n_expression(self, sum_1_to_n):
        """Σ(i=1..n)[i] should sum 1 to n."""
        assert sum_1_to_n.eval({'n': 1}) == 1
        assert sum_1_to_n.eval({'n': 5}) == 15
        assert sum_1_to_n.eval({'n': 10}) == 55

    def test_factorial_expression(self, factorial_expr):
        """∏(i=1..n)[i] should compute n!."""
        assert factorial_expr.eval({'n': 1}) == 1
        assert factorial_expr.eval({'n': 5}) == 120
        assert factorial_expr.eval({'n': 6}) == 720

    def test_deeply_nested(self):
        """Test a deeply nested expression."""
        # ((n + 1) * (n - 1)) = n^2 - 1
        n_plus_1 = BinOp('+', Var('n'), Const(1))
        n_minus_1 = BinOp('-', Var('n'), Const(1))
        expr = BinOp('*', n_plus_1, n_minus_1)

        for n in range(10):
            expected = n * n - 1
            assert expr.eval({'n': n}) == expected
