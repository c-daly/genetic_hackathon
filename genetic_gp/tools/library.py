"""Primitive library for storing and reusing discovered patterns.

Derived primitives are patterns discovered through evolution that can be
reused in future problems. They are built from base primitives (+, -, *, /, ^, Σ, ∏).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple
import os
import yaml

from genetic_gp.core.expressions import Const, Var, BinOp, Sum, Product
from genetic_gp.core.signatures import behavioral_signature, signature_similarity
from genetic_gp.core.simplify import simplify, is_degenerate


# LLM configuration for name suggestion
_llm_provider: str = "openai"  # "openai" or "anthropic"
_llm_model: str | None = None  # None = use default for provider


def configure_llm(provider: str = "openai", model: str | None = None) -> None:
    """Configure which LLM to use for name suggestions.

    Args:
        provider: "openai" or "anthropic"
        model: Model name (or None for default)
    """
    global _llm_provider, _llm_model
    _llm_provider = provider
    _llm_model = model


def suggest_name_via_llm(expr: Any, description: str = "") -> str | None:
    """Use an LLM to suggest a descriptive name for a mathematical pattern.

    Uses OpenAI by default (configure with configure_llm()).

    Args:
        expr: The expression to name
        description: Optional description of what the expression computes

    Returns:
        Suggested name, or None if LLM is not available
    """
    prompt = f"""Given this mathematical expression:
{expr}

{f"It computes: {description}" if description else ""}

Suggest a short, descriptive function name (1-2 words, snake_case) that captures what this expression computes.
Examples: sum_to_n, factorial, double, square, triangular_number, power

