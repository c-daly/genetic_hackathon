"""Transformation discovery and application.

Transformations are learned simplification rules. When GP discovers that
two expressions with different complexity have identical behavior, it
saves the simpler form as a transformation rule.

This is meta-computation: discovering rules for transforming computations.
"""

from __future__ import annotations
import hashlib
from dataclasses import dataclass, field
from typing import Any, List, Tuple

from genetic_gp.core.signatures import behavioral_signature, signatures_match


@dataclass
class Transformation:
    """A discovered simplification rule.

    Represents the equivalence: from_expr ≡ to_expr
    where to_expr is simpler (lower complexity).
    """
    id: str
    from_signature: Tuple[float, ...]
    to_expr: Any  # Expression
    to_signature: Tuple[float, ...]
    complexity_reduction: int
    from_complexity: int
    to_complexity: int
    metadata: dict = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"Transform({self.id}: Δ=-{self.complexity_reduction})"

    def description(self) -> str:
        """Human-readable description of the transformation."""
        return (
            f"Complexity {self.from_complexity} → {self.to_complexity} "
            f"(reduction: {self.complexity_reduction})"
        )


class TransformationLibrary:
    """Library for storing and applying discovered transformations."""

    def __init__(self):
        self._transformations: List[Transformation] = []
        self._by_signature: dict = {}  # signature -> Transformation

    def discover(
        self,
        expr1: Any,
        expr2: Any,
        min_reduction: int = 2,
    ) -> Transformation | None:
        """Check if two expressions are equivalent, create transformation if one simpler.

        Args:
            expr1: First expression
            expr2: Second expression
            min_reduction: Minimum complexity reduction required to save

        Returns:
            Transformation if expressions are equivalent with meaningful
            simplification, None otherwise.
        """
        sig1 = behavioral_signature(expr1)
        sig2 = behavioral_signature(expr2)

        if not signatures_match(sig1, sig2):
            return None

        c1 = expr1.complexity()
        c2 = expr2.complexity()

        # Only save if there's meaningful simplification
        if abs(c1 - c2) < min_reduction:
            return None

        # Create transformation from complex to simple
        if c1 > c2:
            from_sig, to_sig = sig1, sig2
            from_complexity, to_complexity = c1, c2
            to_expr = expr2
        else:
            from_sig, to_sig = sig2, sig1
            from_complexity, to_complexity = c2, c1
            to_expr = expr1

        complexity_reduction = from_complexity - to_complexity

        # Generate unique ID based on signatures
        sig_str = f"{from_sig}{to_sig}"
        trans_id = hashlib.md5(sig_str.encode()).hexdigest()[:8]

        return Transformation(
            id=trans_id,
            from_signature=from_sig,
            to_expr=to_expr,
            to_signature=to_sig,
            complexity_reduction=complexity_reduction,
            from_complexity=from_complexity,
            to_complexity=to_complexity,
        )

    def add(self, trans: Transformation) -> bool:
        """Add a transformation to the library.

        Args:
            trans: Transformation to add

        Returns:
            True if added, False if duplicate
        """
        # Check for duplicate by signature
        sig_key = trans.from_signature
        if sig_key in self._by_signature:
            existing = self._by_signature[sig_key]
            # Only replace if new one has better reduction
            if trans.complexity_reduction <= existing.complexity_reduction:
                return False
            # Remove old one
            self._transformations.remove(existing)

        self._transformations.append(trans)
        self._by_signature[sig_key] = trans
        return True

    def try_simplify(self, expr: Any) -> Any:
        """Try to apply transformations to simplify expression.

        Args:
            expr: Expression to simplify

        Returns:
            Simplified expression if transformation found, original otherwise
        """
        if not self._transformations:
            return expr

        sig = behavioral_signature(expr)
        current_complexity = expr.complexity()

        # Find matching transformation
        best_expr = expr
        best_complexity = current_complexity

        for trans in self._transformations:
            if signatures_match(sig, trans.from_signature):
                # This expression matches the transformation pattern
                if trans.to_complexity < best_complexity:
                    best_expr = trans.to_expr
                    best_complexity = trans.to_complexity

        return best_expr

    def find_by_signature(
        self,
        sig: Tuple[float, ...],
        tolerance: float = 0.01,
    ) -> Transformation | None:
        """Find a transformation that applies to the given signature.

        Args:
            sig: Signature to match
            tolerance: Matching tolerance

        Returns:
            Transformation if found, None otherwise
        """
        for trans in self._transformations:
            if signatures_match(sig, trans.from_signature, tolerance):
                return trans
        return None

    def list_transformations(self) -> List[Transformation]:
        """Return list of all transformations."""
        return self._transformations.copy()

    def __len__(self) -> int:
        return len(self._transformations)

    def __iter__(self):
        return iter(self._transformations)

    def print_summary(self):
        """Print a summary of all transformations."""
        if not self._transformations:
            print("\n  (No transformations discovered yet)")
            return

        print(f"\n{'=' * 70}")
        print(f"TRANSFORMATION LIBRARY: {len(self._transformations)} rules")
        print(f"{'=' * 70}")

        for i, trans in enumerate(self._transformations, 1):
            print(f"\n{i}. {trans.description()}")
            print(f"   Target: {trans.to_expr}")
            if trans.metadata:
                for key, val in trans.metadata.items():
                    print(f"   {key}: {val}")


def discover_transformations_from_solutions(
    solutions: List[Tuple[Any, float]],
    library: TransformationLibrary,
    min_fitness: float = 0.5,
    min_reduction: int = 2,
) -> int:
    """Discover transformations by comparing solutions with same behavior.

    Args:
        solutions: List of (expression, fitness) tuples
        library: TransformationLibrary to add discoveries to
        min_fitness: Minimum fitness to consider
        min_reduction: Minimum complexity reduction required

    Returns:
        Number of new transformations discovered
    """
    # Filter to decent solutions
    good_solutions = [(e, f) for e, f in solutions if f >= min_fitness]

    discovered = 0

    # Compare all pairs
    for i, (expr1, fit1) in enumerate(good_solutions):
        for expr2, fit2 in good_solutions[i + 1:]:
            trans = library.discover(expr1, expr2, min_reduction)
            if trans is not None:
                if library.add(trans):
                    discovered += 1

    return discovered
