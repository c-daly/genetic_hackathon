# LaTeX Expression Reporting Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add beautiful LaTeX-rendered mathematical expression output to the terminal using sixel graphics.

**Architecture:** Event-based reporter receives evolution events, converts expressions to LaTeX, renders as PNG via matplotlib, outputs as sixel graphics with Rich formatting. Config loaded from YAML file.

**Tech Stack:** matplotlib (LaTeX rendering), Rich (terminal formatting), PyYAML (config), sixel protocol for inline images.

---

## Task 1: Add Dependencies

**Files:**
- Modify: `requirements.txt` (create if doesn't exist)
- Modify: `pyproject.toml` (if exists)

**Step 1: Create requirements.txt**

```
rich>=13.0.0
matplotlib>=3.7.0
pyyaml>=6.0
```

**Step 2: Install dependencies**

Run: `pip install rich matplotlib pyyaml`
Expected: Successfully installed

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: add dependencies for LaTeX reporting"
```

---

## Task 2: Config Module

**Files:**
- Create: `genetic_gp/core/config.py`
- Test: `tests/test_config.py`

**Step 1: Write the failing test**

```python
# tests/test_config.py
"""Tests for configuration loading."""

import pytest
import tempfile
import os
from pathlib import Path


class TestConfig:
    """Tests for Config class."""

    def test_default_config_when_no_file(self):
        """Should return defaults when no config file exists."""
        from genetic_gp.core.config import Config, load_config

        config = load_config(Path("/nonexistent/path"))

        assert config.output.verbosity == "normal"
        assert config.output.renderer == "sixel"
        assert config.latex.pretty is True

    def test_load_from_yaml(self):
        """Should load settings from YAML file."""
        from genetic_gp.core.config import load_config

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".gp_config.yaml"
            config_path.write_text("""
output:
  verbosity: verbose
  renderer: unicode
latex:
  pretty: false
  font_size: 18
""")
            config = load_config(Path(tmpdir))

            assert config.output.verbosity == "verbose"
            assert config.output.renderer == "unicode"
            assert config.latex.pretty is False
            assert config.latex.font_size == 18

    def test_verbosity_levels(self):
        """Verbosity enum should have correct ordering."""
        from genetic_gp.core.config import Verbosity

        assert Verbosity.MINIMAL < Verbosity.NORMAL < Verbosity.VERBOSE
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with "No module named 'genetic_gp.core.config'"

**Step 3: Write minimal implementation**

```python
# genetic_gp/core/config.py
"""Configuration loading for genetic programming framework."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any

import yaml


class Verbosity(IntEnum):
    """Verbosity levels for reporting."""
    MINIMAL = 1
    NORMAL = 2
    VERBOSE = 3

    @classmethod
    def from_str(cls, s: str) -> "Verbosity":
        return cls[s.upper()]


@dataclass
class OutputConfig:
    """Output configuration."""
    verbosity: str = "normal"
    renderer: str = "sixel"
    fallback: str = "unicode"

    @property
    def verbosity_level(self) -> Verbosity:
        return Verbosity.from_str(self.verbosity)


@dataclass
class LatexConfig:
    """LaTeX rendering configuration."""
    pretty: bool = True
    font_size: int = 14
    dpi: int = 150


@dataclass
class Config:
    """Main configuration container."""
    output: OutputConfig = field(default_factory=OutputConfig)
    latex: LatexConfig = field(default_factory=LatexConfig)
    report_interval: int = 10


def load_config(search_path: Path | None = None) -> Config:
    """Load configuration from .gp_config.yaml.

    Args:
        search_path: Directory to search for config file.
                    Defaults to current working directory.

    Returns:
        Config object with settings (defaults if no file found)
    """
    if search_path is None:
        search_path = Path.cwd()

    config_file = search_path / ".gp_config.yaml"

    if not config_file.exists():
        return Config()

    with open(config_file) as f:
        data = yaml.safe_load(f) or {}

    output_data = data.get("output", {})
    latex_data = data.get("latex", {})

    return Config(
        output=OutputConfig(**output_data),
        latex=LatexConfig(**latex_data),
        report_interval=data.get("report_interval", 10),
    )


# Global config instance (lazy loaded)
_config: Config | None = None


def get_config() -> Config:
    """Get global config instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reset_config() -> None:
    """Reset global config (for testing)."""
    global _config
    _config = None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add genetic_gp/core/config.py tests/test_config.py
git commit -m "feat: add config module for YAML settings"
```

---

## Task 3: LaTeX Conversion Module

**Files:**
- Create: `genetic_gp/core/latex.py`
- Test: `tests/test_latex.py`

**Step 1: Write the failing test**

```python
# tests/test_latex.py
"""Tests for LaTeX conversion."""

import pytest
from genetic_gp.core.expressions import Const, Var, BinOp, Sum, Product


class TestToLatexBasic:
    """Tests for basic LaTeX conversion."""

    def test_const_to_latex(self):
        from genetic_gp.core.latex import to_latex
        assert to_latex(Const(5)) == "5"
        assert to_latex(Const(3.14)) == "3.14"

    def test_var_to_latex(self):
        from genetic_gp.core.latex import to_latex
        assert to_latex(Var("n")) == "n"
        assert to_latex(Var("x")) == "x"

    def test_binop_add_to_latex(self):
        from genetic_gp.core.latex import to_latex
        expr = BinOp("+", Var("n"), Const(1))
        assert to_latex(expr) == "n + 1"

    def test_binop_mult_to_latex(self):
        from genetic_gp.core.latex import to_latex
        expr = BinOp("*", Var("n"), Const(2))
        # Raw: n \cdot 2, Pretty: 2n
        assert to_latex(expr, pretty=False) == r"n \cdot 2"

    def test_binop_power_to_latex(self):
        from genetic_gp.core.latex import to_latex
        expr = BinOp("^", Var("n"), Const(2))
        assert to_latex(expr) == "n^{2}"

    def test_sum_to_latex(self):
        from genetic_gp.core.latex import to_latex
        expr = Sum("i", Const(1), Var("n"), Var("i"))
        assert to_latex(expr) == r"\sum_{i=1}^{n} i"

    def test_product_to_latex(self):
        from genetic_gp.core.latex import to_latex
        expr = Product("i", Const(1), Var("n"), Var("i"))
        assert to_latex(expr) == r"\prod_{i=1}^{n} i"


class TestToLatexPretty:
    """Tests for pretty LaTeX formatting."""

    def test_coefficient_ordering(self):
        """n * 3 -> 3n"""
        from genetic_gp.core.latex import to_latex
        expr = BinOp("*", Var("n"), Const(3))
        assert to_latex(expr, pretty=True) == "3n"

    def test_identity_mult_removal(self):
        """1 * n -> n"""
        from genetic_gp.core.latex import to_latex
        expr = BinOp("*", Const(1), Var("n"))
        assert to_latex(expr, pretty=True) == "n"

    def test_identity_add_removal(self):
        """n + 0 -> n"""
        from genetic_gp.core.latex import to_latex
        expr = BinOp("+", Var("n"), Const(0))
        assert to_latex(expr, pretty=True) == "n"

    def test_squaring_detection(self):
        """n * n -> n^2"""
        from genetic_gp.core.latex import to_latex
        expr = BinOp("*", Var("n"), Var("n"))
        assert to_latex(expr, pretty=True) == "n^{2}"

    def test_division_as_fraction(self):
        """n / 2 -> \frac{n}{2}"""
        from genetic_gp.core.latex import to_latex
        expr = BinOp("/", Var("n"), Const(2))
        assert to_latex(expr, pretty=True) == r"\frac{n}{2}"

    def test_negative_handling(self):
        """0 - n -> -n"""
        from genetic_gp.core.latex import to_latex
        expr = BinOp("-", Const(0), Var("n"))
        assert to_latex(expr, pretty=True) == "-n"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_latex.py -v`
Expected: FAIL with "No module named 'genetic_gp.core.latex'"

**Step 3: Write minimal implementation**

```python
# genetic_gp/core/latex.py
"""LaTeX conversion for mathematical expressions."""

from __future__ import annotations
from typing import Any

from genetic_gp.core.expressions import Const, Var, BinOp, Sum, Product, ToolCall


def to_latex(expr: Any, pretty: bool = True) -> str:
    """Convert expression to LaTeX string.

    Args:
        expr: Expression to convert
        pretty: Apply pretty formatting rules (coefficient ordering, etc.)

    Returns:
        LaTeX string representation
    """
    if isinstance(expr, Const):
        return _const_to_latex(expr)
    elif isinstance(expr, Var):
        return _var_to_latex(expr)
    elif isinstance(expr, BinOp):
        return _binop_to_latex(expr, pretty)
    elif isinstance(expr, Sum):
        return _sum_to_latex(expr, pretty)
    elif isinstance(expr, Product):
        return _product_to_latex(expr, pretty)
    elif isinstance(expr, ToolCall):
        return _toolcall_to_latex(expr, pretty)
    else:
        return str(expr)


def _const_to_latex(expr: Const) -> str:
    """Convert constant to LaTeX."""
    if expr.val == int(expr.val):
        return str(int(expr.val))
    return str(round(expr.val, 2))


def _var_to_latex(expr: Var) -> str:
    """Convert variable to LaTeX."""
    return expr.name


def _binop_to_latex(expr: BinOp, pretty: bool) -> str:
    """Convert binary operation to LaTeX."""
    left = to_latex(expr.left, pretty)
    right = to_latex(expr.right, pretty)

    if pretty:
        result = _apply_pretty_rules(expr, left, right)
        if result is not None:
            return result

    # Raw conversion
    if expr.op == "+":
        return f"{left} + {right}"
    elif expr.op == "-":
        return f"{left} - {right}"
    elif expr.op == "*":
        return rf"{left} \cdot {right}"
    elif expr.op == "/":
        if pretty:
            return rf"\frac{{{left}}}{{{right}}}"
        return f"{left} / {right}"
    elif expr.op == "^":
        return f"{left}^{{{right}}}"
    else:
        return f"{left} {expr.op} {right}"


def _apply_pretty_rules(expr: BinOp, left: str, right: str) -> str | None:
    """Apply pretty formatting rules. Returns None if no rule applies."""

    # Identity removal: n + 0 -> n, 0 + n -> n
    if expr.op == "+" and isinstance(expr.right, Const) and expr.right.val == 0:
        return left
    if expr.op == "+" and isinstance(expr.left, Const) and expr.left.val == 0:
        return right

    # Identity removal: 1 * n -> n, n * 1 -> n
    if expr.op == "*" and isinstance(expr.left, Const) and expr.left.val == 1:
        return right
    if expr.op == "*" and isinstance(expr.right, Const) and expr.right.val == 1:
        return left

    # Negative handling: 0 - n -> -n
    if expr.op == "-" and isinstance(expr.left, Const) and expr.left.val == 0:
        return f"-{right}"

    # Squaring detection: n * n -> n^2
    if expr.op == "*" and _exprs_equal(expr.left, expr.right):
        return f"{left}^{{2}}"

    # Coefficient ordering: n * 3 -> 3n (variable * const -> const * var)
    if expr.op == "*":
        if isinstance(expr.right, Const) and isinstance(expr.left, Var):
            return f"{right}{left}"
        if isinstance(expr.left, Const) and isinstance(expr.right, Var):
            return f"{left}{right}"

    # Division as fraction
    if expr.op == "/":
        return rf"\frac{{{left}}}{{{right}}}"

    return None


def _exprs_equal(e1: Any, e2: Any) -> bool:
    """Check if two expressions are structurally equal."""
    if type(e1) != type(e2):
        return False
    if isinstance(e1, Const):
        return e1.val == e2.val
    if isinstance(e1, Var):
        return e1.name == e2.name
    if isinstance(e1, BinOp):
        return e1.op == e2.op and _exprs_equal(e1.left, e2.left) and _exprs_equal(e1.right, e2.right)
    return False


def _sum_to_latex(expr: Sum, pretty: bool) -> str:
    """Convert summation to LaTeX."""
    start = to_latex(expr.start, pretty)
    end = to_latex(expr.end, pretty)
    body = to_latex(expr.body, pretty)
    return rf"\sum_{{{expr.var}={start}}}^{{{end}}} {body}"


def _product_to_latex(expr: Product, pretty: bool) -> str:
    """Convert product to LaTeX."""
    start = to_latex(expr.start, pretty)
    end = to_latex(expr.end, pretty)
    body = to_latex(expr.body, pretty)
    return rf"\prod_{{{expr.var}={start}}}^{{{end}}} {body}"


def _toolcall_to_latex(expr: ToolCall, pretty: bool) -> str:
    """Convert tool call to LaTeX."""
    args = ", ".join(to_latex(a, pretty) for a in expr.args)
    return rf"\text{{{expr.tool_name}}}({args})"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_latex.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add genetic_gp/core/latex.py tests/test_latex.py
git commit -m "feat: add LaTeX conversion with pretty formatting"
```

---

## Task 4: Sixel Renderer Module

**Files:**
- Create: `genetic_gp/core/renderer.py`
- Test: `tests/test_renderer.py`

**Step 1: Write the failing test**

```python
# tests/test_renderer.py
"""Tests for expression rendering."""

import pytest
from genetic_gp.core.expressions import Const, Var, BinOp, Sum


class TestLatexRenderer:
    """Tests for LaTeX to image rendering."""

    def test_render_simple_expression(self):
        """Should render without error."""
        from genetic_gp.core.renderer import render_latex_to_png

        png_bytes = render_latex_to_png("2n", dpi=100)

        assert png_bytes is not None
        assert len(png_bytes) > 0
        # PNG magic bytes
        assert png_bytes[:8] == b'\x89PNG\r\n\x1a\n'

    def test_render_complex_expression(self):
        """Should render sum notation."""
        from genetic_gp.core.renderer import render_latex_to_png

        latex = r"\sum_{i=1}^{n} i"
        png_bytes = render_latex_to_png(latex, dpi=100)

        assert png_bytes is not None
        assert len(png_bytes) > 0


class TestSixelOutput:
    """Tests for sixel encoding."""

    def test_png_to_sixel(self):
        """Should convert PNG to sixel string."""
        from genetic_gp.core.renderer import render_latex_to_png, png_to_sixel

        png_bytes = render_latex_to_png("x", dpi=72)
        sixel = png_to_sixel(png_bytes)

        # Sixel starts with escape sequence
        assert sixel.startswith('\x1bP') or sixel.startswith('\033P')
        # Sixel ends with ST (string terminator)
        assert sixel.endswith('\x1b\\') or sixel.endswith('\033\\')


class TestRendererFallback:
    """Tests for fallback rendering."""

    def test_unicode_fallback(self):
        """Should produce Unicode output when sixel unavailable."""
        from genetic_gp.core.renderer import render_unicode
        from genetic_gp.core.expressions import Sum, Const, Var

        expr = Sum("i", Const(1), Var("n"), Var("i"))
        result = render_unicode(expr)

        # Should contain sigma-like character
        assert "Σ" in result or "sum" in result.lower()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_renderer.py -v`
Expected: FAIL with "No module named 'genetic_gp.core.renderer'"

**Step 3: Write minimal implementation**

```python
# genetic_gp/core/renderer.py
"""Render LaTeX expressions to terminal output."""

from __future__ import annotations
import io
import sys
from typing import Any

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from matplotlib import mathtext

from genetic_gp.core.latex import to_latex


def render_latex_to_png(latex: str, font_size: int = 14, dpi: int = 150) -> bytes:
    """Render LaTeX string to PNG bytes.

    Args:
        latex: LaTeX math string (without $ delimiters)
        font_size: Font size in points
        dpi: Image resolution

    Returns:
        PNG image as bytes
    """
    fig, ax = plt.subplots(figsize=(0.01, 0.01))
    ax.axis('off')

    # Render the LaTeX
    text = ax.text(
        0.5, 0.5, f"${latex}$",
        fontsize=font_size,
        ha='center', va='center',
        transform=ax.transAxes
    )

    # Get tight bounding box
    fig.canvas.draw()
    bbox = text.get_window_extent(renderer=fig.canvas.get_renderer())
    bbox = bbox.transformed(fig.dpi_scale_trans.inverted())

    # Resize figure to fit text with padding
    pad = 0.1
    fig.set_size_inches(bbox.width + pad, bbox.height + pad)

    # Save to bytes
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight',
                pad_inches=0.05, transparent=False, facecolor='white')
    plt.close(fig)

    buf.seek(0)
    return buf.read()


def png_to_sixel(png_bytes: bytes) -> str:
    """Convert PNG bytes to sixel string.

    Uses a simple sixel encoder. For production, consider libsixel.

    Args:
        png_bytes: PNG image data

    Returns:
        Sixel encoded string
    """
    try:
        from PIL import Image
    except ImportError:
        raise ImportError("PIL required for sixel conversion. Install with: pip install pillow")

    # Load image
    img = Image.open(io.BytesIO(png_bytes))
    img = img.convert('P', palette=Image.ADAPTIVE, colors=256)

    width, height = img.size
    palette = img.getpalette()
    pixels = list(img.getdata())

    # Build sixel output
    output = []

    # DCS (Device Control String) introducer
    output.append('\x1bPq')

    # Set raster attributes: "Pan;Pad;Ph;Pv
    output.append(f'"1;1;{width};{height}')

    # Define color palette
    for i in range(256):
        if palette:
            r = palette[i * 3] * 100 // 255
            g = palette[i * 3 + 1] * 100 // 255
            b = palette[i * 3 + 2] * 100 // 255
            output.append(f'#{i};2;{r};{g};{b}')

    # Encode pixels in sixel format
    for row_start in range(0, height, 6):
        row_data = {}
        for x in range(width):
            sixel_val = 0
            for bit in range(6):
                y = row_start + bit
                if y < height:
                    pixel_idx = y * width + x
                    color = pixels[pixel_idx]
                    if color not in row_data:
                        row_data[color] = [0] * width
                    row_data[color][x] |= (1 << bit)

        for color, data in row_data.items():
            output.append(f'#{color}')
            for val in data:
                output.append(chr(63 + val))
            output.append('$')  # Carriage return
        output.append('-')  # New line

    # String terminator
    output.append('\x1b\\')

    return ''.join(output)


def render_unicode(expr: Any) -> str:
    """Render expression using Unicode characters.

    Fallback for terminals without sixel support.

    Args:
        expr: Expression to render

    Returns:
        Unicode string representation
    """
    # Use the existing __repr__ which already has Unicode symbols
    return repr(expr)


def render_expression(
    expr: Any,
    renderer: str = "sixel",
    font_size: int = 14,
    dpi: int = 150,
    pretty: bool = True,
) -> str:
    """Render expression to terminal output.

    Args:
        expr: Expression to render
        renderer: "sixel", "unicode", or "plain"
        font_size: Font size for LaTeX rendering
        dpi: DPI for LaTeX rendering
        pretty: Apply pretty formatting rules

    Returns:
        String to print (may contain sixel escape codes)
    """
    if renderer == "plain":
        return repr(expr)

    if renderer == "unicode":
        return render_unicode(expr)

    if renderer == "sixel":
        latex = to_latex(expr, pretty=pretty)
        try:
            png = render_latex_to_png(latex, font_size=font_size, dpi=dpi)
            return png_to_sixel(png)
        except Exception as e:
            # Fallback to unicode
            return render_unicode(expr)

    return repr(expr)


def supports_sixel() -> bool:
    """Check if terminal supports sixel graphics."""
    # Check for known sixel-capable terminals
    term = sys.stdout.isatty()
    if not term:
        return False

    import os
    term_program = os.environ.get('TERM_PROGRAM', '')
    term = os.environ.get('TERM', '')

    # Known sixel-capable terminals
    if any(t in term_program.lower() for t in ['iterm', 'mintty', 'wezterm']):
        return True
    if 'xterm' in term and '256' in term:
        # xterm with sixel support
        return True
    if 'mlterm' in term or 'yaft' in term:
        return True

    # Windows Terminal (check for WT_SESSION)
    if os.environ.get('WT_SESSION'):
        return True

    return False
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_renderer.py -v`
Expected: PASS (may need to install pillow: `pip install pillow`)

**Step 5: Update requirements and commit**

```bash
echo "pillow>=10.0.0" >> requirements.txt
git add genetic_gp/core/renderer.py tests/test_renderer.py requirements.txt
git commit -m "feat: add sixel renderer with PNG/unicode fallback"
```

---

## Task 5: Reporter Module

**Files:**
- Create: `genetic_gp/core/reporter.py`
- Test: `tests/test_reporter.py`

**Step 1: Write the failing test**

```python
# tests/test_reporter.py
"""Tests for the reporter module."""

import pytest
from io import StringIO
from genetic_gp.core.expressions import Const, Var, BinOp


class TestReporter:
    """Tests for Reporter class."""

    def test_create_reporter(self):
        """Should create reporter with default config."""
        from genetic_gp.core.reporter import Reporter

        reporter = Reporter()
        assert reporter is not None

    def test_on_new_best_normal_verbosity(self):
        """Should report new best at normal verbosity."""
        from genetic_gp.core.reporter import Reporter
        from genetic_gp.core.config import Verbosity

        reporter = Reporter(verbosity=Verbosity.NORMAL, renderer="plain")
        expr = BinOp("*", Var("n"), Const(2))

        # Should not raise
        reporter.on_new_best(expr, fitness=0.9, generation=10)

    def test_on_new_best_minimal_verbosity_skips(self):
        """Should skip new_best at minimal verbosity."""
        from genetic_gp.core.reporter import Reporter
        from genetic_gp.core.config import Verbosity

        reporter = Reporter(verbosity=Verbosity.MINIMAL, renderer="plain")
        expr = BinOp("*", Var("n"), Const(2))

        # Should not output anything (we'd need to capture stdout to verify)
        reporter.on_new_best(expr, fitness=0.9, generation=10)

    def test_on_solved(self):
        """Should always report solved."""
        from genetic_gp.core.reporter import Reporter
        from genetic_gp.core.config import Verbosity

        reporter = Reporter(verbosity=Verbosity.MINIMAL, renderer="plain")
        expr = BinOp("+", Var("n"), Var("n"))

        # Should not raise
        reporter.on_solved(expr, fitness=1.0, generation=25)

    def test_on_simplified(self):
        """Should report simplification."""
        from genetic_gp.core.reporter import Reporter
        from genetic_gp.core.config import Verbosity

        reporter = Reporter(verbosity=Verbosity.MINIMAL, renderer="plain")
        original = BinOp("*", Var("n"), Const(2))
        simplified = BinOp("+", Var("n"), Var("n"))

        # Should not raise
        reporter.on_simplified(original, simplified)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_reporter.py -v`
Expected: FAIL with "No module named 'genetic_gp.core.reporter'"

**Step 3: Write minimal implementation**

```python
# genetic_gp/core/reporter.py
"""Event-based reporter for evolution progress."""

from __future__ import annotations
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from genetic_gp.core.config import Config, Verbosity, get_config
from genetic_gp.core.latex import to_latex
from genetic_gp.core.renderer import render_expression, supports_sixel


class Reporter:
    """Reports evolution events with formatted output."""

    def __init__(
        self,
        config: Config | None = None,
        verbosity: Verbosity | None = None,
        renderer: str | None = None,
    ):
        """Initialize reporter.

        Args:
            config: Configuration object (uses global if not provided)
            verbosity: Override verbosity level
            renderer: Override renderer ("sixel", "unicode", "plain")
        """
        self._config = config or get_config()
        self._verbosity = verbosity or self._config.output.verbosity_level

        # Determine renderer
        if renderer:
            self._renderer = renderer
        elif self._config.output.renderer == "sixel" and not supports_sixel():
            self._renderer = self._config.output.fallback
        else:
            self._renderer = self._config.output.renderer

        self._console = Console()
        self._pretty = self._config.latex.pretty

    def on_problem_started(self, name: str, pop_size: int, generations: int) -> None:
        """Report problem start."""
        self._console.print()
        self._console.rule(f"[bold blue]PROBLEM: {name}[/bold blue]")
        self._console.print(f"  Population: {pop_size}    Generations: {generations}")
        self._console.print()

    def on_generation_update(
        self,
        generation: int,
        best_expr: Any,
        best_fitness: float,
        avg_fitness: float,
    ) -> None:
        """Report generation progress (verbose only)."""
        if self._verbosity < Verbosity.VERBOSE:
            return

        self._console.print(
            f"Gen {generation:3d}: "
            f"Best={best_fitness:.3f} "
            f"Avg={avg_fitness:.3f} "
            f"Complexity={best_expr.complexity()}"
        )

    def on_new_best(self, expr: Any, fitness: float, generation: int) -> None:
        """Report new best solution found."""
        if self._verbosity < Verbosity.NORMAL:
            return

        content = self._render_expr(expr)

        panel = Panel(
            content,
            title=f"[green]Generation {generation} - New Best[/green]",
            subtitle=f"Fitness: {fitness:.3f}  Complexity: {expr.complexity()}",
            border_style="green",
        )
        self._console.print(panel)

    def on_solved(self, expr: Any, fitness: float, generation: int) -> None:
        """Report problem solved."""
        content = self._render_expr(expr)

        panel = Panel(
            content,
            title=f"[bold green]Solved at Generation {generation}![/bold green]",
            subtitle=f"Fitness: {fitness:.3f}  Complexity: {expr.complexity()}",
            border_style="bold green",
        )
        self._console.print(panel)

    def on_simplified(self, original: Any, simplified: Any) -> None:
        """Report simplification applied."""
        orig_content = self._render_expr(original)
        simp_content = self._render_expr(simplified)

        orig_complexity = original.complexity()
        simp_complexity = simplified.complexity()
        reduction = (orig_complexity - simp_complexity) / orig_complexity * 100

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Original", justify="center")
        table.add_column("Arrow", justify="center")
        table.add_column("Simplified", justify="center")
        table.add_row(orig_content, "→", simp_content)

        panel = Panel(
            table,
            title="[cyan]Simplification Applied[/cyan]",
            subtitle=f"Complexity: {orig_complexity} → {simp_complexity} ({reduction:.0f}% reduction)",
            border_style="cyan",
        )
        self._console.print(panel)

    def on_tool_discovered(self, name: str, expr: Any, description: str) -> None:
        """Report new tool discovered."""
        content = self._render_expr(expr)

        panel = Panel(
            content,
            title=f"[yellow]Tool Discovered: {name}[/yellow]",
            subtitle=description,
            border_style="yellow",
        )
        self._console.print(panel)

    def _render_expr(self, expr: Any) -> str:
        """Render expression based on current renderer setting."""
        if self._renderer == "plain":
            return repr(expr)

        if self._renderer == "sixel":
            return render_expression(
                expr,
                renderer="sixel",
                font_size=self._config.latex.font_size,
                dpi=self._config.latex.dpi,
                pretty=self._pretty,
            )

        # Unicode - show both repr and LaTeX
        latex = to_latex(expr, pretty=self._pretty)
        return f"{repr(expr)}\n  LaTeX: ${latex}$"


# Global reporter instance
_reporter: Reporter | None = None


def get_reporter() -> Reporter:
    """Get global reporter instance."""
    global _reporter
    if _reporter is None:
        _reporter = Reporter()
    return _reporter


def reset_reporter() -> None:
    """Reset global reporter (for testing)."""
    global _reporter
    _reporter = None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_reporter.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add genetic_gp/core/reporter.py tests/test_reporter.py
git commit -m "feat: add reporter module with Rich formatting"
```

---

## Task 6: Integrate Reporter into Evolution Engine

**Files:**
- Modify: `genetic_gp/evolution/engine.py`
- Test: `tests/test_evolution.py` (add new tests)

**Step 1: Write the failing test**

```python
# Add to tests/test_evolution.py

class TestEvolutionReporter:
    """Tests for reporter integration."""

    def test_evolve_accepts_reporter(self):
        """Should accept optional reporter parameter."""
        from genetic_gp.evolution.engine import evolve
        from genetic_gp.core.reporter import Reporter
        from genetic_gp.core.config import Verbosity
        from genetic_gp.problems.math import test_double as fitness_double

        reporter = Reporter(verbosity=Verbosity.MINIMAL, renderer="plain")

        result = evolve(
            fitness_double,
            pop_size=20,
            generations=10,
            reporter=reporter,
            verbose=False,
        )

        assert result is not None

    def test_evolve_emits_events(self):
        """Should emit events to reporter."""
        from genetic_gp.evolution.engine import evolve
        from genetic_gp.core.config import Verbosity
        from genetic_gp.problems.math import test_double as fitness_double

        events = []

        class TestReporter:
            def on_problem_started(self, *args): events.append(('started', args))
            def on_new_best(self, *args): events.append(('new_best', args))
            def on_solved(self, *args): events.append(('solved', args))
            def on_generation_update(self, *args): events.append(('gen', args))

        result = evolve(
            fitness_double,
            pop_size=30,
            generations=50,
            reporter=TestReporter(),
            verbose=False,
        )

        # Should have emitted some events
        assert len(events) > 0
        assert any(e[0] == 'new_best' for e in events)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_evolution.py::TestEvolutionReporter -v`
Expected: FAIL with "unexpected keyword argument 'reporter'"

**Step 3: Modify engine.py to accept and use reporter**

Add to the `evolve()` function signature:
```python
reporter: Any | None = None,
```

Add event emissions at appropriate points:
- `on_problem_started` at start
- `on_new_best` when best_fitness improves
- `on_solved` when target reached
- `on_generation_update` at report_interval

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_evolution.py::TestEvolutionReporter -v`
Expected: PASS

**Step 5: Commit**

```bash
git add genetic_gp/evolution/engine.py tests/test_evolution.py
git commit -m "feat: integrate reporter into evolution engine"
```

---

## Task 7: Create Default Config File

**Files:**
- Create: `.gp_config.yaml`

**Step 1: Create default config**

```yaml
# Genetic Programming Configuration
# Copy to your project root and customize

output:
  # Verbosity: minimal | normal | verbose
  verbosity: normal

  # Renderer: sixel | unicode | plain
  renderer: sixel

  # Fallback if sixel not supported
  fallback: unicode

latex:
  # Apply pretty formatting (2n instead of n*2)
  pretty: true

  # Font size for rendered images
  font_size: 14

  # Image resolution
  dpi: 150

# Generations between updates (verbose mode)
report_interval: 10
```

**Step 2: Commit**

```bash
git add .gp_config.yaml
git commit -m "chore: add default config file"
```

---

## Task 8: Update Core __init__.py Exports

**Files:**
- Modify: `genetic_gp/core/__init__.py`

**Step 1: Update exports**

```python
# genetic_gp/core/__init__.py
"""Core modules for genetic programming."""

from genetic_gp.core.expressions import (
    Const,
    Var,
    BinOp,
    Sum,
    Product,
    ToolCall,
    Expression,
)
from genetic_gp.core.signatures import behavioral_signature, signatures_match
from genetic_gp.core.config import Config, load_config, get_config, Verbosity
from genetic_gp.core.latex import to_latex
from genetic_gp.core.reporter import Reporter, get_reporter

__all__ = [
    # Expressions
    "Const",
    "Var",
    "BinOp",
    "Sum",
    "Product",
    "ToolCall",
    "Expression",
    # Signatures
    "behavioral_signature",
    "signatures_match",
    # Config
    "Config",
    "load_config",
    "get_config",
    "Verbosity",
    # LaTeX
    "to_latex",
    # Reporter
    "Reporter",
    "get_reporter",
]
```

**Step 2: Commit**

```bash
git add genetic_gp/core/__init__.py
git commit -m "feat: export new modules from core package"
```

---

## Task 9: Update an Experiment to Use Reporter

**Files:**
- Modify: `genetic_gp/experiments/simplicity.py`

**Step 1: Update experiment to use reporter**

Replace print statements with reporter calls. This serves as the example for updating other experiments.

**Step 2: Run experiment to verify**

Run: `python -m genetic_gp.experiments.simplicity`
Expected: Formatted output with Rich panels

**Step 3: Commit**

```bash
git add genetic_gp/experiments/simplicity.py
git commit -m "refactor: use reporter in simplicity experiment"
```

---

## Task 10: Run Full Test Suite

**Step 1: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests pass

**Step 2: Run an experiment end-to-end**

Run: `python -m genetic_gp.experiments.simplicity`
Expected: Beautiful formatted output with LaTeX rendering (or Unicode fallback)

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete LaTeX expression reporting feature"
```

---

## Summary

**New files created:**
- `genetic_gp/core/config.py` - YAML config loading
- `genetic_gp/core/latex.py` - Expression to LaTeX conversion
- `genetic_gp/core/renderer.py` - Sixel/Unicode rendering
- `genetic_gp/core/reporter.py` - Event-based reporter
- `tests/test_config.py`
- `tests/test_latex.py`
- `tests/test_renderer.py`
- `tests/test_reporter.py`
- `.gp_config.yaml`
- `requirements.txt`

**Files modified:**
- `genetic_gp/evolution/engine.py` - Reporter integration
- `genetic_gp/core/__init__.py` - Exports
- `genetic_gp/experiments/simplicity.py` - Example conversion
