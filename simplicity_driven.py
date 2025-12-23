"""
SIMPLICITY-DRIVEN EVOLUTION

Fitness = Accuracy * 0.7 + Simplicity * 0.3

Forces evolution toward simplest form that works.
Makes pattern generalization reliable.
"""

import random
import hashlib
import math
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
        return 5 + self.start.complexity() + self.end.complexity() + self.body.complexity()
    
    def __repr__(self):
        return f"Σ({self.var}={self.start}..{self.end})[{self.body}]"

# ============================================
# SIMPLICITY SCORING
# ============================================

def simplicity_score(expr) -> float:
    """
    How simple is this expression?
    Returns 0.0 (complex) to 1.0 (very simple)
    """
    complexity = expr.complexity()
    
    # Exponential decay - heavily penalize complexity
    # complexity 1-3: ~1.0
    # complexity 5: ~0.8
    # complexity 10: ~0.4
    # complexity 20: ~0.1
    simplicity = math.exp(-complexity / 10.0)
    
    return simplicity

def combined_fitness(accuracy: float, expr) -> float:
    """
    Fitness = Accuracy (70%) + Simplicity (30%)
    
    This drives evolution toward simplest correct solution.
    """
    simplicity = simplicity_score(expr)
    
    # Weight accuracy more, but simplicity matters
    fitness = accuracy * 0.7 + simplicity * 0.3
    
    return fitness

# ============================================
# GENERALIZED TOOLS
# ============================================

@dataclass
class GeneralizedTool:
    name: str
    params: List[str]
    template: Any
    examples: List[Tuple]
    
    def instantiate(self, *args):
        if len(args) != len(self.params):
            return Const(0)
        env = {param: arg for param, arg in zip(self.params, args)}
        return self._substitute(self.template, env)
    
    def _substitute(self, expr, env):
        if isinstance(expr, Var):
            if expr.name in env:
                return env[expr.name]
            return expr
        elif isinstance(expr, BinOp):
            return BinOp(expr.op,
                        self._substitute(expr.left, env),
                        self._substitute(expr.right, env))
        elif isinstance(expr, Sum):
            return Sum(expr.var,
                      self._substitute(expr.start, env),
                      self._substitute(expr.end, env),
                      self._substitute(expr.body, env))
        else:
            return expr
    
    def eval_with_params(self, input_val, param_vals):
        instance = self.instantiate(*param_vals)
        return instance.eval({'n': input_val})
    
    def complexity(self):
        return self.template.complexity()

@dataclass
class ToolCall:
    tool_name: str
    args: List[Any]
    tool_library: Any
    
    def eval(self, env):
        try:
            tool = self.tool_library.get_tool(self.tool_name)
            if tool is None:
                return 0
            
            arg_vals = []
            for arg in self.args:
                if hasattr(arg, 'eval'):
                    arg_vals.append(arg.eval(env))
                else:
                    arg_vals.append(arg)
            
            input_val = env.get('n', 0)
            return tool.eval_with_params(input_val, arg_vals)
        except:
            return 0
    
    def complexity(self):
        base = 2  # Tool call has base cost
        args_complexity = sum(arg.complexity() if hasattr(arg, 'complexity') else 1 
                             for arg in self.args)
        # But tool use is encouraged - don't count tool's internal complexity
        return base + args_complexity
    
    def __repr__(self):
        args_str = ','.join(str(a) for a in self.args)
        return f"{self.tool_name}({args_str})"

# ============================================
# PATTERN GENERALIZATION
# ============================================

