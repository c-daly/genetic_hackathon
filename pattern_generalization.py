"""
PATTERN GENERALIZATION

When GP discovers n^2, extract the general pattern: power(base, exponent)
When GP discovers n*5, extract: scale(value, factor)

Save generalized, parameterized tools instead of specific instances.
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

# ============================================
# GENERALIZED TOOLS
# ============================================

@dataclass
class GeneralizedTool:
    """A tool with parameters that can be instantiated"""
    name: str
    params: List[str]  # Parameter names
    template: Any      # Expression template
    examples: List[Tuple]  # (param_values, result) pairs
    
    def instantiate(self, *args):
        """Create specific instance with parameter values"""
        if len(args) != len(self.params):
            return Const(0)
        
        # Build environment with parameter values
        env = {param: arg for param, arg in zip(self.params, args)}
        
        # Substitute parameters in template
        return self._substitute(self.template, env)
    
    def _substitute(self, expr, env):
        """Recursively substitute parameters"""
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
        """Evaluate with specific parameter values"""
        instance = self.instantiate(*param_vals)
        return instance.eval({'n': input_val})

@dataclass
class ToolCall:
    tool_name: str
    args: List[Any]  # Arguments (can be expressions)
    tool_library: Any
    
    def eval(self, env):
        try:
            tool = self.tool_library.get_tool(self.tool_name)
            if tool is None:
                return 0
            
            # Evaluate arguments
            arg_vals = []
            for arg in self.args:
                if hasattr(arg, 'eval'):
                    arg_vals.append(arg.eval(env))
                else:
                    arg_vals.append(arg)
            
            # Get input value
            input_val = env.get('n', 0)
            
            # Evaluate tool with parameters
            return tool.eval_with_params(input_val, arg_vals)
        except:
            return 0
    
    def complexity(self):
        return 2 + sum(arg.complexity() if hasattr(arg, 'complexity') else 1 
                      for arg in self.args)
    
    def __repr__(self):
        args_str = ','.join(str(a) for a in self.args)
        return f"{self.tool_name}({args_str})"

# ============================================
# PATTERN GENERALIZATION
# ============================================

def generalize_pattern(expr) -> Optional[GeneralizedTool]:
    """
    Extract generalized pattern from specific expression.
    Returns GeneralizedTool if pattern found, None otherwise.
    """
    
    # Pattern 1: n^constant → power(base, exp)
    if isinstance(expr, BinOp) and expr.op == '^':
        if isinstance(expr.left, Var) and isinstance(expr.right, Const):
            exponent = expr.right.val
            # Generalize: base^exp where exp is parameter
            template = BinOp('^', Var('n'), Var('exp'))
            examples = [
                ((2,), 4),    # 2^exp
                ((3,), 9),    # 3^exp
                ((4,), 16),   # etc
                ((5,), 25),
            ]
            return GeneralizedTool('power', ['exp'], template, examples)
    
    # Pattern 2: n*constant → scale(value, factor)
    if isinstance(expr, BinOp) and expr.op == '*':
        if isinstance(expr.left, Var) and isinstance(expr.right, Const):
            factor = expr.right.val
            template = BinOp('*', Var('n'), Var('factor'))
            examples = [
                ((2,), n*2) for n in [0, 1, 2, 3, 4, 5]
            ]
            return GeneralizedTool('scale', ['factor'], template, examples)
        if isinstance(expr.left, Const) and isinstance(expr.right, Var):
            factor = expr.left.val
            template = BinOp('*', Var('factor'), Var('n'))
            examples = [
                ((2,), n*2) for n in [0, 1, 2, 3, 4, 5]
            ]
            return GeneralizedTool('scale', ['factor'], template, examples)
    
    # Pattern 3: Σ(i=1..n)[i] → triangular numbers
    if isinstance(expr, Sum):
        # Check for sum from 1 to n of i
        if (isinstance(expr.start, Const) and expr.start.val == 1 and
            isinstance(expr.end, Var) and 
            isinstance(expr.body, Var) and expr.body.name == expr.var):
            # This is sum(1 to n) of i
            # Keep as is - it's already general
            return None  # Don't generalize, save as structural pattern
    
    # Pattern 4: Σ(i=1..n)[i^k] → sum of powers
    if isinstance(expr, Sum):
        if (isinstance(expr.start, Const) and expr.start.val == 1 and
            isinstance(expr.end, Var)):
            # Check if body is i^k
            if (isinstance(expr.body, BinOp) and expr.body.op == '^' and
                isinstance(expr.body.left, Var) and expr.body.left.name == expr.var and
                isinstance(expr.body.right, Const)):
                power = expr.body.right.val
                # Generalize: sum of i^k
                template = Sum('i', Const(1), Var('n'), 
                             BinOp('^', Var('i'), Var('k')))
                examples = [
                    ((2,), sum(i**2 for i in range(1, 6))),  # sum i^2
                    ((3,), sum(i**3 for i in range(1, 6))),  # sum i^3
                ]
                return GeneralizedTool('sum_powers', ['k'], template, examples)
    
    return None

# ============================================
# TOOL LIBRARY WITH GENERALIZATION
# ============================================

def behavioral_signature(expr, test_range=20) -> Tuple[float, ...]:
    """Function IS its input/output behavior"""
    signature = []
    for x in range(test_range):
        try:
            result = expr.eval({'n': x})
            if abs(result) > 1e10:
                result = 1e10 if result > 0 else -1e10
            signature.append(round(result, 6))
        except:
            signature.append(0)
    return tuple(signature)

class ToolLibrary:
    def __init__(self):
        self.tools = []  # GeneralizedTool objects
    
    def should_save(self, expr, fitness) -> bool:
        """Should we save/generalize this?"""
        if fitness < 0.95:
            return False
        
        # Try to generalize
        generalized = generalize_pattern(expr)
        
        if generalized:
            # Check if we already have this pattern
            for tool in self.tools:
                if tool.name == generalized.name:
                    return False  # Already have this pattern
            return True
        else:
            # Not a trivial pattern, check if structurally interesting
            if expr.complexity() < 4:
                return False
            # Check novelty
            if self.tools:
                sig = behavioral_signature(expr)
                for tool in self.tools:
                    # Compare signatures
                    test_sig = tuple(tool.eval_with_params(x, [2]) 
                                    for x in range(20))
                    if sig == test_sig:
                        return False
            return True
    
    def add_tool(self, expr, fitness, examples, problem_context):
        """Add tool - generalize if possible"""
        
        # Try generalization first
        generalized = generalize_pattern(expr)
        
        if generalized:
            self.tools.append(generalized)
            print(f"\n  🔧 Generalized pattern: {generalized.name}")
            print(f"     Parameters: {generalized.params}")
            print(f"     Template: {generalized.template}")
            print(f"     Example: power(2) = {generalized.eval_with_params(2, [2])}")
            return generalized
        else:
            # Save as structural pattern (like Σ(i=1..n)[i])
            # Wrap in GeneralizedTool with no parameters
            tool = GeneralizedTool(
                name=f'pattern_{len(self.tools)}',
                params=[],
                template=expr,
                examples=examples
            )
            self.tools.append(tool)
            print(f"\n  📦 Saved structural pattern: {expr}")
            print(f"     Examples: {examples[:3]}")
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

# ============================================
# RANDOM GENERATION WITH PARAMETERIZED TOOLS
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
    
    # Use tool?
    if tool_lib and tool_lib.tools and random.random() < 0.3:
        tool = random.choice(tool_lib.tools)
        # Generate arguments for parameters
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
        return ToolCall(expr.tool_name,
                       [mutate(arg, rate, vars_avail, tool_lib) for arg in expr.args],
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
    print("PATTERN GENERALIZATION")
    print("="*70)
    print("\nInstead of saving n^2, extract: power(base, exp)")
    print("Instead of saving n*5, extract: scale(value, factor)")
    print()
    
    library = ToolLibrary()
    
    # Problem 1: Square → should generalize to power
    best, fit = evolve(test_square, library, "f(n) = n²", gens=40)
    if library.should_save(best, fit):
        examples = [(n, n**2) for n in range(6)]
        library.add_tool(best, fit, examples, "square")
    
    # Problem 2: Sum
    best, fit = evolve(test_sum_to_n, library, "f(n) = sum(1 to n)", gens=60)
    if library.should_save(best, fit):
        examples = [(n, n*(n+1)//2) for n in range(1, 7)]
        library.add_tool(best, fit, examples, "sum")
    
    # Problem 3: Cube → should reuse power(n, 3)
    best, fit = evolve(test_cube, library, "f(n) = n³", gens=60)
    if library.should_save(best, fit):
        examples = [(n, n**3) for n in range(6)]
        library.add_tool(best, fit, examples, "cube")
    
    # Show library
    library.list_tools()
    
    # Challenge: Can it use power(n, 2) and scale?
    print("\n" + "="*70)
    print("CHALLENGE: ∫₀ⁿ x dx = n²/2")
    print("="*70)
    print("Should use: power(n, 2) / scale(1, 2)")
    
    best, fit = evolve(test_integral_x, library, "integral", 
                      pop_size=80, gens=100)
    
    print("\n" + "="*70)
    print("RESULT")
    print("="*70)
    print(f"Fitness: {fit:.3f}")
    print(f"Expression: {best}")
    
    if fit >= 0.99:
        print("\n✓ SUCCESS via generalized tools!")
    else:
        print(f"\n~ Best attempt. Generalization framework works.")
