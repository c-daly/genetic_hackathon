"""Behavioral signatures for expression comparison.

A function IS its input/output behavior. Two expressions with the same
behavioral signature compute the same function, regardless of syntax.
"""

from __future__ import annotations
from typing import Any, Iterable, Tuple


def behavioral_signature(
    expr: Any,
    test_inputs: Iterable[int] | None = None,
    var_name: str = 'n',
    cap_value: float = 1e10,
) -> Tuple[float, ...]:
    """Compute I/O signature for an expression.

    Args:
        expr: Expression to evaluate
        test_inputs: Input values to test (default: range(20))
        var_name: Variable name to bind inputs to
        cap_value: Cap extreme values to prevent overflow issues

    Returns:
        Tuple of output values, one per input
    """
    if test_inputs is None:
        test_inputs = range(20)

    signature = []
    for x in test_inputs:
        try:
            result = expr.eval({var_name: x})
            # Cap extreme values
            if abs(result) > cap_value:
                result = cap_value if result > 0 else -cap_value
            signature.append(round(result, 6))
        except Exception:
            signature.append(0)

    return tuple(signature)


def signatures_match(
    sig1: Tuple[float, ...],
    sig2: Tuple[float, ...],
    tolerance: float = 0.01,
) -> bool:
    """Check if two signatures represent the same function.

    Args:
        sig1: First signature
        sig2: Second signature
        tolerance: Maximum allowed difference per element

    Returns:
        True if signatures match within tolerance
    """
    if len(sig1) != len(sig2):
        return False

    return all(abs(v1 - v2) < tolerance for v1, v2 in zip(sig1, sig2))


def signature_similarity(
    sig1: Tuple[float, ...],
    sig2: Tuple[float, ...],
) -> float:
    """Compute similarity between two signatures.

    Args:
        sig1: First signature
        sig2: Second signature

    Returns:
        0.0 (completely different) to 1.0 (identical)
    """
    if len(sig1) != len(sig2):
        return 0.0

    # Exact match
    if sig1 == sig2:
        return 1.0

    # Compute normalized distance
    differences = 0.0
    for v1, v2 in zip(sig1, sig2):
        # Normalize by magnitude
        mag = max(abs(v1), abs(v2), 1)
        diff = abs(v1 - v2) / mag
        differences += diff

    # Convert to similarity score
    avg_diff = differences / len(sig1)
    similarity = max(0.0, 1.0 - avg_diff)

    return similarity


def analyze_growth(expr: Any) -> str:
    """Classify the growth pattern of an expression.

    Args:
        expr: Expression to analyze

    Returns:
        One of: 'constant', 'linear', 'quadratic', 'exponential', 'complex', 'explosive', 'error'
    """
    vals = []
    for x in range(10):
        try:
            v = expr.eval({'n': x})
            if abs(v) < 1e10:
                vals.append(v)
            else:
                return 'explosive'
        except Exception:
            return 'error'

    if len(vals) < 3:
        return 'error'

    # Check if constant
    if all(abs(vals[i] - vals[0]) < 0.01 for i in range(len(vals))):
        return 'constant'

    # Check linear (constant first differences)
    diffs = [vals[i + 1] - vals[i] for i in range(len(vals) - 1)]
    if all(abs(diffs[i] - diffs[0]) < 0.01 for i in range(len(diffs))):
        return 'linear'

    # Check quadratic (constant second differences)
    if len(diffs) > 1:
        diffs2 = [diffs[i + 1] - diffs[i] for i in range(len(diffs) - 1)]
        if all(abs(diffs2[i] - diffs2[0]) < 0.01 for i in range(len(diffs2))):
            return 'quadratic'

    # Check exponential (constant ratios)
    # Need all values > 0.1 to compute ratios safely
    if all(abs(v) > 0.1 for v in vals):
        try:
            ratios = [vals[i + 1] / vals[i] for i in range(len(vals) - 1)]
            if all(abs(ratios[i] - ratios[0]) < 0.01 for i in range(len(ratios))):
                return 'exponential'
        except ZeroDivisionError:
            pass

    return 'complex'