def generalize_pattern(expr) -> Optional[GeneralizedTool]:
    """Extract generalized pattern from simple expression"""
    
    # Pattern: n^constant → power(base, exp)
    if isinstance(expr, BinOp) and expr.op == '^':
        if isinstance(expr.left, Var) and isinstance(expr.right, Const):
            template = BinOp('^', Var('n'), Var('exp'))
            examples = [((2,), 4), ((3,), 9), ((4,), 16), ((5,), 25)]
            return GeneralizedTool('power', ['exp'], template, examples)
    
    # Pattern: n*constant → scale(value, factor)
    if isinstance(expr, BinOp) and expr.op == '*':
        if isinstance(expr.left, Var) and isinstance(expr.right, Const):
            template = BinOp('*', Var('n'), Var('factor'))
            examples = [((2,), 0), ((2,), 2), ((2,), 4), ((2,), 6), ((2,), 8)]
            return GeneralizedTool('scale', ['factor'], template, examples)
        if isinstance(expr.left, Const) and isinstance(expr.right, Var):
            template = BinOp('*', Var('factor'), Var('n'))
            examples = [((2,), 0), ((2,), 2), ((2,), 4), ((2,), 6), ((2,), 8)]
            return GeneralizedTool('scale', ['factor'], template, examples)
    
    # Pattern: n/constant → divide(value, divisor)
    if isinstance(expr, BinOp) and expr.op == '/':
        if isinstance(expr.left, Var) and isinstance(expr.right, Const):
            template = BinOp('/', Var('n'), Var('divisor'))
            examples = [((2,), 0), ((2,), 1), ((2,), 2), ((2,), 3), ((2,), 4)]
            return GeneralizedTool('divide', ['divisor'], template, examples)
    
    # Pattern: Σ(i=1..n)[i] → triangular
    if isinstance(expr, Sum):
        if (isinstance(expr.start, Const) and expr.start.val == 1 and
            isinstance(expr.end, Var) and 
            isinstance(expr.body, Var) and expr.body.name == expr.var):
            # This is already maximally simple
            template = Sum('i', Const(1), Var('n'), Var('i'))
            examples = [((), n*(n+1)//2) for n in [1,2,3,4,5,10]]
            return GeneralizedTool('triangular', [], template, examples)
    
    return None

# ============================================
# TOOL LIBRARY
# ============================================

class ToolLibrary:
    def __init__(self):
        self.tools = []
    
    def should_save(self, expr, accuracy) -> bool:
        if accuracy < 0.95:
            return False
        
        # Try generalization
        generalized = generalize_pattern(expr)
        
        if generalized:
            # Check if we already have this
            for tool in self.tools:
                if tool.name == generalized.name:
                    return False
            return True
        else:
            # Must be non-trivial if not generalized
            if expr.complexity() < 4:
                return False
            return True
    
    def add_tool(self, expr, accuracy, examples, problem_context):
        generalized = generalize_pattern(expr)
        
        if generalized:
            self.tools.append(generalized)
            print(f"\n  🔧 Generalized: {generalized.name}({','.join(generalized.params)})")
            print(f"     Template: {generalized.template}")
            print(f"     Complexity: {generalized.complexity()}")
            return generalized
        else:
            tool = GeneralizedTool(
                name=f'pattern_{len(self.tools)}',
                params=[],
                template=expr,
                examples=examples
            )
            self.tools.append(tool)
            print(f"\n  📦 Saved: {tool.name}")
            print(f"     Pattern: {expr}")
            print(f"     Complexity: {expr.complexity()}")
            return tool
    
    def get_tool(self, name):
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None
    
    def list_tools(self):
        print(f"\n{'='*70}")
        print(f"TOOL LIBRARY: {len(self.tools)} tools")
        print(f"{'='*70}")
        for i, tool in enumerate(self.tools):
            print(f"\n{i+1}. {tool.name}")
            if tool.params:
                print(f"   Parameters: {tool.params}")
            print(f"   Template: {tool.template}")
            print(f"   Complexity: {tool.complexity()}")

# ============================================
# RANDOM GENERATION
# ============================================

def random_expr(depth=0, max_depth=2, vars_avail=None, tool_lib=None):
    """Generate simpler expressions by default (max_depth=2)"""
    if vars_avail is None:
        vars_avail = ['n']
    
    if depth >= max_depth or random.random() < 0.5:
        choice = random.choice(['const', 'var'])
        if choice == 'const':
            return Const(random.randint(0, 5))
        else:
            return Var(random.choice(vars_avail))
    
    # Use tool?
    if tool_lib and tool_lib.tools and random.random() < 0.4:
        tool = random.choice(tool_lib.tools)
        args = [random_expr(depth + 1, max_depth, vars_avail, tool_lib) 
               for _ in tool.params] if tool.params else []
        return ToolCall(tool.name, args, tool_lib)
    
    choice = random.choice(['binop', 'sum'])
    
    if choice == 'binop':
        op = random.choice(['+', '-', '*', '/', '^'])
        left = random_expr(depth + 1, max_depth, vars_avail, tool_lib)
        right = random_expr(depth + 1, max_depth, vars_avail, tool_lib)
        return BinOp(op, left, right)
    
    elif choice == 'sum':
        var = random.choice(['i', 'j'])
        start = random_expr(depth + 1, max_depth, vars_avail, tool_lib)
        end = random_expr(depth + 1, max_depth, vars_avail, tool_lib)
        body = random_expr(depth + 1, max_depth, vars_avail + [var], tool_lib)
        return Sum(var, start, end, body)

def mutate(expr, rate=0.25, vars_avail=None, tool_lib=None):
    if vars_avail is None:
        vars_avail = ['n']
    
    if random.random() < rate:
        return random_expr(0, 2, vars_avail, tool_lib)
    
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
        return ToolCall(expr.tool_name,
                       [mutate(arg, rate, vars_avail, tool_lib) for arg in expr.args],
                       expr.tool_library)
    return expr

# ============================================
# EVOLUTION WITH SIMPLICITY
# ============================================

def evolve(test_func, tool_lib, problem_name, pop_size=80, gens=80):
    print(f"\n{'='*70}")
    print(f"PROBLEM: {problem_name}")
    print(f"{'='*70}")
    print(f"Tools: {len(tool_lib.tools)}")
    print()
    
    population = [random_expr(0, 2, ['n'], tool_lib) for _ in range(pop_size)]
    
    best_ever = None
    best_fitness = 0.0
    best_accuracy = 0.0
    
    for gen in range(gens):
        scores = []
        for expr in population:
            accuracy = test_func(lambda x: expr.eval({'n': x}))
            fitness = combined_fitness(accuracy, expr)
            scores.append((expr, fitness, accuracy))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        
        if scores[0][2] > best_accuracy or (scores[0][2] == best_accuracy and scores[0][1] > best_fitness):
            best_fitness = scores[0][1]
            best_accuracy = scores[0][2]
            best_ever = scores[0][0]
        
        if gen % 20 == 0 or scores[0][2] >= 0.99:
            avg_fit = sum(s[1] for s in scores) / len(scores)
            avg_acc = sum(s[2] for s in scores) / len(scores)
            print(f"Gen {gen:2d}: Acc={scores[0][2]:.3f} Fit={scores[0][1]:.3f} "
                  f"(avgAcc={avg_acc:.2f} avgFit={avg_fit:.2f}) "
                  f"Complex={scores[0][0].complexity()}")
        
        if scores[0][2] >= 0.99:
            print(f"✓ SOLVED")
            break
        
        # Keep top performers
        survivors = [e for e, _, _ in scores[:pop_size // 4]]
        
        next_pop = survivors.copy()
        while len(next_pop) < pop_size:
            parent = random.choice(survivors)
            child = mutate(parent, rate=0.2, vars_avail=['n'], tool_lib=tool_lib)
            next_pop.append(child)
        
        population = next_pop
    
    print(f"\nBest: Acc={best_accuracy:.3f} Fit={best_fitness:.3f} Complex={best_ever.complexity()}")
    print(f"Expression: {best_ever}")
    
    return best_ever, best_accuracy

# ============================================
# TESTS
# ============================================

def test_square(func):
    tests = [(0,0), (1,1), (2,4), (3,9), (4,16), (5,25)]
    return sum(1 for n, exp in tests if abs(func(n) - exp) < 0.1) / len(tests)

def test_sum_to_n(func):
    tests = [(1,1), (2,3), (3,6), (4,10), (5,15), (10,55)]
    return sum(1 for n, exp in tests if abs(func(n) - exp) < 0.1) / len(tests)

def test_cube(func):
    tests = [(0,0), (1,1), (2,8), (3,27), (4,64), (5,125)]
    return sum(1 for n, exp in tests if abs(func(n) - exp) < 0.1) / len(tests)

def test_integral_x(func):
    tests = [(0,0), (1,0.5), (2,2), (3,4.5), (4,8), (5,12.5)]
    return sum(1 for n, exp in tests if abs(func(n) - exp) < 0.5) / len(tests)

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    print("="*70)
    print("SIMPLICITY-DRIVEN EVOLUTION")
    print("="*70)
    print("\nFitness = Accuracy (70%) + Simplicity (30%)")
    print("Forces discovery of simplest working solution")
    print("Makes pattern generalization reliable")
    print()
    
    library = ToolLibrary()
    
    # Problem 1: Square
    best, acc = evolve(test_square, library, "f(n) = n²")
    if library.should_save(best, acc):
        examples = [(n, n**2) for n in range(6)]
        library.add_tool(best, acc, examples, "square")
    
    # Problem 2: Sum
    best, acc = evolve(test_sum_to_n, library, "f(n) = sum(1 to n)")
    if library.should_save(best, acc):
        examples = [(n, n*(n+1)//2) for n in range(1, 7)]
        library.add_tool(best, acc, examples, "sum")
    
    # Problem 3: Cube (should reuse power)
    best, acc = evolve(test_cube, library, "f(n) = n³")
    if library.should_save(best, acc):
        examples = [(n, n**3) for n in range(6)]
        library.add_tool(best, acc, examples, "cube")
    
    library.list_tools()
    
    # Challenge
    print("\n" + "="*70)
    print("CHALLENGE: ∫₀ⁿ x dx = n²/2")
    print("="*70)
    
    best, acc = evolve(test_integral_x, library, "integral", pop_size=100, gens=100)
    
    print("\n" + "="*70)
    print("RESULT")
    print("="*70)
    print(f"Accuracy: {acc:.3f}")
    print(f"Complexity: {best.complexity()}")
    print(f"Expression: {best}")
    
    if acc >= 0.99:
        print("\n✓ SUCCESS! Simplicity pressure worked!")
    else:
        print(f"\n~ Partial. Simpler expressions, better generalization.")
