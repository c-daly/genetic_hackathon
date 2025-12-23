"""
SIMPLICITY-DRIVEN EVOLUTION

Evolution guided by both accuracy AND simplicity.
Demonstrates Occam's razor: among equivalent solutions, prefer simpler ones.

Usage:
    python -m genetic_gp.experiments.simplicity
"""

import math
from typing import Callable

from genetic_gp.core.expressions import Const, Var, BinOp, Sum
from genetic_gp.core.signatures import behavioral_signature
from genetic_gp.core.reporter import get_reporter
from genetic_gp.core.config import get_config, Verbosity
from genetic_gp.evolution.generator import random_expr
from genetic_gp.evolution.mutation import mutate
from genetic_gp.problems.math import test_double, test_square, test_sum_to_n
import random


def evolve_with_simplicity(
    fitness_fn: Callable,
    simplicity_weight: float = 0.3,
    pop_size: int = 60,
    generations: int = 80,
    verbose: bool = None,
) -> tuple:
    """Evolution with combined accuracy and simplicity pressure.

    Combined fitness = accuracy * (1 - w) + simplicity * w

    Where simplicity = exp(-complexity / 10)

    Args:
        fitness_fn: Base fitness function (accuracy)
        simplicity_weight: Weight for simplicity (0-1)
        pop_size: Population size
        generations: Max generations
        verbose: Print progress (None = use config)

    Returns:
        (best_expression, accuracy, combined_fitness)
    """
    reporter = get_reporter()
    config = get_config()

    # Use config verbosity if not explicitly set
    if verbose is None:
        verbose = config.output.verbosity_level >= Verbosity.VERBOSE
    population = [random_expr(0, 3, ['n']) for _ in range(pop_size)]

    best_ever = None
    best_combined = 0.0
    best_accuracy = 0.0

    for gen in range(generations):
        scores = []

        for expr in population:
            # Accuracy component
            accuracy = fitness_fn(lambda n, e=expr: e.eval({'n': n}))

            # Simplicity component
            complexity = expr.complexity()
            simplicity = math.exp(-complexity / 10.0)

            # Combined fitness
            combined = accuracy * (1 - simplicity_weight) + simplicity * simplicity_weight

            scores.append((expr, accuracy, combined))

        # Sort by combined fitness
        scores.sort(key=lambda x: x[2], reverse=True)

        # Track best
        if scores[0][2] > best_combined:
            best_combined = scores[0][2]
            best_accuracy = scores[0][1]
            best_ever = scores[0][0]

            # Show new best in verbose mode
            if verbose:
                reporter.on_new_best(best_ever, best_accuracy, gen, simplicity_weight)

        if verbose and gen % 20 == 0:
            reporter.on_generation_update(gen, scores[0][2])

        # Check for solved with good simplicity
        if scores[0][1] >= 0.99:
            if verbose:
                reporter.on_solved(scores[0][0], scores[0][1], gen, simplicity_weight)
            return scores[0][0], scores[0][1], scores[0][2]

        # Selection and reproduction
        survivors = [e for e, _, _ in scores[:pop_size // 5]]
        next_pop = survivors.copy()
        while len(next_pop) < pop_size:
            parent = random.choice(survivors)
            child = mutate(parent, rate=0.2, vars_available=['n'])
            next_pop.append(child)
        population = next_pop

    return best_ever, best_accuracy, best_combined


def compare_with_without_simplicity(
    problem_name: str,
    fitness_fn: Callable,
    num_runs: int = 3,
):
    """Compare evolution with and without simplicity pressure.

    Args:
        problem_name: Name for display
        fitness_fn: Fitness function
        num_runs: Number of runs to average
    """
    reporter = get_reporter()
    reporter.on_problem_started(
        problem_name,
        "Comparing evolution with and without simplicity pressure"
    )

    # Without simplicity pressure
    print("\n--- Without simplicity pressure (weight=0.0) ---")
    results_no_simp = []
    for i in range(num_runs):
        expr, acc, _ = evolve_with_simplicity(
            fitness_fn,
            simplicity_weight=0.0,
        )
        results_no_simp.append((expr, acc, expr.complexity()))
        print(f"  Run {i+1}: Accuracy={acc:.3f} Complexity={expr.complexity()}")

    avg_complexity_no = sum(r[2] for r in results_no_simp) / num_runs
    avg_accuracy_no = sum(r[1] for r in results_no_simp) / num_runs

    # With simplicity pressure
    print("\n--- With simplicity pressure (weight=0.3) ---")
    results_simp = []
    for i in range(num_runs):
        expr, acc, _ = evolve_with_simplicity(
            fitness_fn,
            simplicity_weight=0.3,
        )
        results_simp.append((expr, acc, expr.complexity()))
        print(f"  Run {i+1}: Accuracy={acc:.3f} Complexity={expr.complexity()}")

    avg_complexity_simp = sum(r[2] for r in results_simp) / num_runs
    avg_accuracy_simp = sum(r[1] for r in results_simp) / num_runs

    # Summary
    print(f"\nSummary (averaged over {num_runs} runs):")
    print(f"  Without simplicity: Accuracy={avg_accuracy_no:.3f} "
          f"Avg Complexity={avg_complexity_no:.1f}")
    print(f"  With simplicity:    Accuracy={avg_accuracy_simp:.3f} "
          f"Avg Complexity={avg_complexity_simp:.1f}")

    if avg_complexity_simp < avg_complexity_no:
        reduction = (1 - avg_complexity_simp / avg_complexity_no) * 100
        print(f"\n  -> Simplicity pressure reduced complexity by {reduction:.0f}%")

    # Show the best (simplest) solution found with simplicity pressure
    best_result = min(results_simp, key=lambda r: r[2])  # Lowest complexity
    if best_result[1] >= 0.99:  # If it solved the problem
        reporter.on_solved(best_result[0], best_result[1], 0, simplicity_weight=0.3)


def main():
    """Run simplicity-driven evolution demos."""
    print("=" * 70)
    print("SIMPLICITY-DRIVEN EVOLUTION")
    print("Occam's Razor: Prefer Simpler Solutions")
    print("=" * 70)

    # Demo 1: Show effect on double
    compare_with_without_simplicity("f(n) = 2n", test_double, num_runs=3)

    # Demo 2: Show effect on square
    compare_with_without_simplicity("f(n) = n^2", test_square, num_runs=3)

    # Demo 3: Detailed run with verbose output
    print("\n" + "=" * 70)
    print("DETAILED RUN: Sum 1 to n with simplicity pressure")
    print("=" * 70)

    print("\nRunning evolution with simplicity_weight=0.3...")
    expr, accuracy, combined = evolve_with_simplicity(
        test_sum_to_n,
        simplicity_weight=0.3,
        pop_size=80,
        generations=100,
        verbose=True,
    )

    print(f"\nFinal result:")
    print(f"  Expression: {expr}")
    print(f"  Accuracy:   {accuracy:.3f}")
    print(f"  Complexity: {expr.complexity()}")

    # Verify it works
    print(f"\nVerification:")
    for n in [1, 2, 3, 5, 10]:
        result = expr.eval({'n': n})
        expected = n * (n + 1) / 2
        match = "✓" if abs(result - expected) < 0.1 else "✗"
        print(f"  f({n}) = {result:.1f} (expected {expected:.1f}) {match}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("\nSimplicity pressure encourages elegant solutions:")
    print("  -> Combined fitness balances accuracy and simplicity")
    print("  -> Evolution prefers shorter expressions when accuracy is equal")
    print("  -> Results in more interpretable, generalizable solutions")
    print("  -> Implements Occam's razor automatically")


if __name__ == '__main__':
    main()
