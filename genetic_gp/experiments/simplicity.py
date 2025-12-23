"""
TWO-PHASE EVOLUTION: SOLVE THEN SIMPLIFY

Evolution in two phases:
1. Find any correct solution (accuracy >= 0.99)
2. Continue searching for simpler solutions that maintain correctness

No simplicity weight during evolution - we select purely on accuracy,
using complexity only as a tiebreaker. After finding a solution,
we continue for 10 more generations looking for simpler equivalents.

Usage:
    python -m genetic_gp.experiments.simplicity
"""

from typing import Callable

from genetic_gp.core.reporter import get_reporter
from genetic_gp.core.config import get_config, Verbosity
from genetic_gp.evolution.engine import evolve
from genetic_gp.problems.math import test_double, test_square, test_sum_to_n


def run_two_phase_evolution(
    problem_name: str,
    fitness_fn: Callable,
    num_runs: int = 3,
    pop_size: int = 60,
    generations: int = 80,
):
    """Run evolution with two-phase approach and show results.

    Args:
        problem_name: Name for display
        fitness_fn: Fitness function
        num_runs: Number of runs to average
        pop_size: Population size
        generations: Max generations
    """
    reporter = get_reporter()
    config = get_config()
    verbose = config.output.verbosity_level >= Verbosity.VERBOSE

    reporter.on_problem_started(
        problem_name,
        "Two-phase evolution: solve then simplify"
    )

    print("\n  Approach: Pure accuracy selection, then continue to find simpler solutions")
    print("  - Phase 1: Find any correct solution (accuracy >= 0.99)")
    print("  - Phase 2: Continue 10 more generations, keeping simpler correct solutions")
    print("  - Complexity is tiebreaker only (simpler wins when accuracy is equal)\n")

    results = []
    for i in range(num_runs):
        result = evolve(
            fitness_fn,
            pop_size=pop_size,
            generations=generations,
            verbose=verbose,
            reporter=reporter if verbose else None,
        )
        results.append(result)
        complexity = result.best_expr.complexity()
        solved = "✓" if result.solved else "✗"
        print(f"    Run {i+1}: {solved} Accuracy={result.best_fitness:.3f} Complexity={complexity} in {result.generations_run} gens")
        print(f"           Expression: {result.best_expr}")

    # Summary
    avg_complexity = sum(r.best_expr.complexity() for r in results) / num_runs
    avg_accuracy = sum(r.best_fitness for r in results) / num_runs
    solved_count = sum(1 for r in results if r.solved)

    print(f"\n  Summary ({num_runs} runs):")
    print("  " + "-" * 50)
    print(f"    Solved: {solved_count}/{num_runs}")
    print(f"    Average accuracy: {avg_accuracy:.3f}")
    print(f"    Average complexity: {avg_complexity:.1f}")

    # Show the simplest solution found
    best = min(results, key=lambda r: (not r.solved, r.best_expr.complexity()))
    if best.solved:
        print(f"\n  Simplest solution found:")
        print(f"    {best.best_expr}")
        print(f"    Complexity: {best.best_expr.complexity()}")


def main():
    """Run two-phase evolution demos."""
    print("=" * 70)
    print("TWO-PHASE EVOLUTION: SOLVE THEN SIMPLIFY")
    print("=" * 70)
    print()
    print("Evolution strategy:")
    print("  1. Evolve until problem is solved (accuracy >= 0.99)")
    print("  2. Continue for 10 more generations")
    print("  3. Only accept simpler solutions that maintain correctness")
    print("  4. Return the simplest correct solution found")
    print()
    print("Selection: Pure accuracy with complexity as tiebreaker")
    print("           (No simplicity weight - correctness is never sacrificed)")

    # Demo 1: Double
    run_two_phase_evolution("f(n) = 2n", test_double, num_runs=3)

    # Demo 2: Square
    run_two_phase_evolution("f(n) = n²", test_square, num_runs=3)

    # Demo 3: Sum to n
    run_two_phase_evolution("f(n) = 1+2+...+n", test_sum_to_n, num_runs=3, generations=100)

    # Summary
    print("\n" + "=" * 70)
    print("KEY INSIGHT")
    print("=" * 70)
    print()
    print("Two-phase evolution guarantees:")
    print("  ✓ Correctness is never sacrificed for simplicity")
    print("  ✓ After solving, actively search for simpler equivalents")
    print("  ✓ Complexity tiebreaker prefers simpler among equally accurate")
    print("  ✓ No arbitrary simplicity weights to tune")
    print()


if __name__ == '__main__':
    main()
