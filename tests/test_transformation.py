"""Tests for transformation discovery and application."""

from genetic_gp.core.expressions import BinOp, Const, Var
from genetic_gp.tools.transformation import (
    TransformationLibrary,
    discover_transformations_from_solutions,
)


def test_transformation_discovery_simplifies_equivalent_expression():
    """Should discover and apply a simplifying transformation."""
    # n * n * n vs n ^ 3
    complex_expr = BinOp('*', Var('n'), BinOp('*', Var('n'), Var('n')))
    simple_expr = BinOp('^', Var('n'), Const(3))

    library = TransformationLibrary()
    trans = library.discover(complex_expr, simple_expr, min_reduction=2)

    assert trans is not None
    assert trans.to_expr == simple_expr
    assert trans.complexity_reduction >= 2

    assert library.add(trans) is True
    simplified = library.try_simplify(complex_expr)
    assert repr(simplified) == repr(simple_expr)


def test_discover_transformations_from_solutions_adds_rule():
    """Should discover transformations from solution pairs."""
    complex_expr = BinOp('*', Var('n'), BinOp('*', Var('n'), Var('n')))
    simple_expr = BinOp('^', Var('n'), Const(3))

    library = TransformationLibrary()
    solutions = [
        (complex_expr, 0.9),
        (simple_expr, 0.95),
    ]

    discovered = discover_transformations_from_solutions(
        solutions,
        library,
        min_fitness=0.5,
        min_reduction=2,
    )

    assert discovered == 1
    assert len(library) == 1
