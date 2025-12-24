"""Proof utilities for propositional logic expressions.

This module provides a lightweight proof checker for basic propositional
logic. It is intended to support writing and inspecting proofs generated
by the logic GP system.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List, Sequence

from genetic_gp.core.logic import And, Implies, Not, Or, expressions_equivalent


@dataclass(frozen=True)
class ProofStep:
    """One step in a proof."""

    conclusion: Any
    rule: str
    premises: tuple[int, ...] = ()

    def __repr__(self) -> str:
        premises = ", ".join(str(p) for p in self.premises)
        return f"{self.rule}({premises}) ⊢ {self.conclusion}"


@dataclass(frozen=True)
class ProofIssue:
    """Validation issue for a proof step."""

    step_index: int
    rule: str
    message: str


class Proof:
    """A structured proof over logic expressions."""

    def __init__(self, steps: Iterable[ProofStep]) -> None:
        self.steps: List[ProofStep] = list(steps)

    def _step_expr(self, index: int) -> Any:
        return self.steps[index].conclusion

    def verify(self) -> tuple[bool, List[ProofIssue]]:
        """Verify proof steps against inference rules."""
        issues: List[ProofIssue] = []

        for idx, step in enumerate(self.steps):
            if any(premise >= idx for premise in step.premises):
                issues.append(
                    ProofIssue(idx, step.rule, "Premises must reference earlier steps.")
                )
                continue

            rule = step.rule.lower()
            if rule == "assumption":
                continue

            validator = _RULES.get(rule)
            if validator is None:
                issues.append(ProofIssue(idx, step.rule, "Unknown proof rule."))
                continue

            error = validator(step, self)
            if error:
                issues.append(ProofIssue(idx, step.rule, error))

        return len(issues) == 0, issues

    def format(self) -> str:
        """Return a human-readable rendering of the proof."""
        lines = []
        for idx, step in enumerate(self.steps):
            lines.append(f"{idx:>2}: {step}")
        return "\n".join(lines)


def _expr_eq(expr1: Any, expr2: Any) -> bool:
    """Check semantic equivalence between expressions."""
    return expressions_equivalent(expr1, expr2)


def _validate_and_intro(step: ProofStep, proof: Proof) -> str | None:
    if len(step.premises) != 2:
        return "and_intro requires two premises."
    if not isinstance(step.conclusion, And):
        return "and_intro conclusion must be a conjunction."

    left = proof._step_expr(step.premises[0])
    right = proof._step_expr(step.premises[1])

    if _expr_eq(step.conclusion.left, left) and _expr_eq(step.conclusion.right, right):
        return None
    if _expr_eq(step.conclusion.left, right) and _expr_eq(step.conclusion.right, left):
        return None

    return "and_intro premises must match conjunction components."


def _validate_and_elim_left(step: ProofStep, proof: Proof) -> str | None:
    if len(step.premises) != 1:
        return "and_elim_left requires one premise."
    premise = proof._step_expr(step.premises[0])
    if not isinstance(premise, And):
        return "and_elim_left premise must be a conjunction."
    if _expr_eq(step.conclusion, premise.left):
        return None
    return "and_elim_left conclusion must match left conjunct."


def _validate_and_elim_right(step: ProofStep, proof: Proof) -> str | None:
    if len(step.premises) != 1:
        return "and_elim_right requires one premise."
    premise = proof._step_expr(step.premises[0])
    if not isinstance(premise, And):
        return "and_elim_right premise must be a conjunction."
    if _expr_eq(step.conclusion, premise.right):
        return None
    return "and_elim_right conclusion must match right conjunct."


def _validate_or_intro(step: ProofStep, proof: Proof) -> str | None:
    if len(step.premises) != 1:
        return "or_intro requires one premise."
    if not isinstance(step.conclusion, Or):
        return "or_intro conclusion must be a disjunction."
    premise = proof._step_expr(step.premises[0])
    if _expr_eq(step.conclusion.left, premise) or _expr_eq(
        step.conclusion.right, premise
    ):
        return None
    return "or_intro conclusion must include the premise."


def _validate_modus_ponens(step: ProofStep, proof: Proof) -> str | None:
    if len(step.premises) != 2:
        return "modus_ponens requires two premises."
    first = proof._step_expr(step.premises[0])
    second = proof._step_expr(step.premises[1])

    if isinstance(first, Implies):
        implication = first
        antecedent = second
    elif isinstance(second, Implies):
        implication = second
        antecedent = first
    else:
        return "modus_ponens requires an implication premise."

    if not _expr_eq(implication.left, antecedent):
        return "modus_ponens antecedent does not match implication."
    if not _expr_eq(step.conclusion, implication.right):
        return "modus_ponens conclusion must match implication consequent."

    return None


def _validate_double_negation_elim(step: ProofStep, proof: Proof) -> str | None:
    if len(step.premises) != 1:
        return "double_negation_elim requires one premise."
    premise = proof._step_expr(step.premises[0])
    if not isinstance(premise, Not) or not isinstance(premise.expr, Not):
        return "double_negation_elim premise must be ¬¬A."
    if _expr_eq(step.conclusion, premise.expr.expr):
        return None
    return "double_negation_elim conclusion must match inner expression."


def _validate_double_negation_intro(step: ProofStep, proof: Proof) -> str | None:
    if len(step.premises) != 1:
        return "double_negation_intro requires one premise."
    premise = proof._step_expr(step.premises[0])
    if not isinstance(step.conclusion, Not) or not isinstance(
        step.conclusion.expr, Not
    ):
        return "double_negation_intro conclusion must be ¬¬A."
    if _expr_eq(step.conclusion.expr.expr, premise):
        return None
    return "double_negation_intro inner expression must match premise."


def _validate_equivalence(step: ProofStep, proof: Proof) -> str | None:
    if len(step.premises) != 1:
        return "equivalence requires one premise."
    premise = proof._step_expr(step.premises[0])
    if _expr_eq(premise, step.conclusion):
        return None
    return "equivalence requires semantically equivalent expressions."


_RULES = {
    "and_intro": _validate_and_intro,
    "and_elim_left": _validate_and_elim_left,
    "and_elim_right": _validate_and_elim_right,
    "or_intro": _validate_or_intro,
    "modus_ponens": _validate_modus_ponens,
    "double_negation_elim": _validate_double_negation_elim,
    "double_negation_intro": _validate_double_negation_intro,
    "equivalence": _validate_equivalence,
}
