"""
FUNCTIONAL EQUIVALENCE & NOVELTY DETECTION

Uses behavioral signatures to detect equivalent patterns.
Only saves tools that are novel and non-trivial.
"""

import random
import hashlib
import math
from dataclasses import dataclass
from typing import Any, List, Tuple

# ============================================
# EXPRESSION TYPES
# ============================================

@dataclass
class Const:
    val: float
    def eval(self, env): return self.val
    def complexity(self): return 1
    def __repr__(self): return str(int(self.val) if self.val == int(self.val) else self.val)

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

@dataclass
class ToolCall:
    tool_id: str
    arg: Any
    tool_library: Any
    
    def eval(self, env):
        try:
            tool = self.tool_library.get_tool(self.tool_id)
            if tool is None:
                return 0
            arg_val = self.arg.eval(env)
            return tool['structure'].eval({'n': arg_val})
        except:
            return 0
    
    def complexity(self):
        return 2 + self.arg.complexity()
    
    def __repr__(self):
        tool = self.tool_library.get_tool(self.tool_id)
        if tool and 'name' in tool:
            return f"{tool['name']}({self.arg})"
        return f"tool_{self.tool_id[:4]}({self.arg})"

# ============================================
# BEHAVIORAL SIGNATURE
# ============================================

def behavioral_signature(expr, test_range=20) -> Tuple[float, ...]:
    """
    A function IS its input/output behavior.
    Returns tuple of outputs for test inputs.
    """
    signature = []
    for x in range(test_range):
        try:
            result = expr.eval({'n': x})
            # Cap to prevent overflow
            if abs(result) > 1e10:
                result = 1e10 if result > 0 else -1e10
            signature.append(round(result, 6))
        except:
            signature.append(0)
    return tuple(signature)

def signature_similarity(sig1: Tuple, sig2: Tuple) -> float:
    """
    How similar are two behavioral signatures?
    Returns 0.0 (completely different) to 1.0 (identical)
    """
    if len(sig1) != len(sig2):
        return 0.0
    
    # Exact match
    if sig1 == sig2:
        return 1.0
    
    # Compute normalized distance
    differences = 0
    for v1, v2 in zip(sig1, sig2):
        # Normalize by magnitude
        mag = max(abs(v1), abs(v2), 1)
        diff = abs(v1 - v2) / mag
        differences += diff
    
    # Convert to similarity score
    avg_diff = differences / len(sig1)
    similarity = max(0, 1.0 - avg_diff)
    
    return similarity

# ============================================
# GROWTH PATTERN ANALYSIS
# ============================================

def analyze_growth(expr) -> str:
    """Classify the growth pattern"""
    vals = []
    for x in range(10):
        try:
            v = expr.eval({'n': x})
            if abs(v) < 1e10:
                vals.append(v)
            else:
                return 'explosive'
        except:
            return 'error'
    
    # Check if constant
    if all(abs(vals[i] - vals[0]) < 0.01 for i in range(len(vals))):
        return 'constant'
    
    # Check linear (constant first differences)
    diffs = [vals[i+1] - vals[i] for i in range(len(vals)-1)]
    if all(abs(diffs[i] - diffs[0]) < 0.01 for i in range(len(diffs))):
        return 'linear'
    
    # Check quadratic (constant second differences)
    if len(diffs) > 1:
        diffs2 = [diffs[i+1] - diffs[i] for i in range(len(diffs)-1)]
        if all(abs(diffs2[i] - diffs2[0]) < 0.01 for i in range(len(diffs2))):
            return 'quadratic'
    
    # Check exponential (constant ratios)
    if all(v > 0.1 for v in vals[1:]):
        ratios = [vals[i+1]/vals[i] for i in range(len(vals)-1)]
        if all(abs(ratios[i] - ratios[0]) < 0.01 for i in range(len(ratios))):
            return 'exponential'
    
    return 'complex'

# ============================================
# TOOL LIBRARY WITH NOVELTY DETECTION
# ============================================

