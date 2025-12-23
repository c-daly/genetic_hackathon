# LaTeX Expression Reporting Design

## Overview

Add beautiful mathematical expression rendering to the genetic programming framework. Expressions are rendered as proper LaTeX math and displayed inline in the terminal using sixel graphics.

## Goals

1. Report expressions when found during evolution
2. Report expressions when simplified
3. Render using LaTeX for readability (complex nested expressions are unreadable as text)
4. Configurable verbosity levels
5. Config file based settings

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Evolution      │────▶│  Reporter        │────▶│  Rich Console   │
│  Engine         │     │  (formats events)│     │  (renders)      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │  Config          │
                        │  (.gp_config.yaml)│
                        └──────────────────┘
```

## New Modules

### `genetic_gp/core/config.py`
- Load YAML config from `.gp_config.yaml`
- Provide defaults if no config exists
- Expose typed config object

### `genetic_gp/core/latex.py`
- Add `to_latex(pretty: bool = True)` method to expressions
- Pretty formatting rules:
  - Coefficient ordering: `n * 3` → `3n`
  - Identity removal: `1 * n` → `n`, `n + 0` → `n`
  - Squaring detection: `n * n` → `n^2`
  - Division as fraction: `n / 2` → `\frac{n}{2}`
  - Negative handling: `0 - n` → `-n`
  - Proper sum/product: `Sum(i,1,n,body)` → `\sum_{i=1}^{n} body`

### `genetic_gp/core/renderer.py`
- Render LaTeX to PNG using matplotlib's mathtext
- Output as sixel graphics for terminal display
- Fallback to Unicode/SymPy pretty printing if sixel not supported
- Auto-detect terminal capabilities

### `genetic_gp/core/reporter.py`
- Event-based reporting system
- Filter events based on verbosity level
- Format output with Rich panels and boxes
- Coordinate LaTeX rendering

## Events

| Event | Verbosity | Description |
|-------|-----------|-------------|
| `problem_started` | minimal | Problem name, parameters |
| `generation_update` | verbose | Every N generations, top candidates |
| `new_best` | normal | Improved fitness found |
| `solved` | minimal | Target fitness reached |
| `simplified` | minimal | Transformation applied |
| `tool_discovered` | minimal | New tool saved to library |

## Config File

`.gp_config.yaml`:

```yaml
output:
  verbosity: normal    # minimal | normal | verbose
  renderer: sixel      # sixel | unicode | plain
  fallback: unicode    # Fallback if sixel not supported

latex:
  pretty: true         # Apply formatting rules
  font_size: 14        # For rendered images
  dpi: 150             # Image resolution

events:
  minimal:
    - problem_started
    - solved
    - simplified
    - tool_discovered
  normal:
    - new_best
  verbose:
    - generation_update

report_interval: 10    # Generations between updates (verbose mode)
```

## Example Output

```
┌─ Generation 34 ─ New Best ───────────────────────────────────────────┐
│                                                                      │
│                        [rendered LaTeX image]                        │
│                                                                      │
│                              n                                       │
│                             ___                                      │
│                             ╲                                        │
│                              ╲   i                                   │
│                              ╱                                       │
│                             ╱                                        │
│                             ‾‾‾                                      │
│                            i = 1                                     │
│                                                                      │
│  Fitness: 1.000                Complexity: 6                         │
└──────────────────────────────────────────────────────────────────────┘

┌─ Simplification Applied ─────────────────────────────────────────────┐
│                                                                      │
│   [original]              ───▶           [simplified]                │
│                                                                      │
│  Complexity: 6  ───▶  5                  Reduction: 17%              │
└──────────────────────────────────────────────────────────────────────┘
```

With sixel rendering, the math appears as crisp, publication-quality typeset mathematics.

## Dependencies

New dependencies to add:
- `rich` - Terminal formatting, panels, boxes
- `matplotlib` - LaTeX rendering to PNG
- `pyyaml` - Config file parsing

## Files to Modify

- `evolution/engine.py` - Emit events to reporter
- `tools/transformation.py` - Emit simplification events
- `experiments/*.py` - Use reporter instead of print()

## Implementation Order

1. Create config module and default config file
2. Create latex module with `to_latex()` methods
3. Create renderer module (sixel + fallbacks)
4. Create reporter module with event handling
5. Integrate into evolution engine
6. Update experiments to use reporter
7. Add tests
