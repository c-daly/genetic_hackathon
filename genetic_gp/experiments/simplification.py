"""
LEARNED SIMPLIFICATION TRANSFORMATIONS

GP discovers that different expressions have identical behavior.
When one is simpler, save as transformation rule.
Later evolution can apply these transformations.

Meta-computation: discovering rules for transforming computations.

Usage:
    python -m genetic_gp.experiments.simplification
"""

from genetic_gp.core.expressions import Const, Var, BinOp
from genetic_gp.core.signatures import behavioral_signature
from genetic_gp.evolution.engine import evolve
from genetic_gp.tools.transformation import (
    TransformationLibrary,
    discover_transformations_from_solutions,
)
from genetic_gp.problems.math import test_double, test_square, test_sum_to_n


def run_with_transformation_discovery(
    name: str,
    fitness_fn,
    trans_lib: TransformationLibrary,
    pop_size: int = 60,
    generations: int = 60,
) -> tuple:
    """Run evolution while discovering transformations from equivalent solutions.

    Args:
        name: Problem name for display
        fitness_fn: Fitness function
        trans_lib: TransformationLibrary to collect discoveries
        pop_size: Population size
        generations: Max generations

    Returns:
        (best_expression, fitness, num_transformations_discovered)
    """
    print(f"\n{'=' * 70}")
    print(f"PROBLEM: {name}")
    print(f"{'=' * 70}")
    print(f"Transformations known: {len(trans_lib)}")

    result = evolve(
        fitness_fn,
        pop_size=pop_size,
        generations=generations,
        collect_solutions_above=0.5,  # Track decent solutions
        stop_at_fitness=0.99,
        verbose=True,
        report_interval=20,
    )

    # Discover transformations from collected solutions
    num_discovered = 0
    if result.all_solutions:
        print(f"\nAnalyzing {len(result.all_solutions)} solutions for transformations...")
        num_discovered = discover_transformations_from_solutions(
            result.all_solutions,
            trans_lib,
            min_fitness=0.5,
            min_reduction=2,
        )
        if num_discovered > 0:
            print(f"Discovered {num_discovered} new transformation(s)!")

    # Try to simplify the best expression
    if result.best_expr is not None:
        simplified = trans_lib.try_simplify(result.best_expr)
        if simplified is not result.best_expr:
            print(f"\nSimplified solution:")
            print(f"  Original:   {result.best_expr} (complexity {result.best_expr.complexity()})")
            print(f"  Simplified: {simplified} (complexity {simplified.complexity()})")

    return result.best_expr, result.best_fitness, num_discovered


def main():
    """Run simplification discovery across multiple problems."""
    print("=" * 70)
    print("LEARNED SIMPLIFICATION TRANSFORMATIONS")
    print("Discovering Equivalent but Simpler Expressions")
    print("=" * 70)
    print("\nWatch how transformations accumulate and can be reused...")

    # Shared transformation library
    trans_lib = TransformationLibrary()

    # Problem 1: Double (simple, many equivalent forms)
    expr1, fit1, disc1 = run_with_transformation_discovery(
        "f(n) = 2n (double)",
        test_double,
        trans_lib,
        pop_size=60,
        generations=60,
    )

    # Problem 2: Square (several forms possible)
    expr2, fit2, disc2 = run_with_transformation_discovery(
        "f(n) = n^2 (square)",
        test_square,
        trans_lib,
        pop_size=60,
        generations=80,
    )

    # Problem 3: Sum 1 to n (loop vs closed form)
    expr3, fit3, disc3 = run_with_transformation_discovery(
        "f(n) = 1+2+...+n (sum)",
        test_sum_to_n,
        trans_lib,
        pop_size=80,
        generations=100,
    )

    # Summary
    print("\n" + "=" * 70)
    print("SIMPLIFICATION SUMMARY")
    print("=" * 70)

    print(f"\nTotal transformations discovered: {len(trans_lib)}")
    trans_lib.print_summary()

    print("\nFitness results:")
    print(f"  double: {fit1:.3f} (discovered {disc1} transformations)")
    print(f"  square: {fit2:.3f} (discovered {disc2} transformations)")
    print(f"  sum:    {fit3:.3f} (discovered {disc3} transformations)")

    print()
    print("This demonstrates meta-computation:")
    print("  -> Evolution discovers multiple equivalent forms")
    print("  -> Simpler forms are saved as transformation rules")
    print("  -> Rules can be applied to simplify future discoveries")


if __name__ == '__main__':
    main()
