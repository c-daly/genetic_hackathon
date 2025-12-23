"""
GENETIC PROGRAMMING WITH PROPOSITIONAL LOGIC

Primitives: ∧, ∨, ¬, →, ↔, T, F
Behavioral signatures: Truth tables
Discovery: Logical equivalences, simplifications, tautologies

Can evolution discover De Morgan's laws? Proof strategies?
"""

import random
import hashlib
from dataclasses import dataclass
from typing import Any, List, Tuple
from itertools import product

# ============================================
# PROPOSITIONAL LOGIC EXPRESSIONS
# ============================================

@dataclass
class Const:
    """Boolean constant"""
    val: bool
    def eval(self, env): return self.val
    def complexity(self): return 1
    def __repr__(self): return "T" if self.val else "F"

@dataclass
class Var:
    """Boolean variable"""
    name: str
    def eval(self, env): return env.get(self.name, False)
    def complexity(self): return 1
    def __repr__(self): return self.name

@dataclass
class Not:
    """¬P"""
    expr: Any
    def eval(self, env):
        return not self.expr.eval(env)
    def complexity(self): return 1 + self.expr.complexity()
    def __repr__(self): return f"¬{self.expr}"

@dataclass
class And:
    """P ∧ Q"""
    left: Any
    right: Any
    def eval(self, env):
        return self.left.eval(env) and self.right.eval(env)
    def complexity(self): return 1 + self.left.complexity() + self.right.complexity()
    def __repr__(self): return f"({self.left} ∧ {self.right})"

@dataclass
class Or:
    """P ∨ Q"""
    left: Any
    right: Any
    def eval(self, env):
        return self.left.eval(env) or self.right.eval(env)
    def complexity(self): return 1 + self.left.complexity() + self.right.complexity()
    def __repr__(self): return f"({self.left} ∨ {self.right})"

@dataclass
class Implies:
    """P → Q"""
    left: Any
    right: Any
    def eval(self, env):
        # P → Q ≡ ¬P ∨ Q
        return (not self.left.eval(env)) or self.right.eval(env)
    def complexity(self): return 1 + self.left.complexity() + self.right.complexity()
    def __repr__(self): return f"({self.left} → {self.right})"

@dataclass
class Iff:
    """P ↔ Q"""
    left: Any
    right: Any
    def eval(self, env):
        # P ↔ Q ≡ (P → Q) ∧ (Q → P)
        l = self.left.eval(env)
        r = self.right.eval(env)
        return l == r
    def complexity(self): return 1 + self.left.complexity() + self.right.complexity()
    def __repr__(self): return f"({self.left} ↔ {self.right})"

# ============================================
# TRUTH TABLE (BEHAVIORAL SIGNATURE)
# ============================================

def get_variables(expr) -> set:
    """Extract all variable names from expression"""
    if isinstance(expr, Var):
        return {expr.name}
    elif isinstance(expr, Not):
        return get_variables(expr.expr)
    elif isinstance(expr, (And, Or, Implies, Iff)):
        return get_variables(expr.left) | get_variables(expr.right)
    else:
        return set()

def truth_table(expr) -> Tuple:
    """
    Generate truth table for expression.
    This IS the behavioral signature for logic.
    """
    variables = sorted(get_variables(expr))
    
    if not variables:
        # No variables - just constant
        return (expr.eval({}),)
    
    results = []
    # Generate all combinations of variable assignments
    for assignment in product([False, True], repeat=len(variables)):
        env = dict(zip(variables, assignment))
        result = expr.eval(env)
        results.append(result)
    
    return tuple(results)

def tables_equivalent(table1: Tuple, table2: Tuple) -> bool:
    """Are two truth tables identical?"""
    return table1 == table2

# ============================================
# LOGICAL PROPERTIES
# ============================================

def is_tautology(expr) -> bool:
    """Is this always true?"""
    table = truth_table(expr)
    return all(table)

def is_contradiction(expr) -> bool:
    """Is this always false?"""
    table = truth_table(expr)
    return not any(table)

def is_contingent(expr) -> bool:
    """Sometimes true, sometimes false?"""
    return not is_tautology(expr) and not is_contradiction(expr)

# ============================================
# TRANSFORMATION DISCOVERY
# ============================================

