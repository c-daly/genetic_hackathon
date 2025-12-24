"""
LEARNED SIMPLIFICATION TRANSFORMATIONS

GP discovers that different expressions have identical behavior.
When one is simpler, save as transformation rule.
Later evolution can apply these transformations.

Meta-computation: discovering rules for transforming computations.
"""

import json
import random
import hashlib
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Optional, Sequence, Tuple

from genetic_gp.core.logic import Implies, LVar
from genetic_gp.core.proofs import Proof, ProofStep
from genetic_gp.tools.algorithm import AlgorithmLibrary, discover_algorithms_from_solutions
from genetic_gp.core.runlog import RunLogger

# ============================================
# EXPRESSION TYPES
# ============================================

@dataclass
class Const:
    val: float
    def eval(self, env): return self.val
    def complexity(self): return 1
    def __repr__(self): return str(int(self.val) if self.val == int(self.val) else round(self.val, 2))

@dataclass
class Var:
    name: str
    def eval(self, env): return env.get(self.name, 0)
    def complexity(self): return 1
    def __repr__(self): return self.name

@dataclass
class BinOp:
    op: str
    left: Any
    right: Any
    
    def eval(self, env):
        try:
            l = self.left.eval(env)
            r = self.right.eval(env)
            if self.op == '+': return l + r
            if self.op == '-': return l - r
            if self.op == '*': return l * r
            if self.op == '/': return l / r if abs(r) > 0.001 else 0
            if self.op == '^': return l ** min(r, 10)
        except:
            return 0
    
    def complexity(self):
        return 1 + self.left.complexity() + self.right.complexity()
    
    def __repr__(self):
        return f"({self.left}{self.op}{self.right})"

@dataclass
class Sum:
    var: str
    start: Any
    end: Any
    body: Any
    
    def eval(self, env):
        try:
            s = int(self.start.eval(env))
            e = int(self.end.eval(env))
            total = 0
            for i in range(s, min(e + 1, s + 100)):
                new_env = env.copy()
                new_env[self.var] = i
                total += self.body.eval(new_env)
            return total
        except:
            return 0
    
    def complexity(self):
        return 3 + self.start.complexity() + self.end.complexity() + self.body.complexity()
    
    def __repr__(self):
        return f"Σ({self.var}={self.start}..{self.end})[{self.body}]"

# ============================================
# BEHAVIORAL SIGNATURE
# ============================================

def behavioral_signature(expr, test_range=20) -> Tuple[float, ...]:
    """Expression IS its behavior"""
    signature = []
    for x in range(test_range):
        try:
            result = expr.eval({'n': x})
            if abs(result) > 1e10:
                result = 1e10 if result > 0 else -1e10
            signature.append(round(result, 4))
        except:
            signature.append(0)
    return tuple(signature)

def signatures_match(sig1: Tuple, sig2: Tuple, tolerance=0.01) -> bool:
    """Do two signatures represent same function?"""
    if len(sig1) != len(sig2):
        return False
    return all(abs(v1 - v2) < tolerance for v1, v2 in zip(sig1, sig2))

# ============================================
# TRANSFORMATION LIBRARY
# ============================================

@dataclass
class Transformation:
    """A discovered simplification rule"""
    id: str
    from_expr: Any
    to_expr: Any
    from_signature: Tuple
    to_signature: Tuple
    complexity_reduction: int
    
    def __repr__(self):
        return f"{self.from_expr} → {self.to_expr} (Δ={-self.complexity_reduction})"

