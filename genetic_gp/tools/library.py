"""Tool library for storing and reusing discovered patterns."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from genetic_gp.core.expressions import Const, Var, BinOp, Sum, Product
from genetic_gp.core.signatures import behavioral_signature, signature_similarity


def _extract_pattern(expr: Any) -> tuple[Any, Dict[str, float]] | None:
    """Extract a generalizable pattern from an expression.

    Recognizes patterns like:
    - n * 2 → n * k (with k=2)
    - n ^ 3 → n ^ k (with k=3)
    - n + 5 → n + k (with k=5)
    - 2 * n → k * n (with k=2)

    Returns:
        (generalized_expr, param_values) or None if not generalizable
    """
    if not isinstance(expr, BinOp):
        return None

    # Check for patterns: var OP const or const OP var
    left_is_var = isinstance(expr.left, Var) and expr.left.name == 'n'
    right_is_var = isinstance(expr.right, Var) and expr.right.name == 'n'
    left_is_const = isinstance(expr.left, Const)
    right_is_const = isinstance(expr.right, Const)

    if left_is_var and right_is_const:
        # n OP k pattern
        k_val = expr.right.val
        generalized = BinOp(expr.op, Var('n'), Var('k'))
        return generalized, {'k': k_val}
    elif left_is_const and right_is_var:
        # k OP n pattern
        k_val = expr.left.val
        generalized = BinOp(expr.op, Var('k'), Var('n'))
        return generalized, {'k': k_val}

    return None


def _match_pattern(expr: Any, pattern: Any) -> Dict[str, float] | None:
    """Check if expr matches a generalized pattern.

    Returns parameter values if match, None otherwise.
    """
    if type(expr) != type(pattern):
        return None

    if isinstance(expr, Const):
        return {} if expr.val == pattern.val else None

    if isinstance(expr, Var):
        if pattern.name == 'k':
            # This is a parameter - expr should be a constant
            return None  # Var can't match param
        return {} if expr.name == pattern.name else None

    if isinstance(expr, BinOp):
        if expr.op != pattern.op:
            return None

        # Check if pattern has parameter in left or right
        if isinstance(pattern.left, Var) and pattern.left.name == 'k':
            if isinstance(expr.left, Const):
                right_match = _match_pattern(expr.right, pattern.right)
                if right_match is not None:
                    return {'k': expr.left.val, **right_match}
            return None

        if isinstance(pattern.right, Var) and pattern.right.name == 'k':
            if isinstance(expr.right, Const):
                left_match = _match_pattern(expr.left, pattern.left)
                if left_match is not None:
                    return {'k': expr.right.val, **left_match}
            return None

        # No parameters - must match exactly
        left_match = _match_pattern(expr.left, pattern.left)
        right_match = _match_pattern(expr.right, pattern.right)
        if left_match is not None and right_match is not None:
            return {**left_match, **right_match}

    return None


@dataclass
class Tool:
    """A discovered computational pattern that can be reused."""
    name: str
    expr: Any  # Expression
    signature: Tuple[float, ...]
    params: List[str] = field(default_factory=list)  # Parameter names for generalized tools
    metadata: Dict[str, Any] = field(default_factory=dict)  # growth_type, source, etc.

    def eval_with_args(self, input_val: float, arg_vals: List[float]) -> float:
        """Evaluate the tool with given input and argument values.

        For generalized tools, arg_vals provide parameter values.
        For simple tools, arg_vals is ignored.
        """
        if self.params:
            # Generalized tool - substitute parameters
            env = {'n': input_val}
            for param, val in zip(self.params, arg_vals):
                env[param] = val
            return self._eval_with_substitution(self.expr, env)
        else:
            # Simple tool - just evaluate
            return self.expr.eval({'n': input_val})

    def _eval_with_substitution(self, expr: Any, env: Dict[str, Any]) -> float:
        """Evaluate expression with parameter substitution."""
        if isinstance(expr, Const):
            return expr.val
        elif isinstance(expr, Var):
            return env.get(expr.name, 0)
        elif isinstance(expr, BinOp):
            l = self._eval_with_substitution(expr.left, env)
            r = self._eval_with_substitution(expr.right, env)
            if expr.op == '+':
                return l + r
            if expr.op == '-':
                return l - r
            if expr.op == '*':
                return l * r
            if expr.op == '/':
                return l / r if abs(r) > 0.001 else 0
            if expr.op == '^':
                return l ** min(r, 10)
        elif isinstance(expr, (Sum, Product)):
            # For loops, need full substitution
            return expr.eval(env)
        return 0

    def complexity(self) -> int:
        """Return complexity of the tool's expression."""
        return self.expr.complexity()


