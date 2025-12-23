"""Tests for the reporter module."""

import pytest
from genetic_gp.core.expressions import Const, Var, BinOp


class TestReporter:
    """Tests for Reporter class."""

    def test_create_reporter(self):
        """Should create reporter with default config."""
        from genetic_gp.core.reporter import Reporter

        reporter = Reporter()
        assert reporter is not None

    def test_on_new_best_normal_verbosity(self):
        """Should report new best at normal verbosity."""
        from genetic_gp.core.reporter import Reporter
        from genetic_gp.core.config import Verbosity

        reporter = Reporter(verbosity=Verbosity.NORMAL, renderer="plain")
        expr = BinOp("*", Var("n"), Const(2))
        reporter.on_new_best(expr, fitness=0.9, generation=10)

    def test_on_new_best_minimal_verbosity_skips(self):
        """Should skip new_best at minimal verbosity."""
        from genetic_gp.core.reporter import Reporter
        from genetic_gp.core.config import Verbosity

        reporter = Reporter(verbosity=Verbosity.MINIMAL, renderer="plain")
        expr = BinOp("*", Var("n"), Const(2))
        reporter.on_new_best(expr, fitness=0.9, generation=10)

    def test_on_solved(self):
        """Should always report solved."""
        from genetic_gp.core.reporter import Reporter
        from genetic_gp.core.config import Verbosity

        reporter = Reporter(verbosity=Verbosity.MINIMAL, renderer="plain")
        expr = BinOp("+", Var("n"), Var("n"))
        reporter.on_solved(expr, fitness=1.0, generation=25)

    def test_on_simplified(self):
        """Should report simplification."""
        from genetic_gp.core.reporter import Reporter
        from genetic_gp.core.config import Verbosity

        reporter = Reporter(verbosity=Verbosity.MINIMAL, renderer="plain")
        original = BinOp("*", Var("n"), Const(2))
        simplified = BinOp("+", Var("n"), Var("n"))
        reporter.on_simplified(original, simplified)
