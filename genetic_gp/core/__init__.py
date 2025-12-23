"""Core expression types and behavioral signatures"""

from genetic_gp.core.expressions import Const, Var, BinOp, Sum, Product, ToolCall, Expression
from genetic_gp.core.signatures import (
    behavioral_signature,
    signatures_match,
    signature_similarity,
    analyze_growth,
)
from genetic_gp.core.logic import (
    LConst,
    LVar,
    Not,
    And,
    Or,
    Implies,
    Iff,
    LogicExpression,
    get_variables,
    truth_table,
    tables_equivalent,
    expressions_equivalent,
    is_tautology,
    is_contradiction,
    is_contingent,
    is_satisfiable,
    classify_expression,
)

__all__ = [
    # Math expressions
    "Const",
    "Var",
    "BinOp",
    "Sum",
    "Product",
    "ToolCall",
    "Expression",
    # Signatures
    "behavioral_signature",
    "signatures_match",
    "signature_similarity",
    "analyze_growth",
    # Logic expressions
    "LConst",
    "LVar",
    "Not",
    "And",
    "Or",
    "Implies",
    "Iff",
    "LogicExpression",
    "get_variables",
    "truth_table",
    "tables_equivalent",
    "expressions_equivalent",
    "is_tautology",
    "is_contradiction",
    "is_contingent",
    "is_satisfiable",
    "classify_expression",
]
