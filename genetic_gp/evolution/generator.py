"""Random expression generation for genetic programming."""

from __future__ import annotations
import random
from typing import Any, List

from genetic_gp.core.expressions import Const, Var, BinOp, Sum, Product, PrimitiveCall


def random_expr(
    depth: int = 0,
    max_depth: int = 3,
    vars_available: List[str] | None = None,
    tool_library: Any | None = None,
    include_product: bool = True,
    terminal_prob: float = 0.4,
) -> Any:
    """Generate a random mathematical expression.

    Args:
        depth: Current recursion depth
        max_depth: Maximum expression depth
        vars_available: Variable names that can be used (default: ['n'])
        tool_library: Optional ToolLibrary for generating tool calls
        include_product: Whether to include Product expressions
        terminal_prob: Probability of generating a terminal at any depth

    Returns:
        A random Expression
    """
    if vars_available is None:
        vars_available = ['n']

    # Terminal condition: at max depth or random early termination
    if depth >= max_depth or random.random() < terminal_prob:
        return _random_terminal(vars_available, tool_library, depth, max_depth)

    # Choose expression type
    choices = ['binop', 'sum']
    if include_product:
        choices.append('product')

    choice = random.choice(choices)

    if choice == 'binop':
        return _random_binop(depth, max_depth, vars_available, tool_library, include_product, terminal_prob)
    elif choice == 'sum':
        return _random_sum(depth, max_depth, vars_available, tool_library, include_product, terminal_prob)
    elif choice == 'product':
        return _random_product(depth, max_depth, vars_available, tool_library, include_product, terminal_prob)

    # Fallback
    return _random_terminal(vars_available, tool_library, depth, max_depth)


def _random_terminal(
    vars_available: List[str],
    tool_library: Any | None,
    depth: int,
    max_depth: int,
) -> Any:
    """Generate a random terminal (constant, variable, or tool call)."""
    choices = ['const', 'var']

    # Can use a tool if library exists and has tools
    if tool_library is not None:
        tools = tool_library.list_tools()
        if tools and random.random() < 0.3:
            choices.append('tool')

    choice = random.choice(choices)

    if choice == 'const':
        return Const(random.randint(0, 5))
    elif choice == 'var':
        return Var(random.choice(vars_available))
    elif choice == 'tool':
        primitives = tool_library.list_primitives()
        primitive = random.choice(primitives)
        # Generate the input argument (typically n or an expression of n)
        arg = random_expr(depth + 1, max_depth, vars_available, tool_library)
        return PrimitiveCall(primitive.name, arg, tool_library)

    return Const(0)


def _random_binop(
    depth: int,
    max_depth: int,
    vars_available: List[str],
    tool_library: Any | None,
    include_product: bool,
    terminal_prob: float,
) -> BinOp:
    """Generate a random binary operation."""
    op = random.choice(['+', '-', '*', '/', '^'])
    left = random_expr(depth + 1, max_depth, vars_available, tool_library, include_product, terminal_prob)
    right = random_expr(depth + 1, max_depth, vars_available, tool_library, include_product, terminal_prob)
    return BinOp(op, left, right)


def _random_sum(
    depth: int,
    max_depth: int,
    vars_available: List[str],
    tool_library: Any | None,
    include_product: bool,
    terminal_prob: float,
) -> Sum:
    """Generate a random summation."""
    loop_var = random.choice(['i', 'j', 'k'])
    start = random_expr(depth + 1, max_depth, vars_available, tool_library, include_product, terminal_prob)
    end = random_expr(depth + 1, max_depth, vars_available, tool_library, include_product, terminal_prob)
    # Body can use the loop variable
    body_vars = vars_available + [loop_var]
    body = random_expr(depth + 1, max_depth, body_vars, tool_library, include_product, terminal_prob)
    return Sum(loop_var, start, end, body)


def _random_product(
    depth: int,
    max_depth: int,
    vars_available: List[str],
    tool_library: Any | None,
    include_product: bool,
    terminal_prob: float,
) -> Product:
    """Generate a random product."""
    loop_var = random.choice(['i', 'j', 'k'])
    start = random_expr(depth + 1, max_depth, vars_available, tool_library, include_product, terminal_prob)
    end = random_expr(depth + 1, max_depth, vars_available, tool_library, include_product, terminal_prob)
    # Body can use the loop variable
    body_vars = vars_available + [loop_var]
    body = random_expr(depth + 1, max_depth, body_vars, tool_library, include_product, terminal_prob)
    return Product(loop_var, start, end, body)
