"""Expression rendering to LaTeX, PNG, and Sixel formats."""

import io
import os
import subprocess
from typing import Any, Optional

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from PIL import Image


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

    # Save to buffer
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight', pad_inches=0.1,
                transparent=True)
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


def render_unicode(expr: Any) -> str:
    """
    Render expression as Unicode text (fallback).

    Args:
        expr: Expression object

    Returns:
        Unicode string representation
    """
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

    # Check if we're in a known sixel-capable terminal
    term_program = os.environ.get('TERM_PROGRAM', '')
    if term_program in ['mlterm', 'yaft']:
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
        # Convert expression to LaTeX (assume it has __repr__ with Unicode)
        latex = repr(expr)

        # Replace Unicode with LaTeX equivalents
        latex = latex.replace('Σ', r'\sum')
        latex = latex.replace('∏', r'\prod')
        latex = latex.replace('..', r'\ldots')

        try:
            png_bytes = render_latex_to_png(latex, font_size=font_size, dpi=dpi)
            return png_to_sixel(png_bytes)
        except Exception:
            # Fall back to unicode on any error
            return render_unicode(expr)

    return render_unicode(expr)
