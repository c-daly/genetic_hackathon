"""
COMPOSITIONAL MATHEMATICAL GP WITH TOOL ACCUMULATION

Shows the thought process:
- What patterns is it trying?
- When does a tool get discovered?
- How does it use previous tools?
- Does factorial actually build on summation?
"""

import random
from dataclasses import dataclass
from typing import Any, Dict, Callable

# ============================================
# TOOL LIBRARY - ACCUMULATES DISCOVERIES
# ============================================

class ToolLibrary:
    """Stores discovered patterns for reuse"""
    
    def __init__(self):
        self.tools = {}  # name -> (expression, description)
    
    def add_tool(self, name: str, expr: Any, description: str):
        """Save a discovered tool"""
        self.tools[name] = (expr, description)
        print(f"\n  📦 TOOL DISCOVERED: {name}")
        print(f"     Description: {description}")
        print(f"     Expression: {expr}")
        print()
    
    def has_tool(self, name: str) -> bool:
        return name in self.tools
    
    def get_tool(self, name: str):
        return self.tools[name][0] if name in self.tools else None
    
    def list_tools(self):
        return list(self.tools.keys())

# Global tool library
TOOLS = ToolLibrary()

# ============================================
# EXPRESSION TYPES
# ============================================

@dataclass
class Const:
    val: float
    def eval(self, env): return self.val
    def __repr__(self): return str(int(self.val))

@dataclass
class Var:
    name: str
    def eval(self, env): return env.get(self.name, 0)
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
            if self.op == '/': return l / r if r != 0 else 0
        except:
            return 0
    
    def __repr__(self):
        return f"({self.left}{self.op}{self.right})"

@dataclass
class Sum:
    """Σ(var=start to end) body"""
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
    
    def __repr__(self):
        return f"Σ({self.var}={self.start}..{self.end})[{self.body}]"

@dataclass
class Product:
    """∏(var=start to end) body"""
    var: str
    start: Any
    end: Any
    body: Any
    
    def eval(self, env):
        try:
            s = int(self.start.eval(env))
            e = int(self.end.eval(env))
            result = 1
            for i in range(s, min(e + 1, s + 100)):
                new_env = env.copy()
                new_env[self.var] = i
                result *= self.body.eval(new_env)
            return result
        except:
            return 1
    
    def __repr__(self):
        return f"∏({self.var}={self.start}..{self.end})[{self.body}]"

@dataclass
class ToolCall:
    """Call a previously discovered tool"""
    tool_name: str
    arg: Any
    
    def eval(self, env):
        tool_expr = TOOLS.get_tool(self.tool_name)
        if tool_expr is None:
            return 0
        # Evaluate tool with argument
        arg_val = self.arg.eval(env) if hasattr(self.arg, 'eval') else self.arg
        tool_env = {'n': arg_val}
        return tool_expr.eval(tool_env)
    
    def __repr__(self):
        return f"{self.tool_name}({self.arg})"

# ============================================
# RANDOM GENERATION WITH TOOL REUSE
# ============================================

def random_expr(depth=0, max_depth=3, vars_available=None):
    """Generate random expression - can use discovered tools"""
    if vars_available is None:
        vars_available = ['n']
    
    # Terminal
    if depth >= max_depth or random.random() < 0.4:
        choices = ['const', 'var']
        # Can also use a tool if any exist
        if TOOLS.list_tools() and random.random() < 0.3:
            choices.append('tool')
        
        choice = random.choice(choices)
        
        if choice == 'const':
            return Const(random.randint(0, 5))
        elif choice == 'var':
            return Var(random.choice(vars_available))
        elif choice == 'tool':
            tool_name = random.choice(TOOLS.list_tools())
            arg = random_expr(depth + 1, max_depth, vars_available)
            return ToolCall(tool_name, arg)
    
    # Compound
    choice = random.choice(['binop', 'sum', 'product'])
    
    if choice == 'binop':
        op = random.choice(['+', '-', '*', '/'])
        left = random_expr(depth + 1, max_depth, vars_available)
        right = random_expr(depth + 1, max_depth, vars_available)
        return BinOp(op, left, right)
    
    elif choice == 'sum':
        var = random.choice(['i', 'j', 'k'])
        start = random_expr(depth + 1, max_depth, vars_available)
        end = random_expr(depth + 1, max_depth, vars_available)
        body = random_expr(depth + 1, max_depth, vars_available + [var])
        return Sum(var, start, end, body)
    
    elif choice == 'product':
        var = random.choice(['i', 'j', 'k'])
        start = random_expr(depth + 1, max_depth, vars_available)
        end = random_expr(depth + 1, max_depth, vars_available)
        body = random_expr(depth + 1, max_depth, vars_available + [var])
        return Product(var, start, end, body)

