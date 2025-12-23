"""Tool library for storing and reusing discovered patterns."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from genetic_gp.core.expressions import Const, Var, BinOp, Sum, Product
from genetic_gp.core.signatures import behavioral_signature, signature_similarity


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
        """Add a tool to the library.

        Args:
            tool: Tool to add

        Returns:
            True if added, False if duplicate
        """
        if tool.name in self._by_name:
            return False

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
        """Check if an expression is trivial (too simple to save).

        Trivial expressions are single operations like n*2, n+n, n^2
        that don't represent meaningful patterns.
        """
        # Constants and variables are trivial
        if isinstance(expr, (Const, Var)):
            return True

        # Simple binary ops with both sides being terminals
        if isinstance(expr, BinOp):
            left_simple = isinstance(expr.left, (Const, Var))
            right_simple = isinstance(expr.right, (Const, Var))
            if left_simple and right_simple:
                return True

        return False

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

        # Must be novel
        if not self.is_novel(expr):
            return False

        return True

    def list_tools(self) -> List[Tool]:
        """Return list of all tools."""
        return self._tools.copy()

    def __len__(self) -> int:
        return len(self._tools)

    def __iter__(self):
        return iter(self._tools)

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
