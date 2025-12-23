"""LaTeX conversion for mathematical expressions."""

from typing import Any
from genetic_gp.core.expressions import Const, Var, BinOp, Sum, Product, PrimitiveCall


def to_latex(expr: Any, pretty: bool = True) -> str:
    """
    Convert an expression to LaTeX format.

    Args:
        expr: The expression to convert (Const, Var, BinOp, Sum, Product, or ToolCall)
        pretty: If True, apply pretty formatting rules (coefficient ordering, identity removal, etc.)

    Returns:
        LaTeX string representation of the expression
    """
    # Convert to base LaTeX
    if isinstance(expr, Const):
        latex = _const_to_latex(expr)
    elif isinstance(expr, Var):
        latex = _var_to_latex(expr)
    elif isinstance(expr, BinOp):
        latex = _binop_to_latex(expr, pretty)
    elif isinstance(expr, Sum):
        latex = _sum_to_latex(expr, pretty)
    elif isinstance(expr, Product):
        latex = _product_to_latex(expr, pretty)
    elif isinstance(expr, PrimitiveCall):
        latex = _primitivecall_to_latex(expr, pretty)
    else:
        latex = str(expr)

    # Apply pretty formatting rules if requested
    if pretty:
        latex = _apply_pretty_rules(expr, latex)

    return latex


def _const_to_latex(expr: Const) -> str:
    """Convert a constant to LaTeX."""
    if expr.val == int(expr.val):
        return str(int(expr.val))
    # Round floats to 2 decimal places for cleaner display
    return str(round(expr.val, 2))


def _var_to_latex(expr: Var) -> str:
    """Convert a variable to LaTeX."""
    return expr.name


def _binop_to_latex(expr: BinOp, pretty: bool) -> str:
    """Convert a binary operation to LaTeX."""
    left_latex = to_latex(expr.left, pretty)
    right_latex = to_latex(expr.right, pretty)

    # Handle different operators
    if expr.op == '+':
        return f"{left_latex} + {right_latex}"
    elif expr.op == '-':
        return f"{left_latex} - {right_latex}"
    elif expr.op == '*':
        return f"{left_latex} \\cdot {right_latex}"
    elif expr.op == '/':
        return f"{left_latex} / {right_latex}"
    elif expr.op == '^':
        return f"{left_latex}^{{{right_latex}}}"
    else:
        return f"{left_latex} {expr.op} {right_latex}"


def _sum_to_latex(expr: Sum, pretty: bool) -> str:
    """Convert a summation to LaTeX."""
    var = expr.var
    start_latex = to_latex(expr.start, pretty)
    end_latex = to_latex(expr.end, pretty)
    body_latex = to_latex(expr.body, pretty)
    return f"\\sum_{{{var}={start_latex}}}^{{{end_latex}}} {body_latex}"


def _product_to_latex(expr: Product, pretty: bool) -> str:
    """Convert a product to LaTeX."""
    var = expr.var
    start_latex = to_latex(expr.start, pretty)
    end_latex = to_latex(expr.end, pretty)
    body_latex = to_latex(expr.body, pretty)
    return f"\\prod_{{{var}={start_latex}}}^{{{end_latex}}} {body_latex}"


def _primitivecall_to_latex(expr: PrimitiveCall, pretty: bool) -> str:
    """Convert a primitive call to LaTeX."""
    arg_latex = to_latex(expr.arg, pretty) if hasattr(expr.arg, 'eval') else str(expr.arg)
    return f"\\text{{{expr.primitive_name}}}({arg_latex})"


def _apply_pretty_rules(expr: Any, latex: str) -> str:
    """
    Apply pretty formatting rules to LaTeX output.

    Rules:
    1. Coefficient ordering: n * 3 -> 3n
    2. Identity multiplication removal: 1 * n -> n
    3. Identity addition removal: n + 0 -> n or 0 + n -> n
    4. Squaring detection: n * n -> n^2
    5. Division as fraction: n / 2 -> \frac{n}{2}
    6. Negative handling: 0 - n -> -n
    """
    if not isinstance(expr, BinOp):
        return latex

    # Get sub-expressions
    left = expr.left
    right = expr.right
    left_latex = to_latex(left, pretty=True)
    right_latex = to_latex(right, pretty=True)

    # Rule: Division as fraction (n / 2 -> \frac{n}{2})
    if expr.op == '/':
        return f"\\frac{{{left_latex}}}{{{right_latex}}}"

    # Rule: Negative handling (0 - n -> -n)
    if expr.op == '-' and isinstance(left, Const) and left.val == 0:
        return f"-{right_latex}"

    # Rule: Identity addition removal (n + 0 -> n, 0 + n -> n)
    if expr.op == '+':
        if isinstance(right, Const) and right.val == 0:
            return left_latex
        if isinstance(left, Const) and left.val == 0:
            return right_latex

    # Rule: Squaring detection (n * n -> n^2)
    if expr.op == '*' and _exprs_equal(left, right):
        return f"{left_latex}^{{2}}"

    # Rule: Identity multiplication removal (1 * n -> n, n * 1 -> n)
    if expr.op == '*':
        if isinstance(left, Const) and left.val == 1:
            return right_latex
        if isinstance(right, Const) and right.val == 1:
            return left_latex

    # Rule: Coefficient ordering (var * const -> const * var, then format as const·var or just const-var)
    if expr.op == '*':
        # Check if we have var * const pattern
        if isinstance(left, Var) and isinstance(right, Const):
            # Reorder to const * var and format compactly
            const_latex = _const_to_latex(right)
            var_latex = _var_to_latex(left)
            return f"{const_latex}{var_latex}"
        # Check if we have const * var pattern (already ordered)
        if isinstance(left, Const) and isinstance(right, Var):
            const_latex = _const_to_latex(left)
            var_latex = _var_to_latex(right)
            return f"{const_latex}{var_latex}"

    return latex


def _exprs_equal(expr1: Any, expr2: Any) -> bool:
    """
    Check if two expressions are structurally equal.

    This is a simple structural equality check, not semantic equality.
    """
    if type(expr1) != type(expr2):
        return False

    if isinstance(expr1, Const):
        return expr1.val == expr2.val

    if isinstance(expr1, Var):
        return expr1.name == expr2.name

    if isinstance(expr1, BinOp):
        return (expr1.op == expr2.op and
                _exprs_equal(expr1.left, expr2.left) and
                _exprs_equal(expr1.right, expr2.right))

    if isinstance(expr1, Sum):
        return (expr1.var == expr2.var and
                _exprs_equal(expr1.start, expr2.start) and
                _exprs_equal(expr1.end, expr2.end) and
                _exprs_equal(expr1.body, expr2.body))

    if isinstance(expr1, Product):
        return (expr1.var == expr2.var and
                _exprs_equal(expr1.start, expr2.start) and
                _exprs_equal(expr1.end, expr2.end) and
                _exprs_equal(expr1.body, expr2.body))

    return False