# ============================================
# MUTATION
# ============================================

def mutate(expr, rate=0.3, vars_available=None):
    """Mutate expression"""
    if vars_available is None:
        vars_available = ['n']
    
    if random.random() < rate:
        return random_expr(0, 3, vars_available)
    
    if isinstance(expr, Const):
        return Const(expr.val + random.randint(-1, 1))
    elif isinstance(expr, Var):
        return expr
    elif isinstance(expr, BinOp):
        return BinOp(expr.op,
                    mutate(expr.left, rate, vars_available),
                    mutate(expr.right, rate, vars_available))
    elif isinstance(expr, Sum):
        return Sum(expr.var,
                  mutate(expr.start, rate, vars_available),
                  mutate(expr.end, rate, vars_available),
                  mutate(expr.body, rate, vars_available + [expr.var]))
    elif isinstance(expr, Product):
        return Product(expr.var,
                      mutate(expr.start, rate, vars_available),
                      mutate(expr.end, rate, vars_available),
                      mutate(expr.body, rate, vars_available + [expr.var]))
    elif isinstance(expr, ToolCall):
        return ToolCall(expr.tool_name,
                       mutate(expr.arg, rate, vars_available))
    return expr

# ============================================
# EVOLUTION WITH VERBOSE OUTPUT
# ============================================

