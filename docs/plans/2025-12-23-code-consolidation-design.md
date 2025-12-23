# Code Consolidation Design

Restructure the PoC from 7 standalone scripts into a proper Python package with shared components.

## Current State

7 files with significant duplication:
- Expression types duplicated ~80 lines × 7 files
- `random_expr()` duplicated ~40 lines × 7 files
- `mutate()` duplicated ~30 lines × 7 files
- Evolution loop duplicated ~60 lines × 7 files
- Test functions duplicated across files
- `behavioral_signature()` duplicated 4 times

## Target Structure

```
genetic_gp/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── expressions.py    # Expression protocol + math types
│   ├── logic.py          # Logic expression types
│   └── signatures.py     # Behavioral signatures
├── evolution/
│   ├── __init__.py
│   ├── generator.py      # Random expression generation
│   ├── mutation.py       # Mutation operators
│   └── engine.py         # Evolution loop
├── tools/
│   ├── __init__.py
│   ├── library.py        # Tool storage
│   ├── transformation.py # Transformation discovery
│   └── generalization.py # Pattern extraction
├── problems/
│   ├── __init__.py
│   └── math.py           # Test problem definitions
└── experiments/
    ├── __init__.py
    ├── compositional.py  # Tool accumulation demo
    ├── simplification.py # Learned transformations demo
    ├── novelty.py        # Novelty detection demo
    ├── logic.py          # Logic domain demo
    └── simplicity.py     # Simplicity-driven demo
```

## Module Designs

### core/expressions.py

Protocol-based expression system:

```python
from typing import Protocol, Any, Dict

class Expression(Protocol):
    def eval(self, env: Dict[str, Any]) -> float: ...
    def complexity(self) -> int: ...

@dataclass
class Const:
    val: float
    def eval(self, env): return self.val
    def complexity(self): return 1

@dataclass
class Var:
    name: str
    def eval(self, env): return env.get(self.name, 0)
    def complexity(self): return 1

@dataclass
class BinOp:
    op: str  # '+', '-', '*', '/', '^'
    left: Expression
    right: Expression
    def eval(self, env): ...
    def complexity(self): return 1 + self.left.complexity() + self.right.complexity()

@dataclass
class Sum:
    var: str
    start: Expression
    end: Expression
    body: Expression
    def eval(self, env): ...  # With iteration cap at 100
    def complexity(self): return 3 + children

@dataclass
class Product:
    var: str
    start: Expression
    end: Expression
    body: Expression
    def eval(self, env): ...
    def complexity(self): return 3 + children
```

### core/logic.py

Logic-specific expressions following same protocol:

```python
@dataclass
class Const:
    val: bool

@dataclass
class Var:
    name: str

@dataclass
class Not:
    expr: Expression

@dataclass
class And:
    left: Expression
    right: Expression

@dataclass
class Or:
    left: Expression
    right: Expression

@dataclass
class Implies:
    left: Expression
    right: Expression

@dataclass
class Iff:
    left: Expression
    right: Expression
```

### core/signatures.py

Behavioral identification:

```python
def behavioral_signature(
    expr: Expression,
    test_inputs: Iterable[int] = range(20),
    var_name: str = 'n'
) -> tuple[float, ...]:
    """Compute I/O signature for an expression"""

def signatures_match(sig1: tuple, sig2: tuple, tolerance: float = 0.01) -> bool:
    """Check if two signatures represent the same function"""

def signature_similarity(sig1: tuple, sig2: tuple) -> float:
    """0.0 (different) to 1.0 (identical)"""

def truth_table(expr: Expression, variables: list[str]) -> tuple[bool, ...]:
    """Generate truth table for logic expressions"""
```

### evolution/generator.py

```python
def random_expr(
    depth: int = 0,
    max_depth: int = 3,
    vars_available: list[str] | None = None,
    tool_library: ToolLibrary | None = None,
) -> Expression:
    """Generate random mathematical expression"""

def random_logic_expr(
    depth: int = 0,
    max_depth: int = 3,
    vars_available: list[str] | None = None,
) -> Expression:
    """Generate random logic expression"""
```

### evolution/mutation.py

```python
def mutate(
    expr: Expression,
    rate: float = 0.3,
    vars_available: list[str] | None = None,
    tool_library: ToolLibrary | None = None,
) -> Expression:
    """Mutate expression tree"""

def mutate_logic(
    expr: Expression,
    rate: float = 0.3,
) -> Expression:
    """Mutate logic expression tree"""
```

