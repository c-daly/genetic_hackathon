"""Pattern extraction for creating generalized tools.

Generalization recognizes common patterns in discovered expressions
and extracts them as parameterized tools that can be reused with
different parameter values.

Example patterns:
- n^k → power(exp) - can be instantiated as square, cube, etc.
- n*k → scale(factor) - can be instantiated as double, triple, etc.
- Σ(i=1..n)[i^k] → sum_powers(k) - works for any power
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, List, Tuple

from genetic_gp.core.expressions import Const, Var, BinOp, Sum, Product
from genetic_gp.core.signatures import behavioral_signature
from genetic_gp.tools.library import Tool


@dataclass
class GeneralizedPattern:
    """A recognized pattern that can be parameterized.

    Attributes:
        name: Name for the generalized tool (e.g., 'power', 'scale')
        params: List of parameter names
        template: Expression template with parameter variables
        original_expr: The specific expression this was extracted from
        description: Human-readable description
    """
    name: str
    params: List[str]
    template: Any  # Expression
    original_expr: Any  # Expression
    description: str = ""

    def create_tool(self) -> Tool:
        """Create a Tool from this generalized pattern."""
        sig = behavioral_signature(self.template)
        return Tool(
            name=self.name,
            expr=self.template,
            signature=sig,
            params=self.params,
            metadata={
                'generalized_from': str(self.original_expr),
                'description': self.description,
            },
        )


def generalize_pattern(expr: Any) -> GeneralizedPattern | None:
    """Extract generalized pattern from a specific expression.

    Recognizes common mathematical patterns and extracts them as
    parameterized templates.

    Args:
        expr: Expression to analyze

    Returns:
        GeneralizedPattern if a pattern is recognized, None otherwise

    Recognized patterns:
    - n^constant → power(exp)
    - constant*n or n*constant → scale(factor)
    - Σ(i=1..n)[i^constant] → sum_powers(k)
    - ∏(i=1..n)[constant] → power_of(base)
    """

    # Pattern 1: n^constant → power(exp)
    if isinstance(expr, BinOp) and expr.op == '^':
        if isinstance(expr.left, Var) and isinstance(expr.right, Const):
            # Generalize: base^exp where exp is a parameter
            template = BinOp('^', Var('n'), Var('exp'))
            return GeneralizedPattern(
                name='power',
                params=['exp'],
                template=template,
                original_expr=expr,
                description=f"Raises n to power exp (from n^{int(expr.right.val)})",
            )

    # Pattern 2: n*constant or constant*n → scale(factor)
    if isinstance(expr, BinOp) and expr.op == '*':
        if isinstance(expr.left, Var) and isinstance(expr.right, Const):
            template = BinOp('*', Var('n'), Var('factor'))
            return GeneralizedPattern(
                name='scale',
                params=['factor'],
                template=template,
                original_expr=expr,
                description=f"Multiplies n by factor (from n*{int(expr.right.val)})",
            )
        if isinstance(expr.left, Const) and isinstance(expr.right, Var):
            template = BinOp('*', Var('factor'), Var('n'))
            return GeneralizedPattern(
                name='scale',
                params=['factor'],
                template=template,
                original_expr=expr,
                description=f"Multiplies n by factor (from {int(expr.left.val)}*n)",
            )

    # Pattern 3: n+constant → shift(offset)
    if isinstance(expr, BinOp) and expr.op == '+':
        if isinstance(expr.left, Var) and isinstance(expr.right, Const):
            template = BinOp('+', Var('n'), Var('offset'))
            return GeneralizedPattern(
                name='shift',
                params=['offset'],
                template=template,
                original_expr=expr,
                description=f"Adds offset to n (from n+{int(expr.right.val)})",
            )

    # Pattern 4: Σ(i=1..n)[i^k] → sum_powers(k)
    if isinstance(expr, Sum):
        if (isinstance(expr.start, Const) and expr.start.val == 1 and
                isinstance(expr.end, Var)):
            # Check if body is i^k
            if (isinstance(expr.body, BinOp) and expr.body.op == '^' and
                    isinstance(expr.body.left, Var) and
                    expr.body.left.name == expr.var and
                    isinstance(expr.body.right, Const)):
                power = int(expr.body.right.val)
                template = Sum(
                    'i',
                    Const(1),
                    Var('n'),
                    BinOp('^', Var('i'), Var('k')),
                )
                return GeneralizedPattern(
                    name='sum_powers',
                    params=['k'],
                    template=template,
                    original_expr=expr,
                    description=f"Sum of i^k from 1 to n (from sum of i^{power})",
                )

    # Pattern 5: Σ(i=1..n)[i] → triangular (no params, structural pattern)
    if isinstance(expr, Sum):
        if (isinstance(expr.start, Const) and expr.start.val == 1 and
                isinstance(expr.end, Var) and
                isinstance(expr.body, Var) and expr.body.name == expr.var):
            # This is already general - triangular numbers
            # Return None to keep as-is rather than over-generalizing
            return None

    # Pattern 6: ∏(i=1..n)[i] → factorial (structural, no generalization)
    if isinstance(expr, Product):
        if (isinstance(expr.start, Const) and expr.start.val == 1 and
                isinstance(expr.end, Var) and
                isinstance(expr.body, Var) and expr.body.name == expr.var):
            # This is factorial - already general
            return None

    # Pattern 7: ∏(i=1..n)[constant] → power_of(base)
    if isinstance(expr, Product):
        if (isinstance(expr.start, Const) and expr.start.val == 1 and
                isinstance(expr.end, Var) and
                isinstance(expr.body, Const)):
            base = int(expr.body.val)
            template = Product(
                'i',
                Const(1),
                Var('n'),
                Var('base'),
            )
            return GeneralizedPattern(
                name='power_of',
                params=['base'],
                template=template,
                original_expr=expr,
                description=f"Raises base to power n (from {base}^n)",
            )

    return None


def try_generalize_and_save(
    expr: Any,
    library: Any,  # ToolLibrary
    min_fitness: float = 0.95,
    fitness: float = 1.0,
) -> Tool | None:
    """Try to generalize an expression and save as a tool.

    Args:
        expr: Expression to generalize
        library: ToolLibrary to add the tool to
        min_fitness: Minimum fitness required
        fitness: Actual fitness of the expression

    Returns:
        Tool if generalized and added, None otherwise
    """
    if fitness < min_fitness:
        return None

    pattern = generalize_pattern(expr)
    if pattern is None:
        return None

    tool = pattern.create_tool()

    # Check if novel
    if not library.is_novel(tool.expr):
        return None

    if library.add(tool):
        return tool

    return None


def extract_all_patterns(expr: Any) -> List[GeneralizedPattern]:
    """Extract all recognizable patterns from an expression tree.

    Recursively walks the expression tree and collects all patterns found.

    Args:
        expr: Root expression to analyze

    Returns:
        List of all GeneralizedPattern objects found
    """
    patterns = []

    # Try to generalize this node
    pattern = generalize_pattern(expr)
    if pattern is not None:
        patterns.append(pattern)

    # Recurse into children
    if isinstance(expr, BinOp):
        patterns.extend(extract_all_patterns(expr.left))
        patterns.extend(extract_all_patterns(expr.right))
    elif isinstance(expr, (Sum, Product)):
        patterns.extend(extract_all_patterns(expr.start))
        patterns.extend(extract_all_patterns(expr.end))
        patterns.extend(extract_all_patterns(expr.body))

    return patterns
