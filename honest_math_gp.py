"""
HONEST MATHEMATICAL GP
No templates. No pre-coded solutions. Pure random generation.

Primitives:
- Constants: 0, 1, 2
- Variables: n, i, j
- Operations: +, -, *, /
- Summation: Σ(var=start to end) body
- Comparisons: <, >, ==

Generate completely random expressions and see what evolves.
"""

import random
from dataclasses import dataclass
from typing import Any

# ============================================
# EXPRESSION TYPES
# ============================================

@dataclass
class Const:
    val: int
    def eval(self, env): 
        return self.val
    def __repr__(self): 
        return str(self.val)

@dataclass
class Var:
    name: str
    def eval(self, env): 
        return env.get(self.name, 0)
    def __repr__(self): 
        return self.name

@dataclass
class BinOp:
    op: str  # '+', '-', '*', '/'
    left: Any
    right: Any
    
    def eval(self, env):
        try:
            l = self.left.eval(env)
            r = self.right.eval(env)
            if self.op == '+': return l + r
            if self.op == '-': return l - r
            if self.op == '*': return l * r
            if self.op == '/': return l / r if r != 0 else 0
        except:
            return 0
    
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
            for i in range(s, min(e + 1, s + 100)):  # Cap at 100 iterations
                new_env = env.copy()
                new_env[self.var] = i
                total += self.body.eval(new_env)
            return total
        except:
            return 0
    
    def __repr__(self):
        return f"Σ({self.var}={self.start}..{self.end})[{self.body}]"

# ============================================
# PURE RANDOM GENERATION
# ============================================

def random_expr(depth=0, max_depth=3, vars_available=None):
    """
    Generate completely random expression.
    NO TEMPLATES. NO HINTS. Just random primitives.
    """
    if vars_available is None:
        vars_available = ['n']
    
    # At max depth or randomly: terminal
    if depth >= max_depth or random.random() < 0.4:
        # Pick: constant or variable
        if random.random() < 0.5:
            return Const(random.randint(0, 5))
        else:
            return Var(random.choice(vars_available))
    
    # Otherwise: compound expression
    choice = random.choice(['binop', 'sum'])
    
    if choice == 'binop':
        op = random.choice(['+', '-', '*', '/'])
        left = random_expr(depth + 1, max_depth, vars_available)
        right = random_expr(depth + 1, max_depth, vars_available)
        return BinOp(op, left, right)
    
    elif choice == 'sum':
        # Summation
        loop_var = random.choice(['i', 'j', 'k'])
        start = random_expr(depth + 1, max_depth, vars_available)
        end = random_expr(depth + 1, max_depth, vars_available)
        body = random_expr(depth + 1, max_depth, vars_available + [loop_var])
        return Sum(loop_var, start, end, body)

# ============================================
# MUTATION
# ============================================

def mutate(expr, rate=0.3, vars_available=None):
    """Mutate expression tree"""
    if vars_available is None:
        vars_available = ['n']
    
    # Random replacement
    if random.random() < rate:
        return random_expr(0, 3, vars_available)
    
    # Structural mutation
    if isinstance(expr, Const):
        return Const(expr.val + random.randint(-2, 2))
    
    elif isinstance(expr, Var):
        return expr
    
    elif isinstance(expr, BinOp):
        return BinOp(
            expr.op,
            mutate(expr.left, rate, vars_available),
            mutate(expr.right, rate, vars_available)
        )
    
    elif isinstance(expr, Sum):
        return Sum(
            expr.var,
            mutate(expr.start, rate, vars_available),
            mutate(expr.end, rate, vars_available),
            mutate(expr.body, rate, vars_available + [expr.var])
        )
    
    return expr

# ============================================
# EVOLUTION
# ============================================

