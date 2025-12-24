"""Expression rendering to LaTeX, PNG, and Sixel formats."""

import io
import os
import shutil
import subprocess
from typing import Any, Optional

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from PIL import Image

# Enable real LaTeX rendering if available
plt.rcParams['text.usetex'] = shutil.which('latex') is not None
plt.rcParams['font.family'] = 'serif'

from genetic_gp.core.latex import to_latex


def render_latex_to_png(latex: str, font_size: int = 14, dpi: int = 150) -> bytes:
    """
    Render LaTeX string to PNG bytes using matplotlib.

    Args:
        latex: LaTeX string to render (without $ delimiters)
        font_size: Font size in points
        dpi: Resolution in dots per inch

    Returns:
        PNG image as bytes
    """
    # Create a figure with minimal padding
    fig = plt.figure(figsize=(0.01, 0.01))
    fig.text(0, 0, f'${latex}$', fontsize=font_size)

    # Save to buffer with white background (transparent breaks sixel)
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight', pad_inches=0.1,
                facecolor='white', edgecolor='none')
    plt.close(fig)

    buf.seek(0)
    return buf.read()


def png_to_sixel(png_bytes: bytes) -> str:
    """
    Convert PNG bytes to sixel format string.

    Args:
        png_bytes: PNG image data

    Returns:
        Sixel format string with escape sequences
    """
    # Load PNG with PIL
    img = Image.open(io.BytesIO(png_bytes))

    # Convert to RGB if necessary
    if img.mode != 'RGB':
        img = img.convert('RGB')

    # Save to temporary buffer for ImageMagick
    temp_png = io.BytesIO()
    img.save(temp_png, format='PNG')
    temp_png.seek(0)

    # Use ImageMagick convert to generate sixel
    try:
        result = subprocess.run(
            ['convert', '-', 'sixel:-'],
            input=temp_png.read(),
            capture_output=True,
            check=True
        )
        return result.stdout.decode('latin-1')
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback: use libsixel if available
        try:
            result = subprocess.run(
                ['img2sixel'],
                input=temp_png.getvalue(),
                capture_output=True,
                check=True
            )
            return result.stdout.decode('latin-1')
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Manual sixel encoding as last resort
            return _encode_sixel_manual(img)


def _encode_sixel_manual(img: Image.Image) -> str:
    """
    Manually encode image to sixel format.

    This is a simple sixel encoder that works for basic images.

    Args:
        img: PIL Image object

    Returns:
        Sixel format string
    """
    # Start sixel sequence
    sixel = '\x1bPq'  # ESC P q (enter sixel mode)

    # Simple palette setup (using first 16 colors)
    # For now, just create a basic grayscale palette
    for i in range(16):
        level = int(i * 100 / 15)
        sixel += f'#{i};2;{level};{level};{level}'

    # Resize image to reasonable size for terminal
    max_width = 400
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height))

    # Convert to grayscale for simple encoding
    img_gray = img.convert('L')
    pixels = img_gray.load()

    width, height = img_gray.size

    # Encode in bands of 6 pixels tall (sixel format)
    for band_y in range(0, height, 6):
        sixel += '$'  # Carriage return

        for x in range(width):
            # Gather 6 vertical pixels
            sixel_char = 0
            for bit in range(6):
                y = band_y + bit
                if y < height:
                    # Map pixel value to color index
                    pixel_val = pixels[x, y]
                    if pixel_val > 128:  # Simple threshold
                        sixel_char |= (1 << bit)

            # Encode as sixel character (add 63 to value)
            if sixel_char > 0:
                sixel += chr(sixel_char + 63)
            else:
                sixel += '?'  # Sixel character for 0

        sixel += '-'  # Newline (next sixel band)

    # End sixel sequence
    sixel += '\x1b\\'  # ESC \ (exit sixel mode)

    return sixel


def render_unicode(expr: Any, pretty: bool = True) -> str:
    """
    Render expression as pretty Unicode math text.

    Uses Unicode superscripts, subscripts, and math symbols for
    native terminal display without images.

    Args:
        expr: Expression object
        pretty: Apply pretty formatting

    Returns:
        Unicode string representation
    """
    from genetic_gp.core.expressions import Const, Var, BinOp, Sum, Product, PrimitiveCall

    if not pretty:
        return repr(expr)

    return _expr_to_unicode(expr)


# Unicode superscript digits
_SUPERSCRIPTS = {'0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
                 '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
                 'n': 'ⁿ', 'k': 'ᵏ', 'i': 'ⁱ', 'j': 'ʲ', '-': '⁻', '.': '·'}

# Unicode subscript digits
_SUBSCRIPTS = {'0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
               '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
               'n': 'ₙ', 'k': 'ₖ', 'i': 'ᵢ', 'j': 'ⱼ', '=': '₌'}


def _to_superscript(s: str) -> str:
    """Convert string to Unicode superscript."""
    return ''.join(_SUPERSCRIPTS.get(c, c) for c in str(s))