def evolve_with_tools(test_func, pop_size=50, gens=100, problem_name="", 
                     tool_name=None, tool_desc=""):
    """Evolve with tool accumulation and show thought process"""
    
    print("\n" + "="*70)
    print(f"PROBLEM: {problem_name}")
    print("="*70)
    
    if TOOLS.list_tools():
        print(f"\n💡 Available tools: {', '.join(TOOLS.list_tools())}")
    else:
        print("\n💡 No tools yet - starting from scratch")
    
    print(f"\n🔬 Starting evolution...")
    print(f"   Population: {pop_size}, Generations: {gens}")
    print()
    
    population = [random_expr(0, 3, ['n']) for _ in range(pop_size)]
    
    best_ever = None
    best_fitness = 0.0
    
    for gen in range(gens):
        scores = []
        for expr in population:
            fitness = test_func(lambda n: expr.eval({'n': n}))
            scores.append((expr, fitness))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        
        if scores[0][1] > best_fitness:
            best_fitness = scores[0][1]
            best_ever = scores[0][0]
            
            # Show improvement
            if best_fitness > 0.5:
                print(f"Gen {gen:3d}: 🎯 Improvement! Fitness={best_fitness:.3f}")
                if len(str(best_ever)) < 100:
                    print(f"         Trying: {best_ever}")
        
        if gen % 20 == 0 and gen > 0:
            avg = sum(s for _, s in scores) / len(scores)
            print(f"Gen {gen:3d}: Best={scores[0][1]:.3f} Avg={avg:.3f}")
        
        if scores[0][1] >= 0.99:
            print(f"\n✅ SOLVED at generation {gen}!")
            print(f"   Final expression: {scores[0][0]}")
            
            # Add to tool library if name provided
            if tool_name:
                TOOLS.add_tool(tool_name, scores[0][0], tool_desc)
            
            return scores[0][0], scores[0][1]
        
        survivors = [e for e, _ in scores[:pop_size // 5]]
        
        next_pop = survivors.copy()
        while len(next_pop) < pop_size:
            parent = random.choice(survivors)
            child = mutate(parent, rate=0.2, vars_available=['n'])
            next_pop.append(child)
        
        population = next_pop
    
    print(f"\n⚠️  Did not fully solve. Best: {best_fitness:.3f}")
    print(f"   Best expression: {best_ever}")
    
    # Still add partial solutions if decent
    if best_fitness >= 0.8 and tool_name:
        print(f"\n   Adding as partial tool (80%+ correct)")
        TOOLS.add_tool(tool_name, best_ever, tool_desc + " (partial)")
    
    return best_ever, best_fitness

# ============================================
# TEST PROBLEMS
# ============================================

def test_sum_1_to_n(func):
    """sum(1 to n) = n(n+1)/2"""
    tests = [(1, 1), (2, 3), (3, 6), (4, 10), (5, 15), (10, 55)]
    correct = sum(1 for n, exp in tests if abs(func(n) - exp) < 0.1)
    return correct / len(tests)

def test_factorial(func):
    """n!"""
    tests = [(0, 1), (1, 1), (2, 2), (3, 6), (4, 24), (5, 120)]
    correct = sum(1 for n, exp in tests if abs(func(n) - exp) < 0.1)
    return correct / len(tests)

def test_sum_of_squares(func):
    """1² + 2² + ... + n²"""
    tests = [(1, 1), (2, 5), (3, 14), (4, 30), (5, 55)]
    correct = sum(1 for n, exp in tests if abs(func(n) - exp) < 0.1)
    return correct / len(tests)

def test_double(func):
    """2n"""
    tests = [(0, 0), (1, 2), (2, 4), (3, 6), (5, 10)]
    correct = sum(1 for n, exp in tests if abs(func(n) - exp) < 0.1)
    return correct / len(tests)

# ============================================
# RUN SEQUENTIAL DISCOVERY
# ============================================

if __name__ == '__main__':
    print("="*70)
    print("COMPOSITIONAL MATHEMATICAL GP")
    print("Tool Accumulation & Discovery Process")
    print("="*70)
    print("\nWatch how tools build on previous discoveries...")
    print()
    
    # Problem 1: Simple doubling (warm-up)
    best1, fit1 = evolve_with_tools(
        test_double,
        pop_size=50, gens=50,
        problem_name="f(n) = 2n (double)",
        tool_name="double",
        tool_desc="Doubles its input"
    )
    
    # Problem 2: Summation
    best2, fit2 = evolve_with_tools(
        test_sum_1_to_n,
        pop_size=80, gens=150,
        problem_name="f(n) = 1+2+...+n (sum)",
        tool_name="sum",
        tool_desc="Sum from 1 to n"
    )
    
    # Problem 3: Factorial (can use sum concept!)
    best3, fit3 = evolve_with_tools(
        test_factorial,
        pop_size=80, gens=150,
        problem_name="f(n) = n! (factorial)",
        tool_name="factorial",
        tool_desc="Factorial of n"
    )
    
    # Problem 4: Sum of squares (can use sum tool!)
    best4, fit4 = evolve_with_tools(
        test_sum_of_squares,
        pop_size=80, gens=150,
        problem_name="f(n) = 1²+2²+...+n² (sum of squares)",
        tool_name="sum_squares",
        tool_desc="Sum of squares from 1 to n"
    )
    
    # Summary
    print("\n" + "="*70)
    print("DISCOVERY SUMMARY")
    print("="*70)
    print()
    print("Tools discovered:")
    for i, tool_name in enumerate(TOOLS.list_tools(), 1):
        expr, desc = TOOLS.tools[tool_name]
        print(f"{i}. {tool_name}: {desc}")
        print(f"   Expression: {expr}")
    
    print()
    print("Fitness results:")
    print(f"  double: {fit1:.3f}")
    print(f"  sum: {fit2:.3f}")
    print(f"  factorial: {fit3:.3f}")
    print(f"  sum_squares: {fit4:.3f}")
    
    print()
    if fit3 >= 0.8 and 'sum' in str(best3).lower():
        print("✅ Factorial used summation concept!")
    elif fit3 >= 0.8:
        print("✅ Factorial discovered, but different approach")
    
    if fit4 >= 0.8 and 'sum' in str(best4):
        print("✅ Sum of squares reused sum tool!")
    
    print()
    print("This demonstrates compositional discovery:")
    print("  → Tools accumulate across problems")
    print("  → Later problems can build on earlier discoveries")
    print("  → Knowledge compounds")
