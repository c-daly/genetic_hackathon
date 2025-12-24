"""Algorithm discovery utilities.

Algorithms are generalized templates that capture structural patterns in
expressions while abstracting literal constants into parameters.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Tuple


TemplateNode = Tuple[Any, ...]


@dataclass
class AlgorithmExample:
    """A concrete instance of an algorithm template."""

    expr: str
    fitness: float
    params: Dict[str, float]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlgorithmTemplate:
    """A generalized structural template for expressions."""

    structure: TemplateNode
    params: List[str]

    def describe(self) -> str:
        """Return a readable template string."""
        return _format_structure(self.structure)


@dataclass
class Algorithm:
    """A discovered algorithmic template with supporting examples."""

    id: str
    template: AlgorithmTemplate
    examples: List[AlgorithmExample] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_example(self, example: AlgorithmExample) -> None:
        self.examples.append(example)


class AlgorithmLibrary:
    """Library for discovering and storing algorithm templates."""

    def __init__(self, min_occurrences: int = 2, min_fitness: float = 0.9):
        self._algorithms: Dict[TemplateNode, Algorithm] = {}
        self._candidates: Dict[TemplateNode, List[AlgorithmExample]] = {}
        self._seen_exprs: set[str] = set()
        self.min_occurrences = min_occurrences
        self.min_fitness = min_fitness

    def consider(self, expr: Any, fitness: float, metadata: Dict[str, Any] | None = None) -> bool:
        """Consider an expression for algorithm discovery.

        Returns True if this adds a new algorithm or extends an existing one.
        """
        if fitness < self.min_fitness:
            return False

        expr_key = repr(expr)
        if expr_key in self._seen_exprs:
            return False
        self._seen_exprs.add(expr_key)

        template, params = extract_algorithm_template(expr)
        example = AlgorithmExample(expr=expr_key, fitness=fitness, params=params, metadata=metadata or {})

        existing = self._algorithms.get(template.structure)
        if existing:
            existing.add_example(example)
            return True

        candidates = self._candidates.setdefault(template.structure, [])
        candidates.append(example)

        if len(candidates) >= self.min_occurrences:
            algo = Algorithm(
                id=_template_id(template.structure),
                template=template,
                examples=candidates,
            )
            self._algorithms[template.structure] = algo
            del self._candidates[template.structure]
            return True

        return False

    def list_algorithms(self) -> List[Algorithm]:
        return list(self._algorithms.values())

    def __len__(self) -> int:
        return len(self._algorithms)

    def __iter__(self):
        return iter(self._algorithms.values())

    def print_summary(self) -> None:
        if not self._algorithms:
            print("\n  (No algorithms discovered yet)")
            return

        print(f"\n{'=' * 70}")
        print(f"ALGORITHM LIBRARY: {len(self._algorithms)} templates")
        print(f"{'=' * 70}")

        for i, algo in enumerate(self._algorithms.values(), 1):
            print(f"\n{i}. Template: {algo.template.describe()}")
            print(f"   Examples: {len(algo.examples)}")


def extract_algorithm_template(expr: Any) -> tuple[AlgorithmTemplate, Dict[str, float]]:
    """Extract a generalized template from an expression.

    Constants become parameters (p0, p1, ...), while variables and structure are preserved.
    Returns the template and concrete parameter values.
    """
    param_names: List[str] = []
    param_values: Dict[str, float] = {}

    def walk(node: Any) -> TemplateNode:
        node_type = type(node).__name__
        if node_type == "Const":
            param_name = f"p{len(param_names)}"
            param_names.append(param_name)
            param_values[param_name] = getattr(node, "val")
            return ("Param", param_name)
        if node_type == "Var":
            return ("Var", getattr(node, "name"))
        if node_type == "BinOp":
            return (
                "BinOp",
                getattr(node, "op"),
                walk(getattr(node, "left")),
                walk(getattr(node, "right")),
            )
        if node_type == "Sum":
            return (
                "Sum",
                getattr(node, "var"),
                walk(getattr(node, "start")),
                walk(getattr(node, "end")),
                walk(getattr(node, "body")),
            )
        if node_type == "Product":
            return (
                "Product",
                getattr(node, "var"),
                walk(getattr(node, "start")),
                walk(getattr(node, "end")),
                walk(getattr(node, "body")),
            )
        if node_type == "PrimitiveCall":
            return (
                "PrimitiveCall",
                getattr(node, "primitive_name"),
                walk(getattr(node, "arg")),
            )
        raise ValueError(f"Unsupported expression type for algorithm template: {node_type}")

    structure = walk(expr)
    return AlgorithmTemplate(structure=structure, params=param_names), param_values


def discover_algorithms_from_solutions(
    solutions: Iterable[Tuple[Any, float]],
    library: AlgorithmLibrary,
    min_fitness: float | None = None,
    min_occurrences: int | None = None,
) -> int:
    """Discover algorithms from a set of (expr, fitness) solutions."""
    if min_fitness is not None:
        library.min_fitness = min_fitness
    if min_occurrences is not None:
        library.min_occurrences = min_occurrences

    discovered = 0
    for expr, fitness in solutions:
        if library.consider(expr, fitness):
            discovered += 1

    return discovered


def _template_id(structure: TemplateNode) -> str:
    hash_input = repr(structure).encode("utf-8")
    return hashlib.md5(hash_input).hexdigest()[:8]


def _format_structure(node: TemplateNode) -> str:
    kind = node[0]
    if kind == "Param":
        return node[1]
    if kind == "Var":
        return node[1]
    if kind == "BinOp":
        _, op, left, right = node
        return f"({_format_structure(left)}{op}{_format_structure(right)})"
    if kind == "Sum":
        _, var, start, end, body = node
        return f"Σ({var}={_format_structure(start)}..{_format_structure(end)})[{_format_structure(body)}]"
    if kind == "Product":
        _, var, start, end, body = node
        return f"∏({var}={_format_structure(start)}..{_format_structure(end)})[{_format_structure(body)}]"
    if kind == "PrimitiveCall":
        _, name, arg = node
        return f"{name}({_format_structure(arg)})"
    return repr(node)
