"""Logic expression types for propositional logic genetic programming.

Primitives: And (∧), Or (∨), Not (¬), Implies (→), Iff (↔), True, False
Behavioral signatures: Truth tables
Discovery targets: Logical equivalences, simplifications, tautologies

Example discoveries:
- De Morgan's laws: ¬(P ∧ Q) ≡ ¬P ∨ ¬Q
- Double negation: ¬¬P ≡ P
- Implication: P → Q ≡ ¬P ∨ Q
"""

from __future__ import annotations
from dataclasses import dataclass
from itertools import product
from typing import Any, Dict, Protocol, Set, Tuple, runtime_checkable


@runtime_checkable
class LogicExpression(Protocol):
    """Protocol that all logic expression types implement."""

    def eval(self, env: Dict[str, bool]) -> bool:
        """Evaluate expression in the given environment."""
        ...

    def complexity(self) -> int:
        """Return complexity score for this expression."""
        ...


@dataclass
class LConst:
    """Boolean constant (True or False)."""
    val: bool

    def eval(self, env: Dict[str, bool]) -> bool:
        return self.val

    def complexity(self) -> int:
        return 1

    def __repr__(self) -> str:
        return "T" if self.val else "F"


@dataclass
class LVar:
    """Boolean variable."""
    name: str

    def eval(self, env: Dict[str, bool]) -> bool:
        return env.get(self.name, False)

    def complexity(self) -> int:
        return 1

    def __repr__(self) -> str:
        return self.name


@dataclass
class Not:
    """Logical negation: ¬P"""
    expr: Any  # LogicExpression

    def eval(self, env: Dict[str, bool]) -> bool:
        return not self.expr.eval(env)

    def complexity(self) -> int:
        return 1 + self.expr.complexity()

    def __repr__(self) -> str:
        return f"¬{self.expr}"


@dataclass
class And:
    """Logical conjunction: P ∧ Q"""
    left: Any  # LogicExpression
    right: Any  # LogicExpression

    def eval(self, env: Dict[str, bool]) -> bool:
        return self.left.eval(env) and self.right.eval(env)

    def complexity(self) -> int:
        return 1 + self.left.complexity() + self.right.complexity()

    def __repr__(self) -> str:
        return f"({self.left} ∧ {self.right})"


@dataclass
class Or:
    """Logical disjunction: P ∨ Q"""
    left: Any  # LogicExpression
    right: Any  # LogicExpression

    def eval(self, env: Dict[str, bool]) -> bool:
        return self.left.eval(env) or self.right.eval(env)

    def complexity(self) -> int:
        return 1 + self.left.complexity() + self.right.complexity()

    def __repr__(self) -> str:
        return f"({self.left} ∨ {self.right})"


@dataclass
class Implies:
    """Logical implication: P → Q

    Equivalent to: ¬P ∨ Q
    """
    left: Any  # LogicExpression
    right: Any  # LogicExpression

    def eval(self, env: Dict[str, bool]) -> bool:
        # P → Q ≡ ¬P ∨ Q
        return (not self.left.eval(env)) or self.right.eval(env)

    def complexity(self) -> int:
        return 1 + self.left.complexity() + self.right.complexity()

    def __repr__(self) -> str:
        return f"({self.left} → {self.right})"


@dataclass
class Iff:
    """Logical biconditional: P ↔ Q

    Equivalent to: (P → Q) ∧ (Q → P)
    """
    left: Any  # LogicExpression
    right: Any  # LogicExpression

    def eval(self, env: Dict[str, bool]) -> bool:
        # P ↔ Q ≡ (P == Q)
        return self.left.eval(env) == self.right.eval(env)

    def complexity(self) -> int:
        return 1 + self.left.complexity() + self.right.complexity()

    def __repr__(self) -> str:
        return f"({self.left} ↔ {self.right})"


# ============================================
# VARIABLE EXTRACTION
# ============================================

