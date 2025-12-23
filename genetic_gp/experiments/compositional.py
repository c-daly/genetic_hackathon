"""
COMPOSITIONAL MATHEMATICAL GP WITH TOOL ACCUMULATION

Demonstrates how tools accumulate across problems:
- Solve problem → discover tool → save to library
- Later problems can reuse discovered tools
- Knowledge compounds as the library grows

Usage:
    python -m genetic_gp.experiments.compositional
"""

from genetic_gp.core.expressions import Const, Var, BinOp
from genetic_gp.core.signatures import behavioral_signature, analyze_growth
from genetic_gp.evolution.engine import evolve
from genetic_gp.tools.library import Tool, ToolLibrary
from genetic_gp.problems.math import (
    test_double,
    test_sum_to_n,
    test_factorial,
    test_sum_of_squares,
)


def run_problem(
    name: str,
    fitness_fn,
    library: ToolLibrary,
    tool_name: str | None = None,
    tool_desc: str = "",
    pop_size: int = 60,
    generations: int = 100,
) -> tuple:
    """Run evolution for a single problem and optionally save result as tool.

    Args:
        name: Display name for the problem
        fitness_fn: Fitness function to optimize
        library: Tool library for reuse
        tool_name: If provided, save result as tool with this name
        tool_desc: Description for the tool
        pop_size: Population size
        generations: Max generations

    Returns:
        (best_expression, fitness)
    """
    print("\n" + "=" * 70)
    print(f"PROBLEM: {name}")
    print("=" * 70)

    if len(library) > 0:
        print(f"\nAvailable tools: {', '.join(t.name for t in library)}")
    else:
        print("\nNo tools yet - starting from scratch")

    print(f"\nStarting evolution...")
    print(f"   Population: {pop_size}, Generations: {generations}")
    print()

    result = evolve(
        fitness_fn,
        pop_size=pop_size,
        generations=generations,
        tool_library=library,
        stop_at_fitness=0.99,
        verbose=True,
        report_interval=20,
    )

    if result.solved:
        print(f"\nSOLVED!")
        print(f"   Expression: {result.best_expr}")

        # Add to tool library if name provided and expression is non-trivial
        if tool_name and not library.is_trivial(result.best_expr):
            sig = behavioral_signature(result.best_expr)
            growth = analyze_growth(result.best_expr)
            tool = Tool(
                name=tool_name,
                expr=result.best_expr,
                signature=sig,
                metadata={
                    'growth_type': growth,
                    'description': tool_desc,
                    'fitness': result.best_fitness,
                },
            )
            if library.add(tool):
                print(f"\n   TOOL DISCOVERED: {tool_name}")
                print(f"   Description: {tool_desc}")
    else:
        print(f"\nDid not fully solve. Best: {result.best_fitness:.3f}")
        print(f"   Best expression: {result.best_expr}")

        # Still add partial solutions if decent
        if result.best_fitness >= 0.8 and tool_name:
            if not library.is_trivial(result.best_expr):
                sig = behavioral_signature(result.best_expr)
                growth = analyze_growth(result.best_expr)
                tool = Tool(
                    name=tool_name,
                    expr=result.best_expr,
                    signature=sig,
                    metadata={
                        'growth_type': growth,
                        'description': tool_desc + " (partial)",
                        'fitness': result.best_fitness,
                    },
                )
                if library.add(tool):
                    print(f"\n   Added as partial tool (80%+ correct)")

    return result.best_expr, result.best_fitness


def main():
    """Run compositional discovery across multiple problems."""
    print("=" * 70)
    print("COMPOSITIONAL MATHEMATICAL GP")
    print("Tool Accumulation & Discovery Process")
    print("=" * 70)
    print("\nWatch how tools build on previous discoveries...")

    # Shared tool library
    library = ToolLibrary()

    # Problem 1: Simple doubling (warm-up)
    expr1, fit1 = run_problem(
        "f(n) = 2n (double)",
        test_double,
        library,
        tool_name="double",
        tool_desc="Doubles its input",
        pop_size=50,
        generations=50,
    )

    # Problem 2: Summation
    expr2, fit2 = run_problem(
        "f(n) = 1+2+...+n (sum)",
        test_sum_to_n,
        library,
        tool_name="sum",
        tool_desc="Sum from 1 to n",
        pop_size=80,
        generations=150,
    )

    # Problem 3: Factorial (can use sum concept!)
    expr3, fit3 = run_problem(
        "f(n) = n! (factorial)",
        test_factorial,
        library,
        tool_name="factorial",
        tool_desc="Factorial of n",
        pop_size=80,
        generations=150,
    )

    # Problem 4: Sum of squares (can use sum tool!)
    expr4, fit4 = run_problem(
        "f(n) = 1^2+2^2+...+n^2 (sum of squares)",
        test_sum_of_squares,
        library,
        tool_name="sum_squares",
        tool_desc="Sum of squares from 1 to n",
        pop_size=80,
        generations=150,
    )

    # Summary
    print("\n" + "=" * 70)
    print("DISCOVERY SUMMARY")
    print("=" * 70)

    print("\nTools discovered:")
    library.print_summary()

    print("\nFitness results:")
    print(f"  double: {fit1:.3f}")
    print(f"  sum: {fit2:.3f}")
    print(f"  factorial: {fit3:.3f}")
    print(f"  sum_squares: {fit4:.3f}")

    # Check for compositional reuse
    print()
    if fit3 >= 0.8:
        expr_str = str(expr3).lower()
        if 'sum' in expr_str or 'double' in expr_str:
            print("Factorial used earlier tool concept!")
        else:
            print("Factorial discovered independently")

    if fit4 >= 0.8:
        expr_str = str(expr4)
        if any(t.name in expr_str for t in library):
            print("Sum of squares reused earlier tool!")

    print()
    print("This demonstrates compositional discovery:")
    print("  -> Tools accumulate across problems")
    print("  -> Later problems can build on earlier discoveries")
    print("  -> Knowledge compounds")


if __name__ == '__main__':
    main()
