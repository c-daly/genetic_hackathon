"""
NOVELTY DETECTION DEMO

Demonstrates how novelty detection prevents saving trivial or duplicate
tools, ensuring the tool library contains genuinely useful patterns.

Usage:
    python -m genetic_gp.experiments.novelty
"""

from genetic_gp.core.expressions import Const, Var, BinOp, Sum
from genetic_gp.core.signatures import behavioral_signature, signature_similarity
from genetic_gp.tools.library import Tool, ToolLibrary


def demo_trivial_detection():
    """Show how trivial expressions are filtered out."""
    print("\n" + "=" * 70)
    print("TRIVIAL EXPRESSION DETECTION")
    print("=" * 70)

    library = ToolLibrary()

    # Trivial expressions that should NOT be saved
    trivial_exprs = [
        (Const(5), "Constant: 5"),
        (Var('n'), "Variable: n"),
        (BinOp('*', Var('n'), Const(2)), "Simple binop: n*2"),
        (BinOp('+', Var('n'), Const(1)), "Simple binop: n+1"),
        (BinOp('+', Var('n'), Var('n')), "Simple binop: n+n"),
    ]

    print("\nChecking trivial expressions:")
    for expr, desc in trivial_exprs:
        is_trivial = library.is_trivial(expr)
        status = "TRIVIAL (rejected)" if is_trivial else "not trivial"
        print(f"  {desc}: {status}")

    # Non-trivial expressions that SHOULD be saved
    print("\nChecking non-trivial expressions:")
    non_trivial_exprs = [
        (Sum('i', Const(1), Var('n'), Var('i')), "Sum: Σ(i=1..n)[i]"),
        (BinOp('*', Var('n'), BinOp('+', Var('n'), Const(1))),
         "Nested: n*(n+1)"),
        (BinOp('/', BinOp('*', Var('n'), BinOp('+', Var('n'), Const(1))), Const(2)),
         "Closed form: n*(n+1)/2"),
    ]

    for expr, desc in non_trivial_exprs:
        is_trivial = library.is_trivial(expr)
        status = "TRIVIAL (rejected)" if is_trivial else "not trivial (accepted)"
        print(f"  {desc}: {status}")


def demo_novelty_detection():
    """Show how similar expressions are detected as non-novel."""
    print("\n" + "=" * 70)
    print("NOVELTY DETECTION")
    print("=" * 70)

    library = ToolLibrary()

    # Add a tool: n*2 (double)
    double_expr = BinOp('*', Const(2), Var('n'))
    sig = behavioral_signature(double_expr)
    tool = Tool(name='double', expr=double_expr, signature=sig)
    library.add(tool)
    print(f"\nAdded tool: double = {double_expr}")

    # Check novelty of similar expressions
    test_exprs = [
        (BinOp('*', Const(2), Var('n')), "2*n (same as double)"),
        (BinOp('+', Var('n'), Var('n')), "n+n (equivalent to double)"),
        (BinOp('*', Var('n'), Const(2)), "n*2 (same behavior)"),
        (BinOp('*', Const(3), Var('n')), "3*n (different - triple)"),
        (BinOp('^', Var('n'), Const(2)), "n^2 (different - square)"),
    ]

    print("\nChecking novelty against library:")
    for expr, desc in test_exprs:
        is_novel = library.is_novel(expr)
        sig = behavioral_signature(expr)

        # Find similarity to existing
        max_sim = 0.0
        for t in library:
            sim = signature_similarity(sig, t.signature)
            max_sim = max(max_sim, sim)

        status = "NOVEL" if is_novel else "NOT NOVEL (duplicate)"
        print(f"  {desc}: {status} (similarity: {max_sim:.2f})")


def demo_should_save():
    """Show the full should_save decision logic."""
    print("\n" + "=" * 70)
    print("SHOULD_SAVE DECISION LOGIC")
    print("=" * 70)

    library = ToolLibrary()

    # Add an existing tool
    sum_expr = Sum('i', Const(1), Var('n'), Var('i'))
    sig = behavioral_signature(sum_expr)
    library.add(Tool(name='sum_to_n', expr=sum_expr, signature=sig))
    print(f"\nLibrary contains: sum_to_n = {sum_expr}")

    # Test cases
    test_cases = [
        (Sum('i', Const(1), Var('n'), Var('i')), 1.0, "Same expression, high fitness"),
        (Var('n'), 1.0, "Trivial expression, high fitness"),
        (Sum('i', Const(1), Var('n'), BinOp('^', Var('i'), Const(2))), 0.5, "Novel but low fitness"),
        (Sum('i', Const(1), Var('n'), BinOp('^', Var('i'), Const(2))), 1.0, "Novel, non-trivial, high fitness"),
    ]

    print("\nDecision results:")
    for expr, fitness, desc in test_cases:
        should = library.should_save(expr, fitness)
        result = "SAVE" if should else "REJECT"
        print(f"  {desc}: {result}")

        # Explain why
        if not should:
            if fitness < 0.95:
                print(f"    (fitness {fitness:.2f} < 0.95)")
            elif library.is_trivial(expr):
                print(f"    (trivial expression)")
            elif not library.is_novel(expr):
                print(f"    (not novel - similar exists)")


def main():
    """Run all novelty detection demos."""
    print("=" * 70)
    print("NOVELTY DETECTION DEMONSTRATION")
    print("=" * 70)
    print("\nShowing how the system filters trivial and duplicate patterns...")

    demo_trivial_detection()
    demo_novelty_detection()
    demo_should_save()

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("\nNovelty detection ensures the tool library stays useful:")
    print("  -> Trivial patterns (constants, variables, simple ops) are rejected")
    print("  -> Duplicate behaviors are detected via signature comparison")
    print("  -> Only novel, non-trivial, high-fitness discoveries are saved")
    print("  -> This keeps the library focused on genuinely useful patterns")


if __name__ == '__main__':
    main()