def evolve(test_func, pop_size=50, gens=200):
    """
    Evolve expression to match test function.
    Pure random start. No hints. No templates.
    """
    
    print("Starting evolution...")
    print(f"Population: {pop_size}")
    print(f"Generations: {gens}")
    print()
    
    # Initialize with PURE RANDOM expressions
    population = [random_expr(0, 3, ['n']) for _ in range(pop_size)]
    
    best_ever = None
    best_fitness = 0.0
    
    for gen in range(gens):
        # Evaluate
        scores = []
        for expr in population:
            fitness = test_func(lambda n: expr.eval({'n': n}))
            scores.append((expr, fitness))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # Track best
        if scores[0][1] > best_fitness:
            best_fitness = scores[0][1]
            best_ever = scores[0][0]
        
        # Report
        if gen % 20 == 0 or scores[0][1] >= 0.99:
            avg = sum(s for _, s in scores) / len(scores)
            print(f"Gen {gen:3d}: Best={scores[0][1]:.3f} Avg={avg:.3f} | {scores[0][0]}")
        
        # Check if solved
        if scores[0][1] >= 0.99:
            print(f"\n✓ SOLVED at generation {gen}")
            return scores[0][0], scores[0][1]
        
        # Selection - keep top 20%
        survivors = [e for e, _ in scores[:pop_size // 5]]
        
        # Breed next generation
        next_pop = survivors.copy()
        while len(next_pop) < pop_size:
            parent = random.choice(survivors)
            child = mutate(parent, rate=0.2, vars_available=['n'])
            next_pop.append(child)
        
        population = next_pop
    
    print(f"\nBest after {gens} generations: {best_fitness:.3f}")
    return best_ever, best_fitness

# ============================================
# TEST PROBLEMS
# ============================================

def test_sum_1_to_n(func):
    """Test: sum(1 to n) = 1+2+...+n"""
    tests = [(1, 1), (2, 3), (3, 6), (4, 10), (5, 15)]
    correct = 0
    for n, expected in tests:
        try:
            result = func(n)
            if abs(result - expected) < 0.1:
                correct += 1
        except:
            pass
    return correct / len(tests)

def test_double(func):
    """Test: 2n"""
    tests = [(0, 0), (1, 2), (2, 4), (3, 6), (5, 10)]
    correct = 0
    for n, expected in tests:
        try:
            result = func(n)
            if abs(result - expected) < 0.1:
                correct += 1
        except:
            pass
    return correct / len(tests)

def test_square(func):
    """Test: n²"""
    tests = [(0, 0), (1, 1), (2, 4), (3, 9), (4, 16)]
    correct = 0
    for n, expected in tests:
        try:
            result = func(n)
            if abs(result - expected) < 0.1:
                correct += 1
        except:
            pass
    return correct / len(tests)

# ============================================
# RUN
# ============================================

if __name__ == '__main__':
    print("="*70)
    print("HONEST MATHEMATICAL GP TEST")
    print("="*70)
    print("\nPure random generation from primitives:")
    print("  - Constants: 0, 1, 2, 3, 4, 5")
    print("  - Variables: n, i, j, k")
    print("  - Operations: +, -, *, /")
    print("  - Summation: Σ(var=start..end)[body]")
    print()
    print("NO TEMPLATES. NO PRE-CODED SOLUTIONS.")
    print()
    
    # Try harder problem - sum 1 to n
    print("="*70)
    print("PROBLEM: f(n) = 1+2+3+...+n (sum 1 to n)")
    print("="*70)
    best, fitness = evolve(test_sum_1_to_n, pop_size=100, gens=200)
    
    if fitness >= 0.99:
        print(f"\nDiscovered: {best}")
        print("\nTesting:")
        for n in [1, 2, 3, 4, 5, 10]:
            result = best.eval({'n': n})
            expected = n * (n + 1) // 2
            print(f"  f({n}) = {result:.1f} (expected {expected})")
    else:
        print(f"\nDid not solve. Best: {best} (fitness {fitness:.3f})")
    
    print()
    print("="*70)
    print("RESULT")
    print("="*70)
    if fitness >= 0.99:
        print("✓ Evolution discovered a solution from pure random generation!")
    elif fitness > 0.6:
        print("~ Partial progress. More generations or better mutation needed.")
    else:
        print("✗ Struggled. May need different approach or primitives.")
    print()
    print("This is honest - no templates, no cheating.")
