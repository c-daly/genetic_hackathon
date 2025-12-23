# Genetic Hackathon: Meta-Computational Discovery System

A complete implementation of genetic programming that discovers both computations and transformations of computations through pure evolutionary experimentation.

## Overview

This system demonstrates **meta-computation**: the ability to not only discover computational patterns, but also to learn its own optimization rules by comparing behaviorally equivalent expressions with different complexity.

## Core Capabilities

1. **Pure Genetic Programming** - Discovers patterns from mathematical primitives (Σ, operations, variables) without linguistic labels
2. **Behavioral Signatures** - Functions identified by what they compute, not how they're written
3. **Novelty Detection** - Rejects trivial patterns, only saves meaningful discoveries
4. **Pattern Generalization** - Extracts parameterized tools (n² → power(base, exp))
5. **Learned Simplifications** - Discovers transformation rules by finding equivalent expressions with different complexity
6. **Tool Composition** - Later problems use earlier discoveries
7. **Meta-computation** - System learns its own optimization rules

## Files

### Main Implementations

**`learned_simplification.py`** ⭐ **[LATEST COMPLETE SYSTEM]**
- Full implementation of learned simplification transformations
- Discovers that different expressions have identical behavior but different complexity
- When one is simpler, saves as transformation rule for future use
- Evolution modified to collect alternatives: lowered tracking threshold, continues after solving, collects 1000+ solutions per problem
- Application: try_simplify() checks if expression matches known transformation signatures and applies simplification
- Demonstrated on:
  - Problem 1: f(n) = 2n → discovered transformations reducing complexity by 33 and 7 points
  - Problem 2: f(n) = sum(1 to n) → discovered transformations reducing complexity by 12 and 16 points

**`logic_gp.py`** 🆕 **[PROPOSITIONAL LOGIC EXTENSION]**
- Applies the complete meta-computational framework to propositional logic
- Primitives: AND, OR, NOT, IMPLIES, XOR, variables p, q, r
- Behavioral signatures: truth tables for all input combinations
- Discovers logical equivalences: (p AND p) = p, (p OR NOT p) = True, De Morgan's laws, etc.
- Learns simplification transformations by finding logically equivalent but simpler expressions
- Demonstrates the framework generalizes beyond arithmetic to any domain with behavioral equivalence

**`pattern_generalization.py`**
- Extracts parameterized patterns from specific discoveries
- When system discovers n², extracts power(base, exp) tool
- Enables compositional learning: later problems use earlier abstractions
- Demonstrated on f(n) = n² evolution

**`novelty_detection.py`**
- Rejects trivial or redundant discoveries
- Ensures only meaningful patterns enter the tool library
- Uses behavioral diversity and structural difference metrics

**`compositional_gp.py`**
- Shows how discovered tools compose
- Problem 1 discovers sum(1..n)
- Problem 2 uses it to discover integral as n²/2
- Demonstrates tool accumulation and reuse

**`honest_math_gp.py`**
- Baseline implementation of pure mathematical GP
- No linguistic shortcuts, only evolution and testing
- Discovers sum(1..n) from primitives alone
- Validates the core approach works

**`simplicity_driven.py`**
- Evolution guided by simplicity metric
- Fitness = correctness - complexity_penalty
- Encourages discovery of elegant solutions

## Key Results

### Learned Simplification (Mathematics)

**Problem 1: f(n) = 2n**
- Analyzed 1159 solutions across 39 generations
- Discovered transformation: `(n+(n-Σ(...)))` [complexity 36] → `(n+n)` [complexity 3]
- **33-point complexity reduction**

**Problem 2: f(n) = sum(1 to n)**
- Analyzed 1560 solutions
- Discovered transformation: `Σ(k=Σ(k=2.92..n)[...]..n)[k]` [complexity 18] → `Σ(k=0..n)[k]` [complexity 6]
- **12-point complexity reduction**

### Logic Domain

