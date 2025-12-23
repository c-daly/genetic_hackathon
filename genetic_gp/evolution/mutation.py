"""Mutation operators for genetic programming."""

from __future__ import annotations
import random
from typing import Any, List

from genetic_gp.core.expressions import Const, Var, BinOp, Sum, Product, ToolCall
from genetic_gp.evolution.generator import random_expr


def mutate(
    expr: Any,
    rate: float = 0.3,
    vars_available: List[str] | None = None,
    tool_library: Any | None = None,
) -> Any:
    """Mutate an expression tree.

    Args:
        expr: Expression to mutate
        rate: Probability of replacing a subtree with random expression
        vars_available: Variables available for generation
        tool_library: Optional ToolLibrary for generating tool calls

    Returns:
        Mutated expression (may be same object if no mutation occurred)
    """
    if vars_available is None:
        vars_available = ['n']

    # Random replacement of entire subtree
    if random.random() < rate:
        return random_expr(0, 3, vars_available, tool_library)

    # Structural mutation based on expression type
    if isinstance(expr, Const):
        return Const(expr.val + random.uniform(-1, 1))

    elif isinstance(expr, Var):
        # Variables don't mutate (could add variable swapping later)
        return expr

    elif isinstance(expr, BinOp):
        return BinOp(
            expr.op,
            mutate(expr.left, rate, vars_available, tool_library),
            mutate(expr.right, rate, vars_available, tool_library),
        )

    elif isinstance(expr, Sum):
        return Sum(
            expr.var,
            mutate(expr.start, rate, vars_available, tool_library),
            mutate(expr.end, rate, vars_available, tool_library),
            mutate(expr.body, rate, vars_available + [expr.var], tool_library),
        )

    elif isinstance(expr, Product):
        return Product(
            expr.var,
            mutate(expr.start, rate, vars_available, tool_library),
            mutate(expr.end, rate, vars_available, tool_library),
            mutate(expr.body, rate, vars_available + [expr.var], tool_library),
        )

    elif isinstance(expr, ToolCall):
        return ToolCall(
            expr.tool_name,
            [mutate(arg, rate, vars_available, tool_library) for arg in expr.args],
            expr.tool_library,
        )

    # Unknown type - return as-is
    return expr


def crossover(
    parent1: Any,
    parent2: Any,
    vars_available: List[str] | None = None,
) -> Any:
    """Perform crossover between two parent expressions.

    Selects a random subtree from parent2 and inserts it at a random
    position in parent1.

    Args:
        parent1: First parent expression
        parent2: Second parent expression
        vars_available: Variables available

    Returns:
        Child expression combining elements from both parents
    """
    if vars_available is None:
        vars_available = ['n']

    # Get a random subtree from parent2
    donor = _random_subtree(parent2)

    # Replace a random subtree in parent1 with the donor
    return _replace_random_subtree(parent1, donor, vars_available)


def _random_subtree(expr: Any) -> Any:
    """Select a random subtree from an expression."""
    subtrees = _collect_subtrees(expr)
    return random.choice(subtrees)


def _collect_subtrees(expr: Any) -> List[Any]:
    """Collect all subtrees of an expression."""
    result = [expr]

    if isinstance(expr, BinOp):
        result.extend(_collect_subtrees(expr.left))
        result.extend(_collect_subtrees(expr.right))
    elif isinstance(expr, (Sum, Product)):
        result.extend(_collect_subtrees(expr.start))
        result.extend(_collect_subtrees(expr.end))
        result.extend(_collect_subtrees(expr.body))
    elif isinstance(expr, ToolCall):
        for arg in expr.args:
            result.extend(_collect_subtrees(arg))

    return result


def _replace_random_subtree(
    expr: Any,
    replacement: Any,
    vars_available: List[str],
    prob: float = 0.3,
) -> Any:
    """Replace a random subtree with the replacement expression."""
    if random.random() < prob:
        return replacement

    if isinstance(expr, (Const, Var)):
        return expr

    elif isinstance(expr, BinOp):
        return BinOp(
            expr.op,
            _replace_random_subtree(expr.left, replacement, vars_available, prob),
            _replace_random_subtree(expr.right, replacement, vars_available, prob),
        )

    elif isinstance(expr, Sum):
        return Sum(
            expr.var,
            _replace_random_subtree(expr.start, replacement, vars_available, prob),
            _replace_random_subtree(expr.end, replacement, vars_available, prob),
            _replace_random_subtree(expr.body, replacement, vars_available + [expr.var], prob),
        )

    elif isinstance(expr, Product):
        return Product(
            expr.var,
            _replace_random_subtree(expr.start, replacement, vars_available, prob),
            _replace_random_subtree(expr.end, replacement, vars_available, prob),
            _replace_random_subtree(expr.body, replacement, vars_available + [expr.var], prob),
        )

    elif isinstance(expr, ToolCall):
        return ToolCall(
            expr.tool_name,
            [_replace_random_subtree(arg, replacement, vars_available, prob) for arg in expr.args],
            expr.tool_library,
        )

    return expr
