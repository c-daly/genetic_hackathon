"""
LEARNED SIMPLIFICATION TRANSFORMATIONS

GP discovers that different expressions have identical behavior.
When one is simpler, save as transformation rule.
Later evolution can apply these transformations.

Meta-computation: discovering rules for transforming computations.
"""

import random
import hashlib
from dataclasses import dataclass
from typing import Any, List, Tuple, Optional

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
# EVOLUTION WITH TRANSFORMATION DISCOVERY
# ============================================

class Solution:
    """Wrapper for expression + metadata"""
    def __init__(self, expr, fitness):
        self.expr = expr
        self.fitness = fitness
        self.signature = behavioral_signature(expr)
        self.complexity = expr.complexity()

def evolve_with_discovery(test_func, trans_lib, problem_name, pop_size=60, gens=60):
    """
    Evolution that discovers transformations during search.
    Compares solutions with same behavior but different complexity.
    """
    print(f"\n{'='*70}")
    print(f"PROBLEM: {problem_name}")
    print(f"{'='*70}")
    print(f"Transformations known: {len(trans_lib.transformations)}")
    print()
    
    population = [random_expr(0, 3, ['n']) for _ in range(pop_size)]
    
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
        
        if scores[0][1] > best_fitness:
            best_fitness = scores[0][1]
            best_ever = scores[0][0]
        
        if gen % 20 == 0 or scores[0][1] >= 0.99:
            avg = sum(s for _, s in scores) / len(scores)
            print(f"Gen {gen:2d}: Best={scores[0][1]:.3f} Avg={avg:.3f}")
        
        if scores[0][1] >= 0.99:
            print(f"✓ SOLVED at gen {gen} - continuing to find alternatives...")
        
        # Selection
        survivors = [e for e, _ in scores[:pop_size // 5]]
        
        # Next generation
        next_pop = survivors.copy()
        while len(next_pop) < pop_size:
            parent = random.choice(survivors)
            child = mutate(parent, rate=0.2)
            
            # Maybe apply known simplifications
            if trans_lib.transformations and random.random() < 0.2:
                child = trans_lib.try_simplify(child)
            
            next_pop.append(child)
        
        population = next_pop
    
    print(f"\nBest: {best_fitness:.3f}")
    print(f"Expression: {best_ever}")
    
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
    
    return best_ever, best_fitness

# ============================================
# RANDOM GENERATION & MUTATION
# ============================================

def random_expr(depth=0, max_depth=3, vars_avail=None):
    if vars_avail is None:
        vars_avail = ['n']
    
    if depth >= max_depth or random.random() < 0.4:
        choice = random.choice(['const', 'var'])
        if choice == 'const':
            return Const(random.randint(0, 5))
        else:
            return Var(random.choice(vars_avail))
    
    choice = random.choice(['binop', 'sum'])
    
    if choice == 'binop':
        op = random.choice(['+', '-', '*', '/', '^'])
        left = random_expr(depth + 1, max_depth, vars_avail)
        right = random_expr(depth + 1, max_depth, vars_avail)
        return BinOp(op, left, right)
    
    elif choice == 'sum':
        var = random.choice(['i', 'j', 'k'])
        start = random_expr(depth + 1, max_depth, vars_avail)
        end = random_expr(depth + 1, max_depth, vars_avail)
        body = random_expr(depth + 1, max_depth, vars_avail + [var])
        return Sum(var, start, end, body)

def mutate(expr, rate=0.3):
    if random.random() < rate:
        return random_expr(0, 3, ['n'])
    
    if isinstance(expr, Const):
        return Const(expr.val + random.uniform(-1, 1))
    elif isinstance(expr, Var):
        return expr
    elif isinstance(expr, BinOp):
        return BinOp(expr.op,
                    mutate(expr.left, rate),
                    mutate(expr.right, rate))
    elif isinstance(expr, Sum):
        return Sum(expr.var,
                  mutate(expr.start, rate),
                  mutate(expr.end, rate),
                  mutate(expr.body, rate))
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
    
    trans_lib = TransformationLibrary()
    
    # Problem 1: Double
    print("\n" + "="*70)
    print("PHASE 1: Initial Problems")
    print("="*70)
    
    best, fit = evolve_with_discovery(test_double, trans_lib, "f(n) = 2n", 
                                     pop_size=60, gens=40)
    
    # Problem 2: Square
    best, fit = evolve_with_discovery(test_square, trans_lib, "f(n) = n²",
                                     pop_size=60, gens=40)
    
    # Problem 3: Sum
    best, fit = evolve_with_discovery(test_sum_to_n, trans_lib, "f(n) = sum(1 to n)",
                                     pop_size=60, gens=60)
    
    # Show discovered transformations
    trans_lib.list_transformations()
    
    # Problem 4: Cube - can now use transformations
    print("\n" + "="*70)
    print("PHASE 2: Using Learned Transformations")
    print("="*70)
    
    best, fit = evolve_with_discovery(test_cube, trans_lib, "f(n) = n³",
                                     pop_size=60, gens=60)
    
    # Final report
    trans_lib.list_transformations()
    
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