class ToolLibrary:
    def __init__(self):
        self.tools = []
    
    def structural_hash(self, expr):
        return hashlib.md5(str(expr).encode()).hexdigest()[:8]
    
    def is_trivial(self, expr) -> bool:
        """Is this just a primitive operation?"""
        # Single operations like n*2, n+n, n^2 are trivial
        if isinstance(expr, BinOp):
            # Both sides simple?
            left_simple = isinstance(expr.left, (Var, Const))
            right_simple = isinstance(expr.right, (Var, Const))
            if left_simple and right_simple:
                # n*2, n+n, etc = trivial
                return True
        
        # Constant or variable alone = trivial
        if isinstance(expr, (Const, Var)):
            return True
        
        # Has real structure (summation, tool call, nested operations)
        return False
    
    def novelty_score(self, expr) -> float:
        """
        How novel is this expression compared to existing tools?
        Returns 0.0 (duplicate) to 1.0 (completely novel)
        """
        if not self.tools:
            return 1.0
        
        # Get behavioral signature
        new_sig = behavioral_signature(expr)
        
        # Compare to all existing tools
        max_similarity = 0.0
        for tool in self.tools:
            tool_sig = behavioral_signature(tool['structure'])
            similarity = signature_similarity(new_sig, tool_sig)
            max_similarity = max(max_similarity, similarity)
        
        novelty = 1.0 - max_similarity
        return novelty
    
    def should_save(self, expr, fitness) -> bool:
        """Should we save this tool?"""
        # Must solve problem well
        if fitness < 0.95:
            return False
        
        # Must not be trivial
        if self.is_trivial(expr):
            print(f"    ✗ Rejected: trivial pattern {expr}")
            return False
        
        # Must be novel
        novelty = self.novelty_score(expr)
        if novelty < 0.3:  # At least 30% different
            print(f"    ✗ Rejected: too similar to existing (novelty={novelty:.2f})")
            return False
        
        return True
    
    def add_tool(self, expr, fitness, examples, problem_context):
        """Add tool with behavioral signature"""
        
        sig = behavioral_signature(expr)
        growth = analyze_growth(expr)
        
        tool = {
            'hash': self.structural_hash(expr),
            'structure': expr,
            'examples': examples,
            'signature': sig,
            'growth_type': growth,
            'fitness': fitness,
            'source': problem_context
        }
        self.tools.append(tool)
        
        print(f"\n  📦 Saved tool #{len(self.tools)}")
        print(f"     Pattern: {expr}")
        print(f"     Growth: {growth}")
        print(f"     Signature: {sig[:5]}...")
        print(f"     Examples: {examples[:3]}")
        
        return tool
    
    def get_tool(self, tool_id):
        for tool in self.tools:
            if tool['hash'] == tool_id:
                return tool
        return None
    
    def list_tools(self):
        print(f"\n{'='*70}")
        print(f"TOOL LIBRARY: {len(self.tools)} tools")
        print(f"{'='*70}")
        for i, tool in enumerate(self.tools):
            print(f"\n{i+1}. {tool['structure']}")
            print(f"   Growth: {tool['growth_type']}")
            print(f"   Examples: {tool['examples'][:3]}")

# ============================================
# RANDOM GENERATION
# ============================================

def random_expr(depth=0, max_depth=3, vars_avail=None, tool_lib=None):
    if vars_avail is None:
        vars_avail = ['n']
    
    if depth >= max_depth or random.random() < 0.4:
        choice = random.choice(['const', 'var'])
        if choice == 'const':
            return Const(random.randint(0, 5))
        else:
            return Var(random.choice(vars_avail))
    
    if tool_lib and tool_lib.tools and random.random() < 0.3:
        tool = random.choice(tool_lib.tools)
        arg = random_expr(depth + 1, max_depth, vars_avail, tool_lib)
        return ToolCall(tool['hash'], arg, tool_lib)
    
    choice = random.choice(['binop', 'sum'])
    
    if choice == 'binop':
        op = random.choice(['+', '-', '*', '/', '^'])
        left = random_expr(depth + 1, max_depth, vars_avail, tool_lib)
        right = random_expr(depth + 1, max_depth, vars_avail, tool_lib)
        return BinOp(op, left, right)
    
    elif choice == 'sum':
        var = random.choice(['i', 'j', 'k'])
        start = random_expr(depth + 1, max_depth, vars_avail, tool_lib)
        end = random_expr(depth + 1, max_depth, vars_avail, tool_lib)
        body = random_expr(depth + 1, max_depth, vars_avail + [var], tool_lib)
        return Sum(var, start, end, body)

def mutate(expr, rate=0.3, vars_avail=None, tool_lib=None):
    if vars_avail is None:
        vars_avail = ['n']
    
    if random.random() < rate:
        return random_expr(0, 3, vars_avail, tool_lib)
    
    if isinstance(expr, Const):
        return Const(expr.val + random.uniform(-1, 1))
    elif isinstance(expr, Var):
        return expr
    elif isinstance(expr, BinOp):
        return BinOp(expr.op,
                    mutate(expr.left, rate, vars_avail, tool_lib),
                    mutate(expr.right, rate, vars_avail, tool_lib))
    elif isinstance(expr, Sum):
        return Sum(expr.var,
                  mutate(expr.start, rate, vars_avail, tool_lib),
                  mutate(expr.end, rate, vars_avail, tool_lib),
                  mutate(expr.body, rate, vars_avail + [expr.var], tool_lib))
    elif isinstance(expr, ToolCall):
        return ToolCall(expr.tool_id,
                       mutate(expr.arg, rate, vars_avail, tool_lib),
                       expr.tool_library)
    return expr