@dataclass
class LogicalTransformation:
    """A discovered logical equivalence"""
    id: str
    from_expr: Any
    to_expr: Any
    truth_table: Tuple
    complexity_reduction: int
    category: str  # 'simplification', 'equivalence', etc
    
    def __repr__(self):
        return f"{self.from_expr} ≡ {self.to_expr}"

class LogicTransformationLibrary:
    def __init__(self):
        self.transformations = []
    
    def discover_equivalence(self, expr1, expr2) -> LogicalTransformation:
        """Check if two expressions are logically equivalent"""
        table1 = truth_table(expr1)
        table2 = truth_table(expr2)
        
        if not tables_equivalent(table1, table2):
            return None
        
        c1 = expr1.complexity()
        c2 = expr2.complexity()
        
        # Only save if meaningful simplification
        if abs(c1 - c2) < 1:
            return None
        
        # Prefer simpler
        if c1 > c2:
            from_expr, to_expr = expr1, expr2
            reduction = c1 - c2
        else:
            from_expr, to_expr = expr2, expr1
            reduction = c2 - c1
        
        trans_id = hashlib.md5(f"{from_expr}{to_expr}".encode()).hexdigest()[:8]
        
        # Categorize
        if is_tautology(from_expr):
            category = 'tautology'
        elif is_contradiction(from_expr):
            category = 'contradiction'
        else:
            category = 'simplification'
        
        return LogicalTransformation(
            id=trans_id,
            from_expr=from_expr,
            to_expr=to_expr,
            truth_table=table1,
            complexity_reduction=reduction,
            category=category
        )
    
    def add_transformation(self, trans: LogicalTransformation) -> bool:
        """Add if novel"""
        # Check for duplicates
        for t in self.transformations:
            if (t.truth_table == trans.truth_table and 
                t.to_expr.complexity() == trans.to_expr.complexity()):
                return False
        
        self.transformations.append(trans)
        print(f"\n  ⚡ Discovered {trans.category}:")
        print(f"     {trans.from_expr}")
        print(f"     ≡ {trans.to_expr}")
        print(f"     Reduction: {trans.complexity_reduction}")
        return True
    
    def list_transformations(self):
        if not self.transformations:
            print("\n  (No equivalences discovered yet)")
            return
        
        print(f"\n{'='*70}")
        print(f"LOGICAL EQUIVALENCES: {len(self.transformations)}")
        print(f"{'='*70}")
        
        by_category = {}
        for t in self.transformations:
            if t.category not in by_category:
                by_category[t.category] = []
            by_category[t.category].append(t)
        
        for category, trans_list in by_category.items():
            print(f"\n{category.upper()}:")
            for t in trans_list:
                print(f"  {t.from_expr} ≡ {t.to_expr}")

# ============================================
# RANDOM GENERATION
# ============================================

def random_logic_expr(depth=0, max_depth=3, vars_avail=None):
    """Generate random propositional logic expression"""
    if vars_avail is None:
        vars_avail = ['P', 'Q', 'R']
    
    if depth >= max_depth or random.random() < 0.4:
        choice = random.choice(['const', 'var'])
        if choice == 'const':
            return Const(random.choice([True, False]))
        else:
            return Var(random.choice(vars_avail))
    
    op = random.choice(['not', 'and', 'or', 'implies', 'iff'])
    
    if op == 'not':
        return Not(random_logic_expr(depth + 1, max_depth, vars_avail))
    elif op == 'and':
        return And(random_logic_expr(depth + 1, max_depth, vars_avail),
                   random_logic_expr(depth + 1, max_depth, vars_avail))
    elif op == 'or':
        return Or(random_logic_expr(depth + 1, max_depth, vars_avail),
                  random_logic_expr(depth + 1, max_depth, vars_avail))
    elif op == 'implies':
        return Implies(random_logic_expr(depth + 1, max_depth, vars_avail),
                       random_logic_expr(depth + 1, max_depth, vars_avail))
    elif op == 'iff':
        return Iff(random_logic_expr(depth + 1, max_depth, vars_avail),
                   random_logic_expr(depth + 1, max_depth, vars_avail))

def mutate_logic(expr, rate=0.3):
    """Mutate logic expression"""
    if random.random() < rate:
        return random_logic_expr(0, 3, ['P', 'Q', 'R'])
    
    if isinstance(expr, Const):
        return Const(not expr.val)
    elif isinstance(expr, Var):
        return expr
    elif isinstance(expr, Not):
        return Not(mutate_logic(expr.expr, rate))
    elif isinstance(expr, (And, Or, Implies, Iff)):
        return type(expr)(
            mutate_logic(expr.left, rate),
            mutate_logic(expr.right, rate)
        )
    return expr

