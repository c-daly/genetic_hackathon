"""Mathematical expression types for genetic programming."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Protocol, runtime_checkable


@runtime_checkable
class Expression(Protocol):
    """Protocol that all expression types implement."""

    def eval(self, env: Dict[str, Any]) -> float:
        """Evaluate expression in the given environment."""
        ...

    def complexity(self) -> int:
        """Return complexity score for this expression."""
        ...


@dataclass
class Const:
    """Constant value."""
    val: float

    def eval(self, env: Dict[str, Any]) -> float:
        return self.val

    def complexity(self) -> int:
        return 1

    def __repr__(self) -> str:
        if self.val == int(self.val):
            return str(int(self.val))
        return str(round(self.val, 2))


@dataclass
class Var:
    """Variable reference."""
    name: str

    def eval(self, env: Dict[str, Any]) -> float:
        return env.get(self.name, 0)

    def complexity(self) -> int:
        return 1

    def __repr__(self) -> str:
        return self.name


@dataclass
class BinOp:
    """Binary operation: +, -, *, /, ^"""
    op: str
    left: Any  # Expression
    right: Any  # Expression

    def eval(self, env: Dict[str, Any]) -> float:
        try:
            l = self.left.eval(env)
            r = self.right.eval(env)
            if self.op == '+':
                return l + r
            if self.op == '-':
                return l - r
            if self.op == '*':
                return l * r
            if self.op == '/':
                return l / r if abs(r) > 0.001 else 0
            if self.op == '^':
                result = l ** min(r, 10)  # Cap exponent to prevent overflow
                # Handle complex results (e.g., negative base with fractional exponent)
                if isinstance(result, complex):
                    return abs(result)
                return result
        except (OverflowError, ValueError, ZeroDivisionError, TypeError):
            return 0
        return 0

    def complexity(self) -> int:
        return 1 + self.left.complexity() + self.right.complexity()

    def __repr__(self) -> str:
        return f"({self.left}{self.op}{self.right})"


@dataclass
class Sum:
    """Summation: Σ(var=start..end)[body]"""
    var: str
    start: Any  # Expression
    end: Any  # Expression
    body: Any  # Expression

    def eval(self, env: Dict[str, Any]) -> float:
        try:
            start_val = self.start.eval(env)
            end_val = self.end.eval(env)
            # Handle complex or non-numeric values
            if isinstance(start_val, complex):
                start_val = abs(start_val)
            if isinstance(end_val, complex):
                end_val = abs(end_val)
            s = int(start_val)
            e = int(end_val)
            total = 0.0
            # Cap iterations to prevent runaway loops
            for i in range(s, min(e + 1, s + 100)):
                new_env = env.copy()
                new_env[self.var] = i
                body_val = self.body.eval(new_env)
                if isinstance(body_val, complex):
                    body_val = abs(body_val)
                total += body_val
            return total
        except (OverflowError, ValueError, RecursionError, TypeError):
            return 0

    def complexity(self) -> int:
        return 3 + self.start.complexity() + self.end.complexity() + self.body.complexity()

    def __repr__(self) -> str:
        return f"Σ({self.var}={self.start}..{self.end})[{self.body}]"


@dataclass
class Product:
    """Product: ∏(var=start..end)[body]"""
    var: str
    start: Any  # Expression
    end: Any  # Expression
    body: Any  # Expression

    def eval(self, env: Dict[str, Any]) -> float:
        try:
            start_val = self.start.eval(env)
            end_val = self.end.eval(env)
            # Handle complex or non-numeric values
            if isinstance(start_val, complex):
                start_val = abs(start_val)
            if isinstance(end_val, complex):
                end_val = abs(end_val)
            s = int(start_val)
            e = int(end_val)
            result = 1.0
            # Cap iterations to prevent runaway loops
            for i in range(s, min(e + 1, s + 100)):
                new_env = env.copy()
                new_env[self.var] = i
                body_val = self.body.eval(new_env)
                if isinstance(body_val, complex):
                    body_val = abs(body_val)
                result *= body_val
            return result
        except (OverflowError, ValueError, RecursionError, TypeError):
            return 1

    def complexity(self) -> int:
        return 3 + self.start.complexity() + self.end.complexity() + self.body.complexity()

    def __repr__(self) -> str:
        return f"∏({self.var}={self.start}..{self.end})[{self.body}]"


@dataclass
class PrimitiveCall:
    """Call to a previously discovered derived primitive."""
    primitive_name: str
    arg: Any  # Expression argument (typically just n)
    primitive_library: Any = None  # PrimitiveLibrary reference (optional for serialization)

    def eval(self, env: Dict[str, Any]) -> float:
        try:
            if self.primitive_library is None:
                return 0
            primitive = self.primitive_library.get(self.primitive_name)
            if primitive is None:
                return 0

            # Evaluate argument
            if hasattr(self.arg, 'eval'):
                arg_val = self.arg.eval(env)
            else:
                arg_val = self.arg

            # Evaluate the primitive
            return primitive.eval_with_args(arg_val, [])
        except Exception:
            return 0

    def complexity(self) -> int:
        # Primitive calls have base cost + argument complexity
        # But don't count primitive's internal complexity (encourages reuse)
        base = 2
        arg_complexity = self.arg.complexity() if hasattr(self.arg, 'complexity') else 1
        return base + arg_complexity

    def __repr__(self) -> str:
        return f"{self.primitive_name}()"


# Backwards compatibility alias
ToolCall = PrimitiveCall
