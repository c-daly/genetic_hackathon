"""
PROPOSITIONAL LOGIC GENETIC PROGRAMMING

Demonstrates GP in a completely different domain - propositional logic.
Same principles apply: behavioral signatures (truth tables), novelty, etc.

Primitives: And (∧), Or (∨), Not (¬), Implies (→), Iff (↔)
Discovery targets: Tautologies, logical equivalences, De Morgan's laws

Usage:
    python -m genetic_gp.experiments.logic
"""

import random
from typing import Any, List

from genetic_gp.core.logic import (
    LConst, LVar, Not, And, Or, Implies, Iff,
    truth_table, is_tautology, is_contradiction, is_contingent,
    classify_expression, expressions_equivalent,
)


# ============================================
# RANDOM LOGIC EXPRESSION GENERATION
# ============================================

def random_logic_expr(
    depth: int = 0,
    max_depth: int = 3,
    vars_available: List[str] | None = None,
) -> Any:
    """Generate a random logic expression.

    Args:
        depth: Current recursion depth
        max_depth: Maximum expression depth
        vars_available: Variable names to use (default: ['P', 'Q'])

    Returns:
        A random logic expression
    """
    if vars_available is None:
        vars_available = ['P', 'Q']

    # Terminal condition
    if depth >= max_depth or random.random() < 0.4:
        choice = random.choice(['const', 'var'])
        if choice == 'const':
            return LConst(random.choice([True, False]))
        else:
            return LVar(random.choice(vars_available))

    # Compound expression
    choice = random.choice(['not', 'and', 'or', 'implies', 'iff'])

    if choice == 'not':
        return Not(random_logic_expr(depth + 1, max_depth, vars_available))
    elif choice == 'and':
        return And(
            random_logic_expr(depth + 1, max_depth, vars_available),
            random_logic_expr(depth + 1, max_depth, vars_available),
        )
    elif choice == 'or':
        return Or(
            random_logic_expr(depth + 1, max_depth, vars_available),
            random_logic_expr(depth + 1, max_depth, vars_available),
        )
    elif choice == 'implies':
        return Implies(
            random_logic_expr(depth + 1, max_depth, vars_available),
            random_logic_expr(depth + 1, max_depth, vars_available),
        )
    else:  # iff
        return Iff(
            random_logic_expr(depth + 1, max_depth, vars_available),
            random_logic_expr(depth + 1, max_depth, vars_available),
        )


def mutate_logic(
    expr: Any,
    rate: float = 0.3,
    vars_available: List[str] | None = None,
) -> Any:
    """Mutate a logic expression.

    Args:
        expr: Expression to mutate
        rate: Probability of replacing subtree
        vars_available: Available variable names

    Returns:
        Mutated expression
    """
    if vars_available is None:
        vars_available = ['P', 'Q']

    if random.random() < rate:
        return random_logic_expr(0, 3, vars_available)

    if isinstance(expr, LConst):
        return LConst(not expr.val)
    elif isinstance(expr, LVar):
        return expr
    elif isinstance(expr, Not):
        return Not(mutate_logic(expr.expr, rate, vars_available))
    elif isinstance(expr, (And, Or, Implies, Iff)):
        new_left = mutate_logic(expr.left, rate, vars_available)
        new_right = mutate_logic(expr.right, rate, vars_available)
        return type(expr)(new_left, new_right)

    return expr


# ============================================
# EVOLUTION FOR LOGIC
# ============================================