Respond with ONLY the function name, nothing else."""

    try:
        if _llm_provider == "openai":
            name = _suggest_via_openai(prompt)
        elif _llm_provider == "anthropic":
            name = _suggest_via_anthropic(prompt)
        else:
            return None

        if name:
            # Sanitize: only allow alphanumeric and underscores
            name = name.strip().lower().replace(' ', '_')
            name = ''.join(c for c in name if c.isalnum() or c == '_')
            return name if name else None
        return None

    except Exception:
        return None


def _suggest_via_openai(prompt: str) -> str | None:
    """Get name suggestion from OpenAI."""
    try:
        from openai import OpenAI
    except ImportError:
        return None

    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return None

    try:
        client = OpenAI(api_key=api_key)
        model = _llm_model or "gpt-4o-mini"

        response = client.chat.completions.create(
            model=model,
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content
    except Exception:
        return None


def _suggest_via_anthropic(prompt: str) -> str | None:
    """Get name suggestion from Anthropic."""
    try:
        import anthropic
    except ImportError:
        return None

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return None

    try:
        client = anthropic.Anthropic(api_key=api_key)
        model = _llm_model or "claude-haiku-3-5-20241022"

        response = client.messages.create(
            model=model,
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text
    except Exception:
        return None


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


def _expr_to_dict(expr: Any) -> dict:
    """Serialize an expression to a dictionary for YAML storage."""
    if isinstance(expr, Const):
        return {'type': 'Const', 'val': expr.val}
    elif isinstance(expr, Var):
        return {'type': 'Var', 'name': expr.name}
    elif isinstance(expr, BinOp):
        return {
            'type': 'BinOp',
            'op': expr.op,
            'left': _expr_to_dict(expr.left),
            'right': _expr_to_dict(expr.right),
        }
    elif isinstance(expr, Sum):
        return {
            'type': 'Sum',
            'var': expr.var,
            'start': _expr_to_dict(expr.start),
            'end': _expr_to_dict(expr.end),
            'body': _expr_to_dict(expr.body),
        }
    elif isinstance(expr, Product):
        return {
            'type': 'Product',
            'var': expr.var,
            'start': _expr_to_dict(expr.start),
            'end': _expr_to_dict(expr.end),
            'body': _expr_to_dict(expr.body),
        }
    else:
        # Handle PrimitiveCall - import here to avoid circular import
        from genetic_gp.core.expressions import PrimitiveCall
        if isinstance(expr, PrimitiveCall):
            return {
                'type': 'PrimitiveCall',
                'primitive_name': expr.primitive_name,
                'arg': _expr_to_dict(expr.arg),
            }
        raise ValueError(f"Unknown expression type: {type(expr)}")


def _dict_to_expr(d: dict) -> Any:
    """Deserialize an expression from a dictionary."""
    expr_type = d['type']
    if expr_type == 'Const':
        return Const(d['val'])
    elif expr_type == 'Var':
        return Var(d['name'])
    elif expr_type == 'BinOp':
        return BinOp(
            d['op'],
            _dict_to_expr(d['left']),
            _dict_to_expr(d['right']),
        )
    elif expr_type == 'Sum':
        return Sum(
            d['var'],
            _dict_to_expr(d['start']),
            _dict_to_expr(d['end']),
            _dict_to_expr(d['body']),
        )
    elif expr_type == 'Product':
        return Product(
            d['var'],
            _dict_to_expr(d['start']),
            _dict_to_expr(d['end']),
            _dict_to_expr(d['body']),
        )
    elif expr_type == 'PrimitiveCall':
        from genetic_gp.core.expressions import PrimitiveCall
        return PrimitiveCall(
            d['primitive_name'],
            _dict_to_expr(d['arg']),
        )
    else:
        raise ValueError(f"Unknown expression type: {expr_type}")


@dataclass
class DerivedPrimitive:
    """A discovered computational pattern that can be reused.

    Derived primitives emerge from evolution and become available
    for future problems, building on the base primitives.
    """
    name: str
    expr: Any  # Expression
    signature: Tuple[float, ...]
    params: List[str] = field(default_factory=list)  # Parameter names for generalized primitives
    metadata: Dict[str, Any] = field(default_factory=dict)  # growth_type, source, etc.

    def eval_with_args(self, input_val: float, arg_vals: List[float]) -> float:
        """Evaluate the primitive with given input and argument values.

        For generalized primitives, arg_vals provide parameter values.
        For simple primitives, arg_vals is ignored.
        """
        if self.params:
            # Generalized primitive - substitute parameters
            env = {'n': input_val}
            for param, val in zip(self.params, arg_vals):
                env[param] = val
            return self._eval_with_substitution(self.expr, env)
        else:
            # Simple primitive - just evaluate
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
        """Return complexity of the primitive's expression."""
        return self.expr.complexity()

    def to_dict(self) -> dict:
        """Serialize to dictionary for persistence."""
        return {
            'name': self.name,
            'expr': _expr_to_dict(self.expr),
            'signature': list(self.signature),
            'params': self.params,
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'DerivedPrimitive':
        """Deserialize from dictionary."""
        return cls(
            name=d['name'],
            expr=_dict_to_expr(d['expr']),
            signature=tuple(d['signature']),
            params=d.get('params', []),
            metadata=d.get('metadata', {}),
        )


# Backwards compatibility alias
Tool = DerivedPrimitive


class PrimitiveLibrary:
    """Library for storing and managing derived primitives.

    Supports persistence to YAML for accumulating knowledge across sessions.
    """

    def __init__(self):
        self._primitives: List[DerivedPrimitive] = []
        self._by_name: Dict[str, DerivedPrimitive] = {}

    def add(self, primitive: DerivedPrimitive) -> bool:
        """Add a primitive to the library, preferring simpler equivalents.

        If an equivalent primitive (same behavioral signature) already exists:
        - Keep the simpler one
        - Replace if new primitive is simpler

        Args:
            primitive: DerivedPrimitive to add

        Returns:
            True if added (or replaced existing), False if duplicate name or not simpler
        """
        if primitive.name in self._by_name:
            return False

        # Check for functionally equivalent existing primitive
        existing = self.find_by_signature(primitive.signature)

        if existing:
            # Found equivalent - keep simpler one
            if primitive.complexity() < existing.complexity():
                # New primitive is simpler - replace existing
                self._primitives.remove(existing)
                del self._by_name[existing.name]
                self._primitives.append(primitive)
                self._by_name[primitive.name] = primitive
                return True  # Replaced with simpler
            else:
                # Existing is simpler or equal - keep it
                return False

        # No equivalent exists - add new primitive
        self._primitives.append(primitive)
        self._by_name[primitive.name] = primitive
        return True

    def get(self, name: str) -> DerivedPrimitive | None:
        """Get a primitive by name."""
        return self._by_name.get(name)

    def find_by_signature(
        self,
        sig: Tuple[float, ...],
        tolerance: float = 0.01,
    ) -> DerivedPrimitive | None:
        """Find a primitive with matching behavioral signature."""
        for primitive in self._primitives:
            if len(primitive.signature) == len(sig):
                if all(abs(v1 - v2) < tolerance for v1, v2 in zip(primitive.signature, sig)):
                    return primitive
        return None

    def is_novel(self, expr: Any, threshold: float = 0.3) -> bool:
        """Check if an expression is novel (different from existing primitives).

        Args:
            expr: Expression to check
            threshold: Minimum novelty score required (0-1)

        Returns:
            True if expression is sufficiently different from all existing primitives
        """
        if not self._primitives:
            return True

        sig = behavioral_signature(expr)

        for primitive in self._primitives:
            similarity = signature_similarity(sig, primitive.signature)
            if similarity > (1 - threshold):
                return False

        return True

    def is_trivial(self, expr: Any) -> bool:
        """Check if an expression is trivial (too simple to save as a derived primitive).

        Trivial expressions are rejected to encourage discovering general patterns.
        For example, we don't want to save n*2, n*3, n*4 as separate primitives -
        instead we want to recognize these as instances of the general pattern n*k.

        Also rejects complex expressions that compute trivial functions (like
        Σ(j=n..n)[∏(k=2..3)[j]] which just computes n² in a roundabout way).

        Returns:
            True if expression is too simple to save
        """
        # Constants and variables are trivial
        if isinstance(expr, (Const, Var)):
            return True

        if isinstance(expr, BinOp):
            left_is_const = isinstance(expr.left, Const)
            right_is_const = isinstance(expr.right, Const)
            left_is_var = isinstance(expr.left, Var)
            right_is_var = isinstance(expr.right, Var)

            # n OP const or const OP n - should generalize to n OP k
            if (left_is_const or right_is_const) and not (left_is_const and right_is_const):
                return True

            # var OP var with same variable - all are trivial
            # These are just base primitives applied to the same argument:
            # n + n = add(n, n), n * n = multiply(n, n), etc.
            # Not novel patterns worth saving.
            if left_is_var and right_is_var and expr.left.name == expr.right.name:
                return True

        # Check behavioral signature against trivial patterns
        # This catches complex expressions that compute simple functions
        if self._has_trivial_behavior(expr):
            return True

        return False

    def _has_trivial_behavior(self, expr: Any) -> bool:
        """Check if expression computes a trivial function regardless of structure.

        Checks against known trivial patterns: n, n², n³, 2n, 3n, etc.
        This catches degenerate expressions like Σ(j=n..n)[∏(k=2..3)[j]] that compute n².
        """
        sig = behavioral_signature(expr)

        # Generate signatures for trivial patterns and compare
        trivial_patterns = [
            Var('n'),                                    # n
            BinOp('+', Var('n'), Var('n')),             # 2n
            BinOp('*', Var('n'), Var('n')),             # n²
            BinOp('*', Var('n'), BinOp('*', Var('n'), Var('n'))),  # n³
            BinOp('^', Var('n'), Const(2)),             # n^2
            BinOp('^', Var('n'), Const(3)),             # n^3
        ]
        # Also check n*k and n+k for small k
        for k in range(2, 11):
            trivial_patterns.append(BinOp('*', Var('n'), Const(k)))
            trivial_patterns.append(BinOp('+', Var('n'), Const(k)))

        for pattern in trivial_patterns:
            pattern_sig = behavioral_signature(pattern)
            if len(sig) == len(pattern_sig):
                if all(abs(v1 - v2) < 0.01 for v1, v2 in zip(sig, pattern_sig)):
                    return True

        return False

    def is_covered_by_general_primitive(self, expr: Any) -> DerivedPrimitive | None:
        """Check if expression is an instance of an existing generalized primitive.

        For example, if we have a primitive for n*k, then n*3 is covered.

        Returns:
            The general primitive that covers this expression, or None
        """
        for primitive in self._primitives:
            if primitive.params:  # Only check generalized primitives
                match = _match_pattern(expr, primitive.expr)
                if match is not None:
                    return primitive
        return None

    # Backwards compatibility alias
    def is_covered_by_general_tool(self, expr: Any) -> DerivedPrimitive | None:
        """Deprecated: Use is_covered_by_general_primitive() instead."""
        return self.is_covered_by_general_primitive(expr)

    def _suggest_pattern_name(self, gen_expr: Any, params: List[str]) -> str:
        """Suggest a name for a generalized pattern.

        Uses LLM if available, otherwise falls back to operator-based naming.

        Examples:
            (n*k) with params=['k'] -> 'scale'
            (n^k) with params=['k'] -> 'power'
            (n+k) with params=['k'] -> 'add'
        """
        # Try LLM first
        llm_name = suggest_name_via_llm(gen_expr, f"Generalized pattern with params {params}")
        if llm_name:
            return llm_name

        # Fallback to operator-based naming
        if isinstance(gen_expr, BinOp):
            op_names = {
                '*': 'scale',
                '^': 'power',
                '+': 'add',
                '-': 'subtract',
                '/': 'divide',
            }
            return op_names.get(gen_expr.op, f"pattern_{gen_expr.op}")

        return "pattern"

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
        """Check if an expression should be saved as a derived primitive.

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

        # Check if covered by existing general primitive (e.g., n*3 covered by n*k)
        if self.is_covered_by_general_primitive(expr):
            return False

        # Must be novel
        if not self.is_novel(expr):
            return False

        return True

    def add_with_generalization(self, name: str | None, expr: Any, fitness: float) -> tuple[bool, str]:
        """Try to add a primitive, generalizing if possible.

        Instead of saving n*2, tries to save n*k as a general pattern.
        Degenerate expressions (single-term loops, unused loop vars) are
        simplified before saving.

        Args:
            name: Name for the primitive. If None and expression is generalized,
                  a name is suggested based on the pattern (e.g., 'scale', 'power').
            expr: The expression to potentially save
            fitness: Fitness score (must be >= 0.99 to save)

        Returns:
            (was_added, message) - whether added and explanation
        """
        # Simplify first (removes no-ops like single-term loops)
        simplified = simplify(expr)
        if repr(simplified) != repr(expr):
            # Expression was simplified - use the simpler form
            expr = simplified

        # Check if already covered by general primitive
        covering = self.is_covered_by_general_primitive(expr)
        if covering:
            return False, f"Covered by general primitive '{covering.name}'"

        # Try to generalize
        gen_result = self.try_generalize(expr)
        if gen_result:
            gen_expr, params, _ = gen_result
            # Check if we already have this general pattern
            for primitive in self._primitives:
                if primitive.params == params and repr(primitive.expr) == repr(gen_expr):
                    return False, f"General pattern already exists as '{primitive.name}'"

            # Use provided name or suggest one based on pattern
            primitive_name = name if name else self._suggest_pattern_name(gen_expr, params)

            # Create generalized primitive
            sig = behavioral_signature(expr)  # Use original signature
            primitive = DerivedPrimitive(
                name=primitive_name,
                expr=gen_expr,
                signature=sig,
                params=params,
                metadata={'generalized_from': repr(expr)}
            )
            added = self.add(primitive)
            if added:
                return True, f"Generalized to {gen_expr} as '{primitive_name}'"
            return False, "General primitive not added (equivalent exists)"

        # Not generalizable - add as-is if novel
        if not self.should_save(expr, fitness):
            return False, "Expression not novel or trivial"

        if not name:
            return False, "Name required for non-generalizable expressions"

        sig = behavioral_signature(expr)
        primitive = DerivedPrimitive(name=name, expr=expr, signature=sig)
        added = self.add(primitive)
        return added, "Added as derived primitive" if added else "Equivalent exists"

    def list_primitives(self) -> List[DerivedPrimitive]:
        """Return list of all derived primitives."""
        return self._primitives.copy()

    # Backwards compatibility
    def list_tools(self) -> List[DerivedPrimitive]:
        """Deprecated: Use list_primitives() instead."""
        return self.list_primitives()

    def __len__(self) -> int:
        return len(self._primitives)

    def __iter__(self):
        return iter(self._primitives)

    def try_simplify(self, expr: Any) -> tuple[Any, bool]:
        """Try to simplify an expression using known equivalent primitives.

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

    def save(self, path: str | Path) -> None:
        """Save the library to a YAML file.

        Args:
            path: Path to save to
        """
        path = Path(path)
        data = {
            'version': 1,
            'primitives': [p.to_dict() for p in self._primitives]
        }
        with open(path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    @classmethod
    def load(cls, path: str | Path) -> 'PrimitiveLibrary':
        """Load a library from a YAML file.

        Args:
            path: Path to load from

        Returns:
            Loaded PrimitiveLibrary
        """
        path = Path(path)
        with open(path) as f:
            data = yaml.safe_load(f)

        library = cls()
        for p_data in data.get('primitives', []):
            primitive = DerivedPrimitive.from_dict(p_data)
            library._primitives.append(primitive)
            library._by_name[primitive.name] = primitive

        return library

    def print_summary(self):
        """Print a summary of all derived primitives in the library."""
        print(f"\n{'=' * 70}")
        print(f"DERIVED PRIMITIVES: {len(self._primitives)}")
        print(f"{'=' * 70}")

        for i, primitive in enumerate(self._primitives, 1):
            print(f"\n{i}. {primitive.name}")
            if primitive.params:
                print(f"   Parameters: {primitive.params}")
            print(f"   Expression: {primitive.expr}")
            print(f"   Complexity: {primitive.complexity()}")
            if 'growth_type' in primitive.metadata:
                print(f"   Growth: {primitive.metadata['growth_type']}")


# Backwards compatibility alias
ToolLibrary = PrimitiveLibrary
