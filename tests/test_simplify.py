"""Tests for expression simplification."""

import pytest
from genetic_gp.core.expressions import Const, Var, BinOp, Sum, Product
from genetic_gp.core.simplify import (
    simplify,
    is_degenerate,
    get_free_variables,
    has_unused_loop_var,
    is_single_iteration_loop,
)


class TestGetFreeVariables:
    """Tests for get_free_variables."""

    def test_const_has_no_vars(self):
        assert get_free_variables(Const(5)) == set()

    def test_var_has_itself(self):
        assert get_free_variables(Var('n')) == {'n'}

    def test_binop_combines_children(self):
        expr = BinOp('+', Var('n'), Var('m'))
        assert get_free_variables(expr) == {'n', 'm'}

    def test_sum_excludes_loop_var(self):
        # Σ(i=1..n)[i] - 'i' is bound, 'n' is free
        expr = Sum('i', Const(1), Var('n'), Var('i'))
        assert get_free_variables(expr) == {'n'}

    def test_product_excludes_loop_var(self):
        # ∏(k=1..n)[k+m] - 'k' is bound, 'n' and 'm' are free
        expr = Product('k', Const(1), Var('n'), BinOp('+', Var('k'), Var('m')))
        assert get_free_variables(expr) == {'n', 'm'}


class TestLoopAnalysis:
    """Tests for loop pattern detection."""

    def test_single_iteration_loop_detected(self):
        # Σ(j=n..n)[body]
        expr = Sum('j', Var('n'), Var('n'), Var('j'))
        assert is_single_iteration_loop(expr)

    def test_multi_iteration_loop_not_single(self):
        # Σ(j=1..n)[body]
        expr = Sum('j', Const(1), Var('n'), Var('j'))
        assert not is_single_iteration_loop(expr)

    def test_unused_loop_var_detected(self):
        # ∏(k=1..3)[n] - k is not used in body
        expr = Product('k', Const(1), Const(3), Var('n'))
        assert has_unused_loop_var(expr)

    def test_used_loop_var_not_detected(self):
        # ∏(k=1..3)[k] - k is used in body
        expr = Product('k', Const(1), Const(3), Var('k'))
        assert not has_unused_loop_var(expr)


class TestSimplify:
    """Tests for expression simplification."""

    def test_identity_add_zero(self):
        # n + 0 -> n
        expr = BinOp('+', Var('n'), Const(0))
        assert simplify(expr) == Var('n')

    def test_identity_zero_add(self):
        # 0 + n -> n
        expr = BinOp('+', Const(0), Var('n'))
        assert simplify(expr) == Var('n')

    def test_identity_mult_one(self):
        # n * 1 -> n
        expr = BinOp('*', Var('n'), Const(1))
        assert simplify(expr) == Var('n')

    def test_identity_one_mult(self):
        # 1 * n -> n
        expr = BinOp('*', Const(1), Var('n'))
        assert simplify(expr) == Var('n')

    def test_mult_by_zero(self):
        # n * 0 -> 0
        expr = BinOp('*', Var('n'), Const(0))
        result = simplify(expr)
        assert isinstance(result, Const) and result.val == 0

    def test_power_of_one(self):
        # n ^ 1 -> n
        expr = BinOp('^', Var('n'), Const(1))
        assert simplify(expr) == Var('n')

    def test_power_of_zero(self):
        # n ^ 0 -> 1
        expr = BinOp('^', Var('n'), Const(0))
        result = simplify(expr)
        assert isinstance(result, Const) and result.val == 1

    def test_single_iteration_sum(self):
        # Σ(j=n..n)[j] -> n (substitute j with n)
        expr = Sum('j', Var('n'), Var('n'), Var('j'))
        assert simplify(expr) == Var('n')

    def test_single_iteration_product(self):
        # ∏(j=n..n)[j*2] -> n*2
        expr = Product('j', Var('n'), Var('n'), BinOp('*', Var('j'), Const(2)))
        result = simplify(expr)
        assert isinstance(result, BinOp)
        assert result.op == '*'

    def test_unused_loop_var_sum_becomes_mult(self):
        # Σ(k=1..3)[n] = n * 3 (3 iterations)
        expr = Sum('k', Const(1), Const(3), Var('n'))
        result = simplify(expr)
        assert isinstance(result, BinOp)
        assert result.op == '*'
        assert isinstance(result.right, Const) and result.right.val == 3

    def test_unused_loop_var_product_becomes_power(self):
        # ∏(k=1..3)[n] = n ^ 3 (3 iterations)
        expr = Product('k', Const(1), Const(3), Var('n'))
        result = simplify(expr)
        assert isinstance(result, BinOp)
        assert result.op == '^'
        assert isinstance(result.right, Const) and result.right.val == 3


class TestIsDegenerate:
    """Tests for degenerate expression detection."""

    def test_single_iteration_is_degenerate(self):
        expr = Sum('j', Var('n'), Var('n'), Var('j'))
        assert is_degenerate(expr)

    def test_unused_loop_var_is_degenerate(self):
        expr = Product('k', Const(1), Const(3), Var('n'))
        assert is_degenerate(expr)

    def test_add_zero_is_degenerate(self):
        expr = BinOp('+', Var('n'), Const(0))
        assert is_degenerate(expr)

    def test_proper_sum_not_degenerate(self):
        # Σ(i=1..n)[i] - proper summation
        expr = Sum('i', Const(1), Var('n'), Var('i'))
        assert not is_degenerate(expr)

    def test_nested_degenerate_detected(self):
        # (n + 0) * 2 - has degenerate subexpression
        inner = BinOp('+', Var('n'), Const(0))
        expr = BinOp('*', inner, Const(2))
        assert is_degenerate(expr)