# ============================================
# EVOLUTION
# ============================================

class LogicSolution:
    def __init__(self, expr, fitness):
        self.expr = expr
        self.fitness = fitness
        self.truth_table = truth_table(expr)
        self.complexity = expr.complexity()

def evolve_logic(target_table, trans_lib, problem_name, pop_size=50, gens=40):
    """Evolve expression to match target truth table"""
    print(f"\n{'='*70}")
    print(f"PROBLEM: {problem_name}")
    print(f"{'='*70}")
    print(f"Target truth table: {target_table}")
    print()
    
    population = [random_logic_expr(0, 3, ['P', 'Q']) for _ in range(pop_size)]
    
    all_solutions = []
    best_ever = None
    best_fitness = 0.0
    
    for gen in range(gens):
        scores = []
        for expr in population:
            table = truth_table(expr)
            # Fitness = how many entries match
            matches = sum(1 for t, target in zip(table, target_table) if t == target)
            fitness = matches / len(target_table)
            scores.append((expr, fitness))
            
            if fitness > 0.7:
                all_solutions.append(LogicSolution(expr, fitness))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        
        if scores[0][1] > best_fitness:
            best_fitness = scores[0][1]
            best_ever = scores[0][0]
        
        if gen % 10 == 0 or scores[0][1] >= 0.99:
            avg = sum(s for _, s in scores) / len(scores)
            print(f"Gen {gen:2d}: Best={scores[0][1]:.3f} Avg={avg:.3f}")
        
        if scores[0][1] >= 0.99:
            print(f"✓ SOLVED at gen {gen} - continuing...")
        
        # Selection
        survivors = [e for e, _ in scores[:pop_size // 5]]
        
        # Next generation
        next_pop = survivors.copy()
        while len(next_pop) < pop_size:
            parent = random.choice(survivors)
            child = mutate_logic(parent, rate=0.2)
            next_pop.append(child)
        
        population = next_pop
    
    print(f"\nBest: {best_fitness:.3f}")
    print(f"Expression: {best_ever}")
    
    # Discover equivalences
    print(f"\n  🔬 Analyzing {len(all_solutions)} solutions...")
    discovered = 0
    for i in range(len(all_solutions)):
        for j in range(i + 1, len(all_solutions)):
            equiv = trans_lib.discover_equivalence(
                all_solutions[i].expr,
                all_solutions[j].expr
            )
            if equiv:
                if trans_lib.add_transformation(equiv):
                    discovered += 1
    
    if discovered > 0:
        print(f"  ✓ Discovered {discovered} equivalences!")
    
    return best_ever, best_fitness

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    print("="*70)
    print("GENETIC PROGRAMMING WITH PROPOSITIONAL LOGIC")
    print("="*70)
    print("\nPrimitives: ∧, ∨, ¬, →, ↔, T, F")
    print("Signatures: Truth tables")
    print("Discovery: Logical equivalences")
    print()
    
    trans_lib = LogicTransformationLibrary()
    
    # Problem 1: AND function
    # P Q | Result
    # T T | T
    # T F | F
    # F T | F
    # F F | F
    best, fit = evolve_logic((True, False, False, False), trans_lib,
                            "P ∧ Q", pop_size=50, gens=40)
    
    # Problem 2: OR function
    best, fit = evolve_logic((True, True, True, False), trans_lib,
                            "P ∨ Q", pop_size=50, gens=40)
    
    # Problem 3: IMPLIES
    best, fit = evolve_logic((True, False, True, True), trans_lib,
                            "P → Q", pop_size=50, gens=40)
    
    # Problem 4: XOR (exclusive or)
    best, fit = evolve_logic((False, True, True, False), trans_lib,
                            "P ⊕ Q (XOR)", pop_size=50, gens=40)
    
    # Show discoveries
    trans_lib.list_transformations()
    
    print("\n" + "="*70)
    print("RESULT")
    print("="*70)
    print(f"\nDiscovered {len(trans_lib.transformations)} logical equivalences")
    print("\nCan evolution discover De Morgan's laws?")
    print("Can it find that (P → Q) ≡ (¬P ∨ Q)?")
    print("\nThis demonstrates GP on pure logic - no arithmetic!")