class TransformationLibrary:
    def __init__(self):
        self.transformations = []
    
    def discover_transformation(self, expr1, expr2) -> Optional[Transformation]:
        """Check if two expressions are equivalent, create transformation if one simpler"""
        sig1 = behavioral_signature(expr1)
        sig2 = behavioral_signature(expr2)
        
        if not signatures_match(sig1, sig2):
            return None
        
        c1 = expr1.complexity()
        c2 = expr2.complexity()
        
        # Only save if there's meaningful simplification
        if abs(c1 - c2) < 2:
            return None
        
        # Create transformation from complex to simple
        if c1 > c2:
            from_expr, to_expr = expr1, expr2
            complexity_reduction = c1 - c2
        else:
            from_expr, to_expr = expr2, expr1
            complexity_reduction = c2 - c1
        
        trans_id = hashlib.md5(f"{from_expr}{to_expr}".encode()).hexdigest()[:8]
        
        return Transformation(
            id=trans_id,
            from_expr=from_expr,
            to_expr=to_expr,
            from_signature=sig1,
            to_signature=sig2,
            complexity_reduction=complexity_reduction
        )
    
    def add_transformation(self, trans: Transformation):
        """Add transformation to library"""
        # Check if we already have this
        for t in self.transformations:
            if t.from_signature == trans.from_signature and t.to_signature == trans.to_signature:
                return False
        
        self.transformations.append(trans)
        print(f"\n  🔄 Discovered simplification:")
        print(f"     From: {trans.from_expr} (complexity {trans.from_expr.complexity()})")
        print(f"     To:   {trans.to_expr} (complexity {trans.to_expr.complexity()})")
        print(f"     Reduction: {trans.complexity_reduction}")
        return True
    
    def try_simplify(self, expr) -> Any:
        """Try to apply transformations to simplify expression"""
        best_expr = expr
        best_complexity = expr.complexity()
        
        for trans in self.transformations:
            # Check if this expression matches the transformation pattern
            sig = behavioral_signature(expr)
            if signatures_match(sig, trans.from_signature):
                # Apply transformation
                simplified = trans.to_expr
                if simplified.complexity() < best_complexity:
                    best_expr = simplified
                    best_complexity = simplified.complexity()
        
        return best_expr
    
    def list_transformations(self):
        if not self.transformations:
            print("\n  (No transformations discovered yet)")
            return
        
        print(f"\n{'='*70}")
        print(f"TRANSFORMATION LIBRARY: {len(self.transformations)} rules")
        print(f"{'='*70}")
        for i, trans in enumerate(self.transformations):
            print(f"\n{i+1}. Complexity reduction: {trans.complexity_reduction}")
            print(f"   {trans.from_expr}")
            print(f"   → {trans.to_expr}")

# ============================================
# PRIMITIVE LIBRARY
# ============================================

@dataclass
class ToolCall:
    tool_name: str
    arg: Any
    tool_library: Any

    def eval(self, env):
        tool_expr = self.tool_library.get_tool(self.tool_name)
        if tool_expr is None:
            return 0
        value = self.arg.eval(env)
        return tool_expr.eval({'n': value})

    def complexity(self):
        tool_expr = self.tool_library.get_tool(self.tool_name)
        if tool_expr is None:
            return 1 + self.arg.complexity()
        return 2 + self.arg.complexity() + tool_expr.complexity()

    def __repr__(self):
        return f"{self.tool_name}({self.arg})"


class PrimitiveLibrary:
    def __init__(self, min_fitness=0.99):
        self.tools = {}
        self.min_fitness = min_fitness

    def should_save(self, expr, fitness) -> bool:
        if fitness < self.min_fitness:
            return False
        signature = behavioral_signature(expr)
        return signature not in (tool["signature"] for tool in self.tools.values())

    def add_tool(self, name, expr):
        signature = behavioral_signature(expr)
        self.tools[name] = {"expr": expr, "signature": signature}
        print(f"\n  📦 Saved primitive: {name} -> {expr}")

    def get_tool(self, name):
        tool = self.tools.get(name)
        return tool["expr"] if tool else None

    def list_tools(self):
        if not self.tools:
            print("\n  (No primitives saved yet)")
            return
        print(f"\n{'='*70}")
        print(f"PRIMITIVE LIBRARY: {len(self.tools)} primitives")
        print(f"{'='*70}")
        for i, (name, tool) in enumerate(self.tools.items(), 1):
            print(f"\n{i}. {name}: {tool['expr']}")

# ============================================
# EVOLUTION WITH TRANSFORMATION DISCOVERY
# ============================================

class Solution:
    """Wrapper for expression + metadata"""
    def __init__(self, expr, fitness):
        self.expr = expr
        self.fitness = fitness
        self.signature = behavioral_signature(expr)
        self.complexity = expr.complexity()


@dataclass
class ExperimentProblem:
    name: str
    test_func: Any | None = None
    pop_size: int = 60
    gens: int = 60
    kind: str = "evolution"
    proof: Optional[Proof] = None
    expected_proof_valid: Optional[bool] = None


@dataclass
class ExperimentConfig:
    seed: Optional[int] = None
    problems: Sequence[ExperimentProblem] = None
    results_path: Optional[str] = None
    primitive_fitness: float = 0.99
    log_path: Optional[str] = None