# ============================================
# EVOLUTION
# ============================================

def evolve(test_func, tool_lib, problem_name, pop_size=60, gens=60):
    print(f"\n{'='*70}")
    print(f"PROBLEM: {problem_name}")
    print(f"{'='*70}")
    print(f"Available tools: {len(tool_lib.tools)}")
    print()
    
    population = [random_expr(0, 3, ['n'], tool_lib) for _ in range(pop_size)]
    
    best_ever = None
    best_fitness = 0.0
    
    for gen in range(gens):
        scores = []
        for expr in population:
            fitness = test_func(lambda x: expr.eval({'n': x}))
            scores.append((expr, fitness))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        
        if scores[0][1] > best_fitness:
            best_fitness = scores[0][1]
            best_ever = scores[0][0]
        
        if gen % 20 == 0 or scores[0][1] >= 0.99:
            avg = sum(s for _, s in scores) / len(scores)
            print(f"Gen {gen:2d}: Best={scores[0][1]:.3f} Avg={avg:.3f}")
        
        if scores[0][1] >= 0.99:
            print(f"✓ SOLVED at gen {gen}")
            break
        
        survivors = [e for e, _ in scores[:pop_size // 5]]
        
        next_pop = survivors.copy()
        while len(next_pop) < pop_size:
            parent = random.choice(survivors)
            child = mutate(parent, rate=0.2, vars_avail=['n'], tool_lib=tool_lib)
            next_pop.append(child)
        
        population = next_pop
    
    print(f"\nBest: {best_fitness:.3f}")
    print(f"Expression: {best_ever}")
    
    return best_ever, best_fitness

# ============================================
# TESTS
# ============================================

def test_double(func):
    tests = [(0,0), (1,2), (2,4), (3,6), (5,10), (10,20)]
    return sum(1 for n, exp in tests if abs(func(n) - exp) < 0.1) / len(tests)

def test_sum_to_n(func):
    tests = [(1,1), (2,3), (3,6), (4,10), (5,15), (10,55)]
    return sum(1 for n, exp in tests if abs(func(n) - exp) < 0.1) / len(tests)

def test_square(func):
    tests = [(0,0), (1,1), (2,4), (3,9), (4,16), (5,25)]
    return sum(1 for n, exp in tests if abs(func(n) - exp) < 0.1) / len(tests)

def test_integral_x(func):
    tests = [(0,0), (1,0.5), (2,2), (3,4.5), (4,8), (5,12.5)]
    return sum(1 for n, exp in tests if abs(func(n) - exp) < 0.5) / len(tests)

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    print("="*70)
    print("FUNCTIONAL EQUIVALENCE & NOVELTY DETECTION")
    print("="*70)
    print("\nBehavioral signatures detect equivalent patterns:")
    print("  - n*2 and n+n → same signature → deduplicated")
    print("  - n² and n*n → same signature → deduplicated")
    print()
    print("Only saves novel, non-trivial tools.")
    print()
    
    library = ToolLibrary()
    
    # Problem 1: Double
    print("Testing trivial rejection:")
    best, fit = evolve(test_double, library, "f(n) = 2n", gens=40)
    if library.should_save(best, fit):
        examples = [(n, 2*n) for n in range(6)]
        library.add_tool(best, fit, examples, "double")
    
    # Problem 2: Sum
    best, fit = evolve(test_sum_to_n, library, "f(n) = sum(1 to n)", gens=60)
    if library.should_save(best, fit):
        examples = [(n, n*(n+1)//2) for n in range(1, 7)]
        library.add_tool(best, fit, examples, "sum_to_n")
    
    # Problem 3: Square
    best, fit = evolve(test_square, library, "f(n) = n²", gens=60)
    if library.should_save(best, fit):
        examples = [(n, n**2) for n in range(6)]
        library.add_tool(best, fit, examples, "square")
    
    # Show library
    library.list_tools()
    
    # Challenge
    print("\n" + "="*70)
    print("CHALLENGE: ∫₀ⁿ x dx = n²/2")
    print("="*70)
    
    best, fit = evolve(test_integral_x, library, "integral of x from 0 to n", 
                      pop_size=80, gens=100)
    
    print("\n" + "="*70)
    print("RESULT")
    print("="*70)
    print(f"Fitness: {fit:.3f}")
    print(f"Expression: {best}")
    
    if fit >= 0.99:
        print("\n✓ SUCCESS! Discovered through tool composition")
    elif fit >= 0.8:
        print("\n~ Close. Novelty filtering working.")
    else:
        print("\n⊙ Didn't solve. But library has quality tools.")
