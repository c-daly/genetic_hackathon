"""Tests for LaTeX conversion."""

import pytest
from genetic_gp.core.expressions import Const, Var, BinOp, Sum, Product


class TestToLatexBasic:
    """Tests for basic LaTeX conversion."""

    def test_const_to_latex(self):
        from genetic_gp.core.latex import to_latex
        assert to_latex(Const(5)) == "5"
        assert to_latex(Const(3.14)) == "3.14"

    def test_var_to_latex(self):
        from genetic_gp.core.latex import to_latex
        assert to_latex(Var("n")) == "n"

    def test_binop_add_to_latex(self):
        from genetic_gp.core.latex import to_latex
        expr = BinOp("+", Var("n"), Const(1))
        assert to_latex(expr) == "n + 1"

    def test_binop_mult_to_latex(self):
        from genetic_gp.core.latex import to_latex
        expr = BinOp("*", Var("n"), Const(2))
        assert to_latex(expr, pretty=False) == r"n \cdot 2"

    def test_binop_power_to_latex(self):
        from genetic_gp.core.latex import to_latex
        expr = BinOp("^", Var("n"), Const(2))
        assert to_latex(expr) == "n^{2}"

    def test_sum_to_latex(self):
        from genetic_gp.core.latex import to_latex
        expr = Sum("i", Const(1), Var("n"), Var("i"))
        assert to_latex(expr) == r"\sum_{i=1}^{n} i"

    def test_product_to_latex(self):
        from genetic_gp.core.latex import to_latex
        expr = Product("i", Const(1), Var("n"), Var("i"))
        assert to_latex(expr) == r"\prod_{i=1}^{n} i"


class TestToLatexPretty:
    """Tests for pretty LaTeX formatting."""

    def test_coefficient_ordering(self):
        """n * 3 -> 3n"""
        from genetic_gp.core.latex import to_latex
        expr = BinOp("*", Var("n"), Const(3))
        assert to_latex(expr, pretty=True) == "3n"

    def test_identity_mult_removal(self):
        """1 * n -> n"""
        from genetic_gp.core.latex import to_latex
        expr = BinOp("*", Const(1), Var("n"))
        assert to_latex(expr, pretty=True) == "n"

    def test_identity_add_removal(self):
        """n + 0 -> n"""
        from genetic_gp.core.latex import to_latex
        expr = BinOp("+", Var("n"), Const(0))
        assert to_latex(expr, pretty=True) == "n"

    def test_squaring_detection(self):
        """n * n -> n^2"""
        from genetic_gp.core.latex import to_latex
        expr = BinOp("*", Var("n"), Var("n"))
        assert to_latex(expr, pretty=True) == "n^{2}"

    def test_division_as_fraction(self):
        """n / 2 -> \frac{n}{2}"""
        from genetic_gp.core.latex import to_latex
        expr = BinOp("/", Var("n"), Const(2))
        assert to_latex(expr, pretty=True) == r"\frac{n}{2}"

    def test_negative_handling(self):
        """0 - n -> -n"""
        from genetic_gp.core.latex import to_latex
        expr = BinOp("-", Const(0), Var("n"))
        assert to_latex(expr, pretty=True) == "-n"
