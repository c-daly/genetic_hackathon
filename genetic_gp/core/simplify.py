"""Expression simplification to detect and remove no-ops.

Detects degenerate patterns like:
- Single-term loops: Σ(j=n..n)[body] → body with j=n
- Unused loop variables: ∏(k=2..3)[x] where x doesn't use k
- Identity operations: n + 0, n * 1, n ^ 1
"""

from __future__ import annotations
from typing import Any, Set

from genetic_gp.core.expressions import Const, Var, BinOp, Sum, Product


def get_free_variables(expr: Any) -> Set[str]:
    """Get all variable names used in an expression."""
    if isinstance(expr, Const):
        return set()
    elif isinstance(expr, Var):
        return {expr.name}
    elif isinstance(expr, BinOp):
        return get_free_variables(expr.left) | get_free_variables(expr.right)
    elif isinstance(expr, (Sum, Product)):
        # Loop variable is bound, not free
        body_vars = get_free_variables(expr.body)
        free = body_vars - {expr.var}
        free |= get_free_variables(expr.start)
        free |= get_free_variables(expr.end)
        return free
    return set()


def is_constant(expr: Any) -> bool:
    """Check if expression evaluates to the same value regardless of environment."""
    return isinstance(expr, Const) or (
        isinstance(expr, BinOp) and is_constant(expr.left) and is_constant(expr.right)
    )


def has_unused_loop_var(expr: Sum | Product) -> bool:
    """Check if a loop's body doesn't use the loop variable."""
    body_vars = get_free_variables(expr.body)
    return expr.var not in body_vars


def is_single_iteration_loop(expr: Sum | Product) -> bool:
    """Check if loop iterates exactly once (start == end as expressions)."""
    # Check if start and end are structurally identical
    return _exprs_equal(expr.start, expr.end)


def _exprs_equal(a: Any, b: Any) -> bool:
    """Check structural equality of expressions."""
    if type(a) != type(b):
        return False
    if isinstance(a, Const):
        return a.val == b.val
    if isinstance(a, Var):
        return a.name == b.name
    if isinstance(a, BinOp):
        return a.op == b.op and _exprs_equal(a.left, b.left) and _exprs_equal(a.right, b.right)
    if isinstance(a, (Sum, Product)):
        return (a.var == b.var and
                _exprs_equal(a.start, b.start) and
                _exprs_equal(a.end, b.end) and
                _exprs_equal(a.body, b.body))
    return False


def substitute(expr: Any, var: str, replacement: Any) -> Any:
    """Substitute a variable with an expression."""
    if isinstance(expr, Const):
        return expr
    elif isinstance(expr, Var):
        return replacement if expr.name == var else expr
    elif isinstance(expr, BinOp):
        return BinOp(
            expr.op,
            substitute(expr.left, var, replacement),
            substitute(expr.right, var, replacement)
        )
    elif isinstance(expr, Sum):
        if expr.var == var:
            # var is shadowed
            return expr
        return Sum(
            expr.var,
            substitute(expr.start, var, replacement),
            substitute(expr.end, var, replacement),
            substitute(expr.body, var, replacement)
        )
    elif isinstance(expr, Product):
        if expr.var == var:
            return expr
        return Product(
            expr.var,
            substitute(expr.start, var, replacement),
            substitute(expr.end, var, replacement),
            substitute(expr.body, var, replacement)
        )
    return expr


def simplify(expr: Any) -> Any:
    """Simplify an expression by removing no-ops and degenerate patterns.

    Returns a simplified expression, or the original if no simplification applies.
    """
    # First, recursively simplify children
    if isinstance(expr, BinOp):
        left = simplify(expr.left)
        right = simplify(expr.right)
        expr = BinOp(expr.op, left, right)

        # Identity operations
        if expr.op == '+':
            if isinstance(left, Const) and left.val == 0:
                return right
            if isinstance(right, Const) and right.val == 0:
                return left
        elif expr.op == '*':
            if isinstance(left, Const) and left.val == 1:
                return right
            if isinstance(right, Const) and right.val == 1:
                return left
            if isinstance(left, Const) and left.val == 0:
                return Const(0)
            if isinstance(right, Const) and right.val == 0:
                return Const(0)
        elif expr.op == '^':
            if isinstance(right, Const) and right.val == 1:
                return left
            if isinstance(right, Const) and right.val == 0:
                return Const(1)
        elif expr.op == '-':
            if isinstance(right, Const) and right.val == 0:
                return left
        elif expr.op == '/':
            if isinstance(right, Const) and right.val == 1:
                return left

        return expr

    elif isinstance(expr, (Sum, Product)):
        start = simplify(expr.start)
        end = simplify(expr.end)
        body = simplify(expr.body)

        if isinstance(expr, Sum):
            expr = Sum(expr.var, start, end, body)
        else:
            expr = Product(expr.var, start, end, body)

        # Single iteration loop: Σ(j=n..n)[body] → body[j/n]
        if is_single_iteration_loop(expr):
            return substitute(body, expr.var, start)

        # Unused loop variable with constant bounds
        if has_unused_loop_var(expr):
            if isinstance(start, Const) and isinstance(end, Const):
                iterations = int(end.val) - int(start.val) + 1
                if iterations > 0:
                    if isinstance(expr, Sum):
                        # Σ(k=a..b)[x] = x * (b - a + 1)
                        return BinOp('*', body, Const(iterations))
                    else:
                        # ∏(k=a..b)[x] = x ^ (b - a + 1)
                        return BinOp('^', body, Const(iterations))

        return expr

    return expr


def is_degenerate(expr: Any) -> bool:
    """Check if expression contains degenerate patterns (no-ops).

    A degenerate expression is one that could be simplified to something simpler.
    """
    simplified = simplify(expr)

    # Check if simplification changed the expression
    if not _exprs_equal(expr, simplified):
        return True

    # Also check for any unused loop variables or single-iteration loops
    if isinstance(expr, (Sum, Product)):
        if has_unused_loop_var(expr):
            return True
        if is_single_iteration_loop(expr):
            return True
        # Recursively check body
        if is_degenerate(expr.body):
            return True

    if isinstance(expr, BinOp):
        if is_degenerate(expr.left) or is_degenerate(expr.right):
            return True

    return False