def _to_subscript(s: str) -> str:
    """Convert string to Unicode subscript."""
    return ''.join(_SUBSCRIPTS.get(c, c) for c in str(s))


def _format_number(val: float) -> str:
    """Format a number for display."""
    if val == int(val):
        return str(int(val))
    return str(round(val, 2))


def _expr_to_unicode(expr: Any, parent_op: str = None) -> str:
    """Convert expression to pretty Unicode string."""
    from genetic_gp.core.expressions import Const, Var, BinOp, Sum, Product, PrimitiveCall

    if isinstance(expr, Const):
        return _format_number(expr.val)

    elif isinstance(expr, Var):
        return expr.name

    elif isinstance(expr, BinOp):
        left = _expr_to_unicode(expr.left, expr.op)
        right = _expr_to_unicode(expr.right, expr.op)

        if expr.op == '+':
            result = f"{left} + {right}"
        elif expr.op == '-':
            result = f"{left} − {right}"  # Use proper minus sign
        elif expr.op == '*':
            # Pretty multiplication
            left_is_const = isinstance(expr.left, Const)
            right_is_var = isinstance(expr.right, Var)
            left_is_var = isinstance(expr.left, Var)
            right_is_const = isinstance(expr.right, Const)

            # n * n -> n²
            if left_is_var and isinstance(expr.right, Var) and expr.left.name == expr.right.name:
                result = f"{left}²"
            # 2 * n -> 2n or n * 2 -> 2n
            elif left_is_const and right_is_var:
                result = f"{left}{right}"
            elif left_is_var and right_is_const:
                result = f"{right}{left}"
            else:
                result = f"{left}·{right}"
        elif expr.op == '/':
            result = f"{left}/{right}"
        elif expr.op == '^':
            # Use superscript for exponent
            exp_str = _expr_to_unicode(expr.right)
            if len(exp_str) <= 3 and all(c in _SUPERSCRIPTS for c in exp_str):
                result = f"{left}{_to_superscript(exp_str)}"
            else:
                result = f"{left}^{right}"
        else:
            result = f"{left} {expr.op} {right}"

        # Add parentheses if needed
        if parent_op in ['*', '^'] and expr.op in ['+', '-']:
            result = f"({result})"

        return result

    elif isinstance(expr, Sum):
        var = expr.var
        start = _expr_to_unicode(expr.start)
        end = _expr_to_unicode(expr.end)
        body = _expr_to_unicode(expr.body)
        # Σ with subscript bounds
        return f"Σ{_to_subscript(var + '=' + start)}{_to_superscript(end)}[{body}]"

    elif isinstance(expr, Product):
        var = expr.var
        start = _expr_to_unicode(expr.start)
        end = _expr_to_unicode(expr.end)
        body = _expr_to_unicode(expr.body)
        # ∏ with subscript bounds
        return f"∏{_to_subscript(var + '=' + start)}{_to_superscript(end)}[{body}]"

    elif isinstance(expr, PrimitiveCall):
        arg = _expr_to_unicode(expr.arg)
        return f"{expr.primitive_name}({arg})"

    return repr(expr)


def supports_sixel() -> bool:
    """
    Check if terminal supports sixel graphics.

    Returns:
        True if sixel is supported
    """
    # Check TERM environment variable
    term = os.environ.get('TERM', '')
    if 'sixel' in term.lower():
        return True

    # Check if we're in Windows Terminal (WT_SESSION is set)
    if os.environ.get('WT_SESSION'):
        return True

    # Check if we're in a known sixel-capable terminal
    term_program = os.environ.get('TERM_PROGRAM', '')
    if term_program in ['mlterm', 'yaft', 'mintty']:
        return True

    # Could also check terminfo database, but this is a simple heuristic
    return False


def render_expression(
    expr: Any,
    renderer: str = 'auto',
    font_size: int = 14,
    dpi: int = 150,
    pretty: bool = True
) -> str:
    """
    Render expression using specified renderer.

    Args:
        expr: Expression object to render
        renderer: Rendering mode ('auto', 'sixel', 'unicode')
        font_size: Font size for LaTeX rendering
        dpi: Resolution for LaTeX rendering
        pretty: Whether to use pretty rendering (vs plain text)

    Returns:
        Rendered string (may include escape sequences for sixel)
    """
    if renderer == 'auto':
        renderer = 'sixel' if supports_sixel() else 'unicode'

    if not pretty or renderer == 'unicode':
        return render_unicode(expr)

    if renderer == 'sixel':
        # Convert expression to LaTeX
        latex = to_latex(expr, pretty=pretty)

        try:
            png_bytes = render_latex_to_png(latex, font_size=font_size, dpi=dpi)
            return png_to_sixel(png_bytes)
        except Exception:
            # Fall back to unicode on any error
            return render_unicode(expr)

    return render_unicode(expr)