**Tautology Discovery: (p ∨ ¬p)**
- Discovered from primitives in 3 generations
- Multiple equivalent representations found
- System learns simplifications like `(p OR (NOT p))` is simpler than `((p OR (NOT p)) AND True)`

**Logical Equivalences**
- Idempotence: `(p AND p) = p`
- Absorption: `(p OR (p AND q)) = p`
- De Morgan: `NOT (p AND q) = (NOT p) OR (NOT q)`

## Usage

### Mathematics Domain

```python
from learned_simplification import run_simplification_experiment

# Run complete experiment
run_simplification_experiment()

# Evolves multiple problems
# Collects alternative solutions
# Discovers transformations automatically
# Applies learned simplifications to new problems
```

### Logic Domain

```python
from logic_gp import run_logic_experiment

# Discover logical patterns
run_logic_experiment()

# Evolves logical expressions
# Discovers equivalences
# Learns simplification rules
# All through behavioral comparison
```

## How It Works

### 1. Evolution Phase
```
Generate random expressions → Test on inputs → Select best → Mutate → Repeat
```

### 2. Discovery Phase
```
When solution found:
- Continue evolving to collect alternatives
- Track 1000+ behaviorally equivalent solutions
- Lower fitness threshold to 0.5 to collect diverse variants
```

### 3. Transformation Learning
```
For each pair of solutions:
    if behavioral_signatures_match(expr1, expr2):
        if complexity(expr1) > complexity(expr2):
            save_transformation(from=expr1, to=expr2)
```

### 4. Application Phase
```
When evolving new problem:
    for each expression:
        signature = compute_signature(expr)
        if signature in known_transformations:
            apply_simplification()
```

## Technical Details

### Behavioral Signatures

**Mathematics:**
- Tuple of outputs for n ∈ {0, 1, 2, 3, 4}
- Example: f(n) = 2n has signature (0, 2, 4, 6, 8)

**Logic:**
- Truth table for all variable combinations
- Example: p AND q has signature (F, F, F, T)

### Complexity Metric

Count of primitive operations:
- Constants: 0.1
- Variables: 0.5
- Operations: 1.0 each
- Summations: base 2.0 + complexity of components

### Novelty Detection

Expression is novel if:
1. No existing tool has same behavioral signature, AND
2. Structural difference from all existing tools > threshold

## Validation

✓ **Non-linguistic discovery** - No LLMs in core loop  
✓ **Behavioral equivalence** - Functions compared by I/O behavior  
✓ **Autonomous learning** - System discovers its own optimization rules  
✓ **Compositional** - Transformations can chain  
✓ **Self-improving** - Learns how to improve itself  
✓ **Domain-general** - Works for mathematics AND logic  

## Key Insights

1. **Meta-computation is possible**: Systems can learn their own optimization rules
2. **Behavioral signatures enable discovery**: Identity comes from behavior, not syntax
3. **Complexity drives simplification**: When two expressions compute the same thing, prefer simpler
4. **Evolution finds alternatives**: By continuing past first solution, we discover equivalent variants
5. **Transformations transfer**: Rules learned on one problem apply to others
6. **Framework generalizes**: Same approach works across different computational domains

## Research Implications

This system demonstrates:
- **Innovative computation through experimentation** rather than deduction
- **Self-discovery of optimization rules** without human-provided heuristics
- **Meta-learning** where systems improve their own learning process
- **Domain-general pattern discovery** that transfers across problem types

## Next Steps

Potential extensions:
- Apply to more domains (graph algorithms, string processing, etc.)
- Multi-objective optimization (simplicity vs. performance)
- Hierarchical composition of transformations
- Transfer learning across domains
- Discovering new primitive operations

## Author Notes

This is an engine of innovative computation. It doesn't just solve problems—it learns how to solve them better. It discovers both the computations and the transformations of computations. It demonstrates that systems can bootstrap their own improvement through behavioral exploration and comparison.

The code is clean, documented, and ready to extend. Have fun experimenting!