class ToolLibrary:
    """Library for storing and managing discovered tools."""

    def __init__(self):
        self._tools: List[Tool] = []
        self._by_name: Dict[str, Tool] = {}

    def add(self, tool: Tool) -> bool:
        """Add a tool to the library, preferring simpler equivalents.

        If an equivalent tool (same behavioral signature) already exists:
        - Keep the simpler one
        - Replace if new tool is simpler

        Args:
            tool: Tool to add

        Returns:
            True if added (or replaced existing), False if duplicate name or not simpler
        """
        if tool.name in self._by_name:
            return False

        # Check for functionally equivalent existing tool
        existing = self.find_by_signature(tool.signature)

        if existing:
            # Found equivalent - keep simpler one
            if tool.complexity() < existing.complexity():
                # New tool is simpler - replace existing
                self._tools.remove(existing)
                del self._by_name[existing.name]
                self._tools.append(tool)
                self._by_name[tool.name] = tool
                return True  # Replaced with simpler
            else:
                # Existing is simpler or equal - keep it
                return False

        # No equivalent exists - add new tool
        self._tools.append(tool)
        self._by_name[tool.name] = tool
        return True

    def get(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._by_name.get(name)

    def find_by_signature(
        self,
        sig: Tuple[float, ...],
        tolerance: float = 0.01,
    ) -> Tool | None:
        """Find a tool with matching behavioral signature."""
        for tool in self._tools:
            if len(tool.signature) == len(sig):
                if all(abs(v1 - v2) < tolerance for v1, v2 in zip(tool.signature, sig)):
                    return tool
        return None

    def is_novel(self, expr: Any, threshold: float = 0.3) -> bool:
        """Check if an expression is novel (different from existing tools).

        Args:
            expr: Expression to check
            threshold: Minimum novelty score required (0-1)

        Returns:
            True if expression is sufficiently different from all existing tools
        """
        if not self._tools:
            return True

        sig = behavioral_signature(expr)

        for tool in self._tools:
            similarity = signature_similarity(sig, tool.signature)
            if similarity > (1 - threshold):
                return False

        return True

    def is_trivial(self, expr: Any) -> bool:
        """Check if an expression is trivial (too simple to save as a tool).

        Trivial expressions are rejected to encourage discovering general patterns.
        For example, we don't want to save n*2, n*3, n*4 as separate tools -
        instead we want to recognize these as instances of the general pattern n*k.

        BUT: Simple correct solutions like n*n or n+n ARE valid tools if they
        don't generalize to a pattern with a constant parameter.

        Returns:
            True if expression is too simple to save (constants, variables only)
        """
        # Constants and variables are trivial
        if isinstance(expr, (Const, Var)):
            return True

        # Simple binops with a constant (like n*2, n+5) should be generalized
        # But binops with two variables (like n*n, n+n) are valid patterns
        if isinstance(expr, BinOp):
            left_is_const = isinstance(expr.left, Const)
            right_is_const = isinstance(expr.right, Const)
            # Only trivial if it has a constant that could be generalized
            if (left_is_const or right_is_const) and not (left_is_const and right_is_const):
                # n OP const or const OP n - should generalize
                return True

        return False

    def is_covered_by_general_tool(self, expr: Any) -> Tool | None:
        """Check if expression is an instance of an existing generalized tool.

        For example, if we have a tool for n*k, then n*3 is covered.

        Returns:
            The general tool that covers this expression, or None
        """
        for tool in self._tools:
            if tool.params:  # Only check generalized tools
                match = _match_pattern(expr, tool.expr)
                if match is not None:
                    return tool
        return None

    def try_generalize(self, expr: Any) -> tuple[Any, List[str], Dict[str, float]] | None:
        """Try to generalize an expression by extracting parameters.

        For example: n*2 → (n*k, ['k'], {'k': 2})

        Returns:
            (generalized_expr, param_names, param_values) or None if not generalizable
        """
        result = _extract_pattern(expr)
        if result:
            generalized_expr, param_values = result
            return generalized_expr, list(param_values.keys()), param_values
        return None

    def should_save(self, expr: Any, fitness: float) -> bool:
        """Check if an expression should be saved as a tool.

        Args:
            expr: Expression to check
            fitness: Fitness score achieved

        Returns:
            True if expression should be saved
        """
        # Must solve problem well
        if fitness < 0.95:
            return False

        # Must not be trivial
        if self.is_trivial(expr):
            return False

        # Check if covered by existing general tool (e.g., n*3 covered by n*k)
        if self.is_covered_by_general_tool(expr):
            return False

        # Must be novel
        if not self.is_novel(expr):
            return False

        return True

    def add_with_generalization(self, name: str, expr: Any, fitness: float) -> tuple[bool, str]:
        """Try to add a tool, generalizing if possible.

        Instead of saving n*2, tries to save n*k as a general pattern.

        Returns:
            (was_added, message) - whether added and explanation
        """
        # Check if already covered by general tool
        covering_tool = self.is_covered_by_general_tool(expr)
        if covering_tool:
            return False, f"Covered by general tool '{covering_tool.name}'"

        # Try to generalize
        gen_result = self.try_generalize(expr)
        if gen_result:
            gen_expr, params, _ = gen_result
            # Check if we already have this general pattern
            for tool in self._tools:
                if tool.params == params and repr(tool.expr) == repr(gen_expr):
                    return False, f"General pattern already exists as '{tool.name}'"

            # Create generalized tool
            sig = behavioral_signature(expr)  # Use original signature
            tool = Tool(
                name=name,
                expr=gen_expr,
                signature=sig,
                params=params,
                metadata={'generalized_from': repr(expr)}
            )
            added = self.add(tool)
            if added:
                return True, f"Generalized to {gen_expr} with params {params}"
            return False, "General tool not added (equivalent exists)"

        # Not generalizable - add as-is if novel
        if not self.should_save(expr, fitness):
            return False, "Expression not novel or trivial"

        sig = behavioral_signature(expr)
        tool = Tool(name=name, expr=expr, signature=sig)
        added = self.add(tool)
        return added, "Added as specific tool" if added else "Equivalent exists"

    def list_tools(self) -> List[Tool]:
        """Return list of all tools."""
        return self._tools.copy()

    def __len__(self) -> int:
        return len(self._tools)

    def __iter__(self):
        return iter(self._tools)

    def try_simplify(self, expr: Any) -> tuple[Any, bool]:
        """Try to simplify an expression using known equivalent tools.

        Args:
            expr: Expression to simplify

        Returns:
            (simplified_expr, was_simplified) - the simpler expression and whether simplification occurred
        """
        sig = behavioral_signature(expr)
        existing = self.find_by_signature(sig)

        if existing and existing.complexity() < expr.complexity():
            return existing.expr, True

        return expr, False

    def print_summary(self):
        """Print a summary of all tools in the library."""
        print(f"\n{'=' * 70}")
        print(f"TOOL LIBRARY: {len(self._tools)} tools")
        print(f"{'=' * 70}")

        for i, tool in enumerate(self._tools, 1):
            print(f"\n{i}. {tool.name}")
            if tool.params:
                print(f"   Parameters: {tool.params}")
            print(f"   Expression: {tool.expr}")
            print(f"   Complexity: {tool.complexity()}")
            if 'growth_type' in tool.metadata:
                print(f"   Growth: {tool.metadata['growth_type']}")