def get_variables(expr: Any) -> Set[str]:
    """Extract all variable names from a logic expression.

    Args:
        expr: Logic expression to analyze

    Returns:
        Set of variable names used in the expression
    """
    if isinstance(expr, LVar):
        return {expr.name}
    elif isinstance(expr, LConst):
        return set()
    elif isinstance(expr, Not):
        return get_variables(expr.expr)
    elif isinstance(expr, (And, Or, Implies, Iff)):
        return get_variables(expr.left) | get_variables(expr.right)
    else:
        return set()


# ============================================
# TRUTH TABLES (BEHAVIORAL SIGNATURES)
# ============================================

def truth_table(
    expr: Any,
    variables: list[str] | None = None,
) -> Tuple[bool, ...]:
    """Generate truth table for a logic expression.

    The truth table IS the behavioral signature for logic expressions.
    Two expressions are logically equivalent iff they have the same truth table.

    Args:
        expr: Logic expression to evaluate
        variables: Optional list of variables (auto-detected if not provided)

    Returns:
        Tuple of boolean results, one per input combination
    """
    if variables is None:
        variables = sorted(get_variables(expr))

    if not variables:
        # No variables - just evaluate the constant
        return (expr.eval({}),)

    results = []
    # Generate all combinations of variable assignments
    for assignment in product([False, True], repeat=len(variables)):
        env = dict(zip(variables, assignment))
        result = expr.eval(env)
        results.append(result)

    return tuple(results)


def tables_equivalent(
    table1: Tuple[bool, ...],
    table2: Tuple[bool, ...],
) -> bool:
    """Check if two truth tables are identical.

    Args:
        table1: First truth table
        table2: Second truth table

    Returns:
        True if tables are identical
    """
    return table1 == table2


def expressions_equivalent(expr1: Any, expr2: Any) -> bool:
    """Check if two logic expressions are logically equivalent.

    Two expressions are equivalent iff they have the same truth table
    over their combined variable set.

    Args:
        expr1: First expression
        expr2: Second expression

    Returns:
        True if expressions are logically equivalent
    """
    # Get combined variable set
    vars1 = get_variables(expr1)
    vars2 = get_variables(expr2)
    all_vars = sorted(vars1 | vars2)

    # Generate truth tables over same variables
    table1 = truth_table(expr1, all_vars)
    table2 = truth_table(expr2, all_vars)

    return tables_equivalent(table1, table2)


# ============================================
# LOGICAL PROPERTIES
# ============================================

def is_tautology(expr: Any) -> bool:
    """Check if expression is always true (tautology).

    Args:
        expr: Logic expression to check

    Returns:
        True if expression is true for all variable assignments
    """
    table = truth_table(expr)
    return all(table)


def is_contradiction(expr: Any) -> bool:
    """Check if expression is always false (contradiction).

    Args:
        expr: Logic expression to check

    Returns:
        True if expression is false for all variable assignments
    """
    table = truth_table(expr)
    return not any(table)


def is_contingent(expr: Any) -> bool:
    """Check if expression is contingent (sometimes true, sometimes false).

    Args:
        expr: Logic expression to check

    Returns:
        True if expression is neither a tautology nor a contradiction
    """
    return not is_tautology(expr) and not is_contradiction(expr)


def is_satisfiable(expr: Any) -> bool:
    """Check if expression can be satisfied (made true).

    Args:
        expr: Logic expression to check

    Returns:
        True if there exists an assignment making the expression true
    """
    table = truth_table(expr)
    return any(table)


# ============================================
# CLASSIFICATION
# ============================================

def classify_expression(expr: Any) -> str:
    """Classify a logic expression by its logical properties.

    Args:
        expr: Logic expression to classify

    Returns:
        One of: 'tautology', 'contradiction', 'contingent'
    """
    if is_tautology(expr):
        return 'tautology'
    elif is_contradiction(expr):
        return 'contradiction'
    else:
        return 'contingent'