def evolve_with_discovery(
    test_func,
    trans_lib,
    problem_name,
    pop_size=60,
    gens=60,
    rng=None,
    tool_lib=None,
    run_logger: RunLogger | None = None,
):
    """
    Evolution that discovers transformations during search.
    Compares solutions with same behavior but different complexity.
    """
    print(f"\n{'='*70}")
    print(f"PROBLEM: {problem_name}")
    print(f"{'='*70}")
    print(f"Transformations known: {len(trans_lib.transformations)}")
    if tool_lib:
        print(f"Primitives available: {len(tool_lib.tools)}")
    print()
    
    rng = rng or random
    population = [random_expr(0, 3, ['n'], rng=rng, tool_lib=tool_lib) for _ in range(pop_size)]
    if run_logger is not None:
        run_logger.log_event(
            "problem_started",
            {
                "name": problem_name,
                "pop_size": pop_size,
                "generations": gens,
            },
        )
    
    best_ever = None
    best_fitness = 0.0
    
    # Track all solutions we've seen
    all_solutions = []
    
    for gen in range(gens):
        # Evaluate
        scores = []
        for expr in population:
            fitness = test_func(lambda x: expr.eval({'n': x}))
            scores.append((expr, fitness))
            
            # Track this solution
            if fitness > 0.5:  # Track decent solutions
                all_solutions.append(Solution(expr, fitness))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        if run_logger is not None:
            run_logger.log_population(gen, scores)
        
        if scores[0][1] > best_fitness:
            best_fitness = scores[0][1]
            best_ever = scores[0][0]
        
        if gen % 20 == 0 or scores[0][1] >= 0.99:
            avg = sum(s for _, s in scores) / len(scores)
            print(f"Gen {gen:2d}: Best={scores[0][1]:.3f} Avg={avg:.3f}")
        
        if scores[0][1] >= 0.99:
            print(f"✓ SOLVED at gen {gen} - continuing to find alternatives...")
            if run_logger is not None:
                run_logger.log_event(
                    "solved",
                    {
                        "generation": gen,
                        "best_expr": repr(scores[0][0]),
                        "best_fitness": scores[0][1],
                    },
                )
        
        # Selection
        survivors = [e for e, _ in scores[:pop_size // 5]]
        
        # Next generation
        next_pop = survivors.copy()
        while len(next_pop) < pop_size:
            parent = rng.choice(survivors)
            child = mutate(parent, rate=0.2, rng=rng, tool_lib=tool_lib)
            
            # Maybe apply known simplifications
            if trans_lib.transformations and rng.random() < 0.2:
                child = trans_lib.try_simplify(child)
            
            next_pop.append(child)
        
        population = next_pop
    
    print(f"\nBest: {best_fitness:.3f}")
    print(f"Expression: {best_ever}")
    if run_logger is not None:
        run_logger.log_event(
            "problem_finished",
            {
                "name": problem_name,
                "best_expr": repr(best_ever),
                "best_fitness": best_fitness,
            },
        )
    
    # DISCOVERY PHASE: Look for transformations in solutions we found
    print(f"\n  🔬 Analyzing {len(all_solutions)} solutions for transformations...")
    
    discovered = 0
    # Compare solutions with same behavior
    for i in range(len(all_solutions)):
        for j in range(i + 1, len(all_solutions)):
            sol1 = all_solutions[i]
            sol2 = all_solutions[j]
            
            # Check if equivalent
            trans = trans_lib.discover_transformation(sol1.expr, sol2.expr)
            if trans:
                if trans_lib.add_transformation(trans):
                    discovered += 1
    
    if discovered > 0:
        print(f"  ✓ Discovered {discovered} new transformations!")
    else:
        print(f"  No new transformations found.")
    
    return best_ever, best_fitness, all_solutions

# ============================================
# RANDOM GENERATION & MUTATION
# ============================================

def random_expr(depth=0, max_depth=3, vars_avail=None, rng=None, tool_lib=None):
    if vars_avail is None:
        vars_avail = ['n']
    rng = rng or random
    
    if depth >= max_depth or rng.random() < 0.4:
        choice = rng.choice(['const', 'var'])
        if choice == 'const':
            return Const(rng.randint(0, 5))
        else:
            return Var(rng.choice(vars_avail))

    if tool_lib and tool_lib.tools and rng.random() < 0.3:
        tool_name = rng.choice(list(tool_lib.tools.keys()))
        arg = random_expr(depth + 1, max_depth, vars_avail, rng=rng, tool_lib=tool_lib)
        return ToolCall(tool_name, arg, tool_lib)

    choice = rng.choice(['binop', 'sum'])
    
    if choice == 'binop':
        op = rng.choice(['+', '-', '*', '/', '^'])
        left = random_expr(depth + 1, max_depth, vars_avail, rng=rng, tool_lib=tool_lib)
        right = random_expr(depth + 1, max_depth, vars_avail, rng=rng, tool_lib=tool_lib)
        return BinOp(op, left, right)
    
    elif choice == 'sum':
        var = rng.choice(['i', 'j', 'k'])
        start = random_expr(depth + 1, max_depth, vars_avail, rng=rng, tool_lib=tool_lib)
        end = random_expr(depth + 1, max_depth, vars_avail, rng=rng, tool_lib=tool_lib)
        body = random_expr(depth + 1, max_depth, vars_avail + [var], rng=rng, tool_lib=tool_lib)
        return Sum(var, start, end, body)

def mutate(expr, rate=0.3, rng=None, tool_lib=None):
    rng = rng or random
    if rng.random() < rate:
        return random_expr(0, 3, ['n'], rng=rng, tool_lib=tool_lib)
    
    if isinstance(expr, Const):
        return Const(expr.val + rng.uniform(-1, 1))
    elif isinstance(expr, Var):
        return expr
    elif isinstance(expr, BinOp):
        return BinOp(expr.op,
                    mutate(expr.left, rate, rng=rng, tool_lib=tool_lib),
                    mutate(expr.right, rate, rng=rng, tool_lib=tool_lib))
    elif isinstance(expr, Sum):
        return Sum(expr.var,
                  mutate(expr.start, rate, rng=rng, tool_lib=tool_lib),
                  mutate(expr.end, rate, rng=rng, tool_lib=tool_lib),
                  mutate(expr.body, rate, rng=rng, tool_lib=tool_lib))
    elif isinstance(expr, ToolCall):
        return ToolCall(expr.tool_name,
                        mutate(expr.arg, rate, rng=rng, tool_lib=tool_lib),
                        expr.tool_library)
    return expr

# ============================================
# TESTS
# ============================================

def test_double(func):
    tests = [(0,0), (1,2), (2,4), (3,6), (5,10), (10,20)]
    return sum(1 for n, exp in tests if abs(func(n) - exp) < 0.1) / len(tests)

def test_square(func):
    tests = [(0,0), (1,1), (2,4), (3,9), (4,16), (5,25)]
    return sum(1 for n, exp in tests if abs(func(n) - exp) < 0.1) / len(tests)

def test_sum_to_n(func):
    tests = [(1,1), (2,3), (3,6), (4,10), (5,15), (10,55)]
    return sum(1 for n, exp in tests if abs(func(n) - exp) < 0.1) / len(tests)

def test_cube(func):
    tests = [(0,0), (1,1), (2,8), (3,27), (4,64), (5,125)]
    return sum(1 for n, exp in tests if abs(func(n) - exp) < 0.1) / len(tests)

def test_linear_plus_one(func):
    tests = [(0,1), (1,3), (2,5), (3,7), (5,11), (10,21)]
    return sum(1 for n, exp in tests if abs(func(n) - exp) < 0.1) / len(tests)

# ============================================
# EXPERIMENT RUNNER
# ============================================

def _default_problems():
    return [
        ExperimentProblem("f(n) = 2n", test_double, pop_size=60, gens=40),
        ExperimentProblem("f(n) = n²", test_square, pop_size=60, gens=40),
        ExperimentProblem("f(n) = sum(1 to n)", test_sum_to_n, pop_size=60, gens=60),
        ExperimentProblem("f(n) = n³", test_cube, pop_size=60, gens=60),
        ExperimentProblem("Algorithm: f(n) = 2n + 1", test_linear_plus_one, pop_size=60, gens=60),
        _default_proof_problem(),
    ]


def _default_proof_problem() -> ExperimentProblem:
    p = LVar("P")
    q = LVar("Q")
    proof = Proof(
        [
            ProofStep(p, "assumption"),
            ProofStep(Implies(p, q), "assumption"),
            ProofStep(q, "modus_ponens", premises=(0, 1)),
        ]
    )
    return ExperimentProblem(
        "Proof: modus ponens",
        kind="proof",
        proof=proof,
        expected_proof_valid=True,
    )


def _serialize_transformation(trans):
    return {
        "id": trans.id,
        "from_expr": str(trans.from_expr),
        "to_expr": str(trans.to_expr),
        "complexity_reduction": trans.complexity_reduction,
        "from_signature": list(trans.from_signature),
        "to_signature": list(trans.to_signature),
    }


def run_simplification_experiment(config: Optional[ExperimentConfig] = None):
    if config is None:
        config = ExperimentConfig()
    if config.problems is None:
        config.problems = _default_problems()

    rng = random.Random(config.seed)
    trans_lib = TransformationLibrary()
    tool_lib = PrimitiveLibrary(min_fitness=config.primitive_fitness)
    algorithm_lib = AlgorithmLibrary()
    run_logger = RunLogger(Path(config.log_path), metadata={"seed": config.seed}) if config.log_path else None
    results = {"seed": config.seed, "problems": [], "proofs": []}

    for problem in config.problems:
        if problem.kind == "proof":
            if not problem.proof:
                raise ValueError(f"Proof problem '{problem.name}' missing proof.")
            print(f"\n{'='*70}")
            print(f"PROOF PROBLEM: {problem.name}")
            print(f"{'='*70}")
            valid, issues = problem.proof.verify()
            results["proofs"].append(
                {
                    "name": problem.name,
                    "valid": valid,
                    "expected_valid": problem.expected_proof_valid,
                    "issues": [
                        {
                            "step": issue.step_index,
                            "rule": issue.rule,
                            "message": issue.message,
                        }
                        for issue in issues
                    ],
                }
            )
            continue
        if problem.test_func is None:
            raise ValueError(f"Problem '{problem.name}' missing test function.")
        before_count = len(trans_lib.transformations)
        best, fitness, all_solutions = evolve_with_discovery(
            problem.test_func,
            trans_lib,
            problem.name,
            pop_size=problem.pop_size,
            gens=problem.gens,
            rng=rng,
            tool_lib=tool_lib,
            run_logger=run_logger,
        )
        discover_algorithms_from_solutions(
            [(sol.expr, sol.fitness) for sol in all_solutions],
            algorithm_lib,
        )
        after_count = len(trans_lib.transformations)
        saved_primitive = None
        if tool_lib.should_save(best, fitness):
            tool_name = f"primitive_{len(tool_lib.tools) + 1}"
            tool_lib.add_tool(tool_name, best)
            saved_primitive = tool_name
        results["problems"].append({
            "name": problem.name,
            "best_expr": str(best),
            "best_fitness": fitness,
            "new_transformations": after_count - before_count,
            "saved_primitive": saved_primitive,
        })

    results["transformations"] = [
        _serialize_transformation(t) for t in trans_lib.transformations
    ]
    results["primitives"] = [
        {"name": name, "expr": str(tool["expr"])}
        for name, tool in tool_lib.tools.items()
    ]
    results["algorithms"] = [
        {
            "id": algo.id,
            "template": algo.template.describe(),
            "examples": len(algo.examples),
        }
        for algo in algorithm_lib.list_algorithms()
    ]

    if config.results_path:
        with open(config.results_path, "w", encoding="utf-8") as handle:
            json.dump(results, handle, indent=2)
    if run_logger is not None:
        run_logger.close()

    return results, trans_lib, tool_lib, algorithm_lib

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    print("="*70)
    print("LEARNED SIMPLIFICATION TRANSFORMATIONS")
    print("="*70)
    print("\nGP discovers equivalent expressions with different complexity.")
    print("System learns its own optimization rules.")
    print("Simplification becomes a discoverable primitive.")
    print()
    
    print("\n" + "="*70)
    print("RUNNING EXPERIMENT")
    print("="*70)
    results, trans_lib, tool_lib, algorithm_lib = run_simplification_experiment()
    trans_lib.list_transformations()
    tool_lib.list_tools()
    algorithm_lib.print_summary()
    
    print("\n" + "="*70)
    print("RESULT")
    print("="*70)
    print(f"\nDiscovered {len(trans_lib.transformations)} simplification rules")
    print("\nKey insight:")
    print("  - System discovers multiple ways to compute same function")
    print("  - Compares complexity")
    print("  - Learns simplification transformations")
    print("  - Applies them in future problems")
    print()
    print("Meta-computation: Learning rules for transforming computations!")