### evolution/engine.py

```python
@dataclass
class EvolutionResult:
    best_expr: Expression
    best_fitness: float
    generations_run: int
    all_solutions: list[tuple[Expression, float]] | None = None

def evolve(
    fitness_fn: Callable[[Callable], float],
    pop_size: int = 60,
    generations: int = 60,
    vars_available: list[str] | None = None,
    tool_library: ToolLibrary | None = None,
    collect_solutions_above: float | None = None,  # Track solutions above threshold
    on_generation: Callable[[int, list], None] | None = None,  # Hook for reporting
    stop_at_fitness: float = 0.99,
) -> EvolutionResult:
    """Core evolution loop"""
```

### tools/library.py

```python
@dataclass
class Tool:
    name: str
    expr: Expression
    signature: tuple
    params: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

class ToolLibrary:
    def __init__(self): ...
    def add(self, tool: Tool) -> bool: ...
    def get(self, name: str) -> Tool | None: ...
    def find_by_signature(self, sig: tuple, tolerance: float = 0.01) -> Tool | None: ...
    def is_novel(self, expr: Expression, threshold: float = 0.3) -> bool: ...
    def is_trivial(self, expr: Expression) -> bool: ...
    def list_tools(self) -> list[Tool]: ...
```

### tools/transformation.py

```python
@dataclass
class Transformation:
    id: str
    from_signature: tuple
    to_expr: Expression
    complexity_reduction: int

class TransformationLibrary:
    def __init__(self): ...
    def discover(self, expr1: Expression, expr2: Expression) -> Transformation | None: ...
    def add(self, trans: Transformation) -> bool: ...
    def try_simplify(self, expr: Expression) -> Expression: ...
    def list_transformations(self) -> list[Transformation]: ...
```

### tools/generalization.py

```python
def generalize_pattern(expr: Expression) -> Tool | None:
    """Extract parameterized tool from specific expression.

    Patterns recognized:
    - n^k → power(exp)
    - n*k → scale(factor)
    - Σ(i=1..n)[i^k] → sum_powers(k)
    """
```

### problems/math.py

```python
def test_double(func: Callable[[int], float]) -> float: ...
def test_square(func: Callable[[int], float]) -> float: ...
def test_cube(func: Callable[[int], float]) -> float: ...
def test_sum_to_n(func: Callable[[int], float]) -> float: ...
def test_factorial(func: Callable[[int], float]) -> float: ...
def test_sum_of_squares(func: Callable[[int], float]) -> float: ...
def test_integral_x(func: Callable[[int], float]) -> float: ...
```

## Experiments

Each experiment becomes a thin script composing shared components:

### experiments/compositional.py (~60 lines)

```python
from genetic_gp.evolution import evolve
from genetic_gp.tools import ToolLibrary
from genetic_gp.problems import test_double, test_sum_to_n, test_factorial

def main():
    library = ToolLibrary()

    # Problem 1
    result = evolve(test_double, tool_library=library)
    library.add(Tool("double", result.best_expr, ...))

    # Problem 2 - can now use 'double' tool
    result = evolve(test_sum_to_n, tool_library=library)
    ...
```

### experiments/simplification.py (~80 lines)

```python
from genetic_gp.evolution import evolve
from genetic_gp.tools import TransformationLibrary

def main():
    trans_lib = TransformationLibrary()

    result = evolve(
        test_double,
        collect_solutions_above=0.5,  # Track alternatives
    )

    # Discover transformations from collected solutions
    for i, (e1, _) in enumerate(result.all_solutions):
        for e2, _ in result.all_solutions[i+1:]:
            trans = trans_lib.discover(e1, e2)
            if trans:
                trans_lib.add(trans)
```

## Implementation Order

1. `core/expressions.py` - Foundation
2. `core/signatures.py` - Behavioral comparison
3. `evolution/generator.py` - Random generation
4. `evolution/mutation.py` - Mutation
5. `evolution/engine.py` - Evolution loop
6. `tools/library.py` - Tool storage
7. `problems/math.py` - Test problems
8. `experiments/compositional.py` - First experiment port
9. `tools/transformation.py` - Transformation discovery
10. `tools/generalization.py` - Pattern extraction
11. `core/logic.py` - Logic domain
12. Remaining experiments

## Testing

Add `tests/` directory with pytest:
- `test_expressions.py` - Expression eval and complexity
- `test_signatures.py` - Signature computation and matching
- `test_evolution.py` - Evolution converges on simple problems
- `test_tools.py` - Tool library operations