def evolve_tautology(
    pop_size: int = 100,
    generations: int = 100,
    vars_available: List[str] | None = None,
) -> tuple:
    """Evolve to find a tautology.

    Args:
        pop_size: Population size
        generations: Max generations
        vars_available: Variable names

    Returns:
        (best_expression, is_tautology)
    """
    if vars_available is None:
        vars_available = ['P', 'Q']

    population = [
        random_logic_expr(0, 3, vars_available)
        for _ in range(pop_size)
    ]

    best_ever = None
    best_score = 0.0

    for gen in range(generations):
        scores = []
        for expr in population:
            table = truth_table(expr)
            # Score = fraction of True values in truth table
            score = sum(table) / len(table)
            scores.append((expr, score))

            # Perfect tautology!
            if score == 1.0:
                print(f"Gen {gen}: Found tautology: {expr}")
                return expr, True

        scores.sort(key=lambda x: x[1], reverse=True)

        if scores[0][1] > best_score:
            best_score = scores[0][1]
            best_ever = scores[0][0]

        if gen % 20 == 0:
            print(f"Gen {gen}: Best score = {scores[0][1]:.3f}")

        # Selection and reproduction
        survivors = [e for e, _ in scores[:pop_size // 5]]
        next_pop = survivors.copy()
        while len(next_pop) < pop_size:
            parent = random.choice(survivors)
            child = mutate_logic(parent, 0.2, vars_available)
            next_pop.append(child)
        population = next_pop

    return best_ever, is_tautology(best_ever) if best_ever else False


def find_equivalences(
    num_expressions: int = 200,
    vars_available: List[str] | None = None,
) -> List[tuple]:
    """Generate random expressions and find equivalent pairs.

    Args:
        num_expressions: Number of expressions to generate
        vars_available: Variable names

    Returns:
        List of (expr1, expr2) equivalent pairs with different structure
    """
    if vars_available is None:
        vars_available = ['P', 'Q']

    expressions = [
        random_logic_expr(0, 3, vars_available)
        for _ in range(num_expressions)
    ]

    equivalences = []

    for i, expr1 in enumerate(expressions):
        for expr2 in expressions[i + 1:]:
            # Same structure doesn't count
            if str(expr1) == str(expr2):
                continue

            if expressions_equivalent(expr1, expr2):
                # Prefer simpler version first
                if expr1.complexity() <= expr2.complexity():
                    equivalences.append((expr1, expr2))
                else:
                    equivalences.append((expr2, expr1))

                # Stop if we have enough
                if len(equivalences) >= 10:
                    return equivalences

    return equivalences


def main():
    """Run logic GP demonstrations."""
    print("=" * 70)
    print("PROPOSITIONAL LOGIC GENETIC PROGRAMMING")
    print("=" * 70)

    # Demo 1: Find a tautology
    print("\n" + "-" * 70)
    print("DEMO 1: Evolving a Tautology")
    print("-" * 70)
    print("Goal: Find an expression that is always true")

    expr, found = evolve_tautology(pop_size=100, generations=100)
    if found:
        print(f"\nSuccess! Found tautology: {expr}")
        print(f"Complexity: {expr.complexity()}")
    else:
        print(f"\nBest found: {expr}")
        print(f"Truth table: {truth_table(expr)}")

    # Demo 2: Find logical equivalences
    print("\n" + "-" * 70)
    print("DEMO 2: Discovering Logical Equivalences")
    print("-" * 70)
    print("Generating random expressions and finding equivalent pairs...")

    equivalences = find_equivalences(num_expressions=300)

    if equivalences:
        print(f"\nFound {len(equivalences)} equivalence(s):")
        for i, (e1, e2) in enumerate(equivalences[:5], 1):
            print(f"\n{i}. {e1}")
            print(f"   ≡ {e2}")
            print(f"   (complexity {e1.complexity()} vs {e2.complexity()})")
    else:
        print("No equivalences found in this run")

    # Demo 3: Classify random expressions
    print("\n" + "-" * 70)
    print("DEMO 3: Classifying Random Expressions")
    print("-" * 70)

    tautologies = 0
    contradictions = 0
    contingent = 0

    for _ in range(100):
        expr = random_logic_expr(0, 3, ['P', 'Q'])
        classification = classify_expression(expr)
        if classification == 'tautology':
            tautologies += 1
        elif classification == 'contradiction':
            contradictions += 1
        else:
            contingent += 1

    print(f"\nOut of 100 random expressions:")
    print(f"  Tautologies:     {tautologies}")
    print(f"  Contradictions:  {contradictions}")
    print(f"  Contingent:      {contingent}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("\nThis demonstrates domain-general GP principles:")
    print("  -> Same framework works for math and logic domains")
    print("  -> Behavioral signatures = truth tables (instead of I/O pairs)")
    print("  -> Can discover tautologies, equivalences, simplifications")
    print("  -> Complexity metrics guide toward elegant proofs")


if __name__ == '__main__':
    main()
