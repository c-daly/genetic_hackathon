"""Shared fixtures for genetic_gp tests."""

import pytest
from genetic_gp.core.expressions import Const, Var, BinOp, Sum, Product
from genetic_gp.tools.library import Tool, ToolLibrary


@pytest.fixture
def simple_const():
    """A simple constant expression."""
    return Const(5)


@pytest.fixture
def simple_var():
    """A simple variable expression."""
    return Var('n')


@pytest.fixture
def double_expr():
    """Expression for 2*n (doubling)."""
    return BinOp('*', Const(2), Var('n'))


@pytest.fixture
def square_expr():
    """Expression for n^2 (squaring)."""
    return BinOp('^', Var('n'), Const(2))


@pytest.fixture
def sum_1_to_n():
    """Sum expression: Σ(i=1..n)[i] = 1+2+...+n"""
    return Sum('i', Const(1), Var('n'), Var('i'))


@pytest.fixture
def factorial_expr():
    """Product expression: ∏(i=1..n)[i] = n!"""
    return Product('i', Const(1), Var('n'), Var('i'))


@pytest.fixture
def empty_tool_library():
    """An empty tool library."""
    return ToolLibrary()


@pytest.fixture
def tool_library_with_double(double_expr):
    """Tool library containing the double tool."""
    lib = ToolLibrary()
    from genetic_gp.core.signatures import behavioral_signature
    sig = behavioral_signature(double_expr)
    tool = Tool(
        name='double',
        expr=double_expr,
        signature=sig,
        params=[],
        metadata={'growth_type': 'linear'},
    )
    lib.add(tool)
    return lib
