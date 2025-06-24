"""
Wrapping Paper and Tablerunner PDF Generator
Generates tiled pattern PDFs for wrapping paper in 6ft and 15ft lengths
and tablerunners in 15ft and 30ft lengths

This script replaces the older pdf.py / pdfmaker.py utilities and introduces barcode
rendering plus several safety checks. All key paths (input image, footer, output
folder) can be supplied via command-line flags so the same binary works across
workstations. Default values fall back to the global `config.py` module when
available.

Usage examples
--------------
python wrapping_paper_pdf_generator.py -i .\Download\AA605282.png
python wrapping_paper_pdf_generator.py -i img1.png img2.png -o .\Output -f .\Footer.pdf
python wrapping_paper_pdf_generator.py -i img1.png --tablerunner -o .\Output\Tablerunner

Required third-party packages
----------------------------
Pillow, PyMuPDF, python-barcode
Install them with::

    pip install -r requirements.txt

"""

from __future__ import annotations

import argparse
import io
import os
import sys
from datetime import datetime
from typing import List

# Ensure we can print Unicode characters even when stdout is captured by a
# Windows process that defaults to a legacy codepage (e.g. cp1252).  By
# re-encoding the stream to UTF-8 and setting *errors='replace'* we avoid
# UnicodeEncodeError while still preserving most output.
import sys as _sys

# The reconfigure API exists on Python ≥3.7.  If unavailable we silently skip.
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Third-party imports — handled with runtime checks so the script fails fast with
# an instructive message if a dependency is missing.
try:
    import fitz  # PyMuPDF
except ImportError as exc:  # pragma: no cover – runtime dependency guard
    sys.exit("[ERROR] PyMuPDF (fitz) is not installed. Run `pip install PyMuPDF`.\n")

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    sys.exit("[ERROR] Pillow is not installed. Run `pip install Pillow`.\n")

try:
    from barcode import Code128
    from barcode.writer import ImageWriter
except ImportError:  # pragma: no cover
    sys.exit("[ERROR] python-barcode is not installed. Run `pip install python-barcode`.\n")

# Attempt to pull shared dimensions / folders from the project-level config.py.
try:
    import config  # type: ignore

    # Wrapping paper dimensions (30" width)
    TEMPLATE_6FT_WIDTH: float = getattr(config, "TEMPLATE_6FT_WIDTH", 2171.53)
    TEMPLATE_6FT_HEIGHT: float = getattr(config, "TEMPLATE_6FT_HEIGHT", 5285.94)
    TEMPLATE_15FT_WIDTH: float = getattr(config, "TEMPLATE_15FT_WIDTH", 2171.53)
    TEMPLATE_15FT_HEIGHT: float = getattr(config, "TEMPLATE_15FT_HEIGHT", 13061.90)

    # Tablerunner dimensions (20" width)
    TABLERUNNER_15FT_WIDTH: float = getattr(config, "TABLERUNNER_15FT_WIDTH", 1447.69)
    TABLERUNNER_15FT_HEIGHT: float = getattr(config, "TABLERUNNER_15FT_HEIGHT", 13061.90)
    TABLERUNNER_30FT_WIDTH: float = getattr(config, "TABLERUNNER_30FT_WIDTH", 1447.69)
    TABLERUNNER_30FT_HEIGHT: float = getattr(config, "TABLERUNNER_30FT_HEIGHT", 26123.80)

    DEFAULT_OUTPUT_DIR = getattr(config, "OUTPUT_BASE_FOLDER", os.path.join(os.getcwd(), "Output"))
    DEFAULT_TABLERUNNER_DIR = getattr(config, "TABLERUNNER_FOLDER", os.path.join(os.getcwd(), "Output", "Tablerunner"))
    DEFAULT_FOOTER_PATH = os.path.join(getattr(config, "SCRIPTS_FOLDER", os.getcwd()), "Footer.pdf")
except ModuleNotFoundError:
    # Fallback defaults when config.py is not present in python path
    # Wrapping paper dimensions (30" width = 30 * 72 points)
    TEMPLATE_6FT_WIDTH = 2171.53
    TEMPLATE_6FT_HEIGHT = 5285.94
    TEMPLATE_15FT_WIDTH = 2171.53
    TEMPLATE_15FT_HEIGHT = 13061.90

    # Tablerunner dimensions (20" width = 20 * 72 points)
    TABLERUNNER_15FT_WIDTH = 1447.69  # 20" in points
    TABLERUNNER_15FT_HEIGHT = 13061.90  # 15 ft in points
    TABLERUNNER_30FT_WIDTH = 1447.69  # 20" in points
    TABLERUNNER_30FT_HEIGHT = 26123.80  # 30 ft in points

    DEFAULT_OUTPUT_DIR = os.path.join(os.getcwd(), "Output")
    DEFAULT_TABLERUNNER_DIR = os.path.join(os.getcwd(), "Output", "Tablerunner")
    DEFAULT_FOOTER_PATH = os.path.join(os.getcwd(), "Footer.pdf")

DPI = 300
HORIZONTAL_REPEATS = 6  # for 30" width rolls
TABLERUNNER_HORIZONTAL_REPEATS = 4  # for 20" width runners

# ---------------------------------------------------------------------------
#   Replace *print* with a helper that strips non-ASCII characters
# ---------------------------------------------------------------------------
import builtins as _builtins  # noqa: E402  (placed early intentionally)

def _ascii_print(*args, **kwargs):
    """Proxy for *print* that silently removes any non-ASCII characters.

    This keeps console output compatible with legacy Windows codepages such as
    CP-1252 so we no longer hit *UnicodeEncodeError* when emojis or other
    Unicode symbols are present in log messages consumed by external
    processes.  Converting to pure ASCII avoids the need to touch every call
    site while still providing readable feedback (the symbols are simply
    omitted).
    """
    processed = [str(arg).encode("ascii", "ignore").decode("ascii") for arg in args]
    _builtins.print(*processed, **kwargs)

# Override the built-in *print* for this module only.
print = _ascii_print  # type: ignore  # noqa: A001

def generate_barcode(code_text: str, width_points: int = 250, height_points: int = 40) -> bytes | None:
    """Return a PNG byte stream containing a *cropped* Code128 barcode.

    The underlying generator can only suppress the human-readable text but still
    emits whitespace. The image is force-cropped to 50 % height to ensure the
    text region is removed completely before being resized to the requested
    physical dimensions (points → pixels for *DPI*).
    """
    try:
        writer = ImageWriter()
        writer.set_options(
            {
                "module_height": 18.0,
                "font_size": 0,
                "text_distance": 0,
                "quiet_zone": 1.0,
                "write_text": False,
            }
        )

        barcode_obj = Code128(code_text, writer=writer)
        buffer = io.BytesIO()
        barcode_obj.write(buffer)
        buffer.seek(0)

        barcode_img = Image.open(buffer)
        width, height = barcode_img.size
        crop_box = (0, 0, width, int(height * 0.50))  # top 50 %
        cropped = barcode_img.crop(crop_box)

        # Convert target size from *points* (1/72 inch) to *pixels*
        width_px = int(width_points * (DPI / 72))
        height_px = int(height_points * (DPI / 72))
        resized = cropped.resize((width_px, height_px), Image.Resampling.NEAREST)

        out_buffer = io.BytesIO()
        resized.save(out_buffer, format="PNG")
        out_buffer.seek(0)
        return out_buffer.getvalue()
    except Exception as exc:
        print(f"  ⚠ Error generating barcode: {exc}")
        return None


def create_tiled_image_pdf(
    output_pdf_path: str,
    image_path: str,
    template_width: float,
    template_height: float,
    dpi: int = DPI,
    horizontal_repeats: int = HORIZONTAL_REPEATS,
) -> bool:
    """Create a single-page PDF filled with the source image in a tile pattern."""

    try:
        print(f"  Creating tiled PDF: {os.path.basename(output_pdf_path)}")
        doc = fitz.open()
        page = doc.new_page(width=template_width, height=template_height)

        image = Image.open(image_path)
        tile_width = template_width / horizontal_repeats
        tile_height = tile_width / (image.width / image.height)

        tile_width_px = int(tile_width * (dpi / 72))
        tile_height_px = int(tile_height * (dpi / 72))
        resized = image.resize((tile_width_px, tile_height_px), Image.Resampling.LANCZOS)

        # Save temporary scaled image inside the output directory
        temp_scaled = os.path.join(os.path.dirname(output_pdf_path), "temp_scaled_image.png")
        resized.save(temp_scaled, "PNG", dpi=(dpi, dpi))

        y = 0
        tiles = 0
        while y < template_height:
            x = 0
            while x + tile_width <= template_width:
                rect = fitz.Rect(x, y, x + tile_width, y + tile_height)
                page.insert_image(rect, filename=temp_scaled)
                x += tile_width
                tiles += 1
            y += tile_height
        print(f"  Placed {tiles} tiles")

        doc.save(output_pdf_path)
        doc.close()
        os.remove(temp_scaled)
        print(f"  ✓ Tiled PDF saved: {output_pdf_path}")
        return True
    except Exception as exc:
        print(f"  ✗ Error creating tiled PDF: {exc}")
        return False


def overlay_footer_and_add_text(
    base_pdf_path: str,
    footer_path: str,
    output_pdf_path: str,
    template_width: float,
    template_height: float,
    pattern_name: str,
    roll_width: str,
    roll_length: str,
    barcode_text: str,
) -> bool:
    """Embed the footer, descriptive texts and a barcode onto *base_pdf_path*."""

    try:
        print("  Adding footer, text, and barcode…")

        base_doc = fitz.open(base_pdf_path)
        base_page = base_doc[0]

        footer_height = 100  # default when footer PDF missing
        if os.path.exists(footer_path):
            footer_doc = fitz.open(footer_path)
            footer_page = footer_doc[0]
            footer_rect_original = footer_page.rect
            scale = template_width / footer_rect_original.width
            footer_height = footer_rect_original.height * scale
            footer_rect = fitz.Rect(0, template_height - footer_height, template_width, template_height)
            base_page.show_pdf_page(footer_rect, footer_doc, 0)
            footer_doc.close()
            print("  ✓ Footer embedded at high quality")
        else:
            print(f"  ⚠ Footer not found at {footer_path}, using placeholder")
            placeholder = fitz.Rect(0, template_height - footer_height, template_width, template_height)
            base_page.draw_rect(placeholder, color=(0.95, 0.95, 0.95), fill=(0.95, 0.95, 0.95))

        # Determine if we are dealing with a 20" tablerunner or 30" wrapping paper
        is_tablerunner = template_width < 2000  # 20" vs 30" products

        if is_tablerunner:
            # 20" Tablerunner settings
            pattern_offset = 132  # fine-tuned right shift
            width_offset   = 115
            length_offset  = 115
            barcode_offset = 320
            font_size = 9
            barcode_width_pt  = 120
            barcode_height_pt = 30
            text_y_offsets = {
                "pattern": 15,
                "width":   26,
                "length":  37,
            }
        else:
            # 30" Wrapping-paper settings (original)
            pattern_offset = 195
            width_offset   = 177
            length_offset  = 170
            barcode_offset = 500
            font_size = 13
            barcode_width_pt  = 200
            barcode_height_pt = 50
            text_y_offsets = {
                "pattern": 21,
                "width":   38,
                "length":  54.5,
            }

        # Insert texts
        grey = (0.35, 0.35, 0.35)
        texts = [
            (pattern_name, (template_width - pattern_offset, template_height - footer_height + text_y_offsets["pattern"])),
            (roll_width,   (template_width - width_offset,   template_height - footer_height + text_y_offsets["width"])),
            (roll_length,  (template_width - length_offset,  template_height - footer_height + text_y_offsets["length"])),
        ]
        for text, pos in texts:
            base_page.insert_text(point=pos, text=text, fontsize=font_size, color=grey)

        # Barcode
        barcode_bytes = generate_barcode(barcode_text, barcode_width_pt, barcode_height_pt)
        if barcode_bytes:
            x = template_width - barcode_offset
            y = template_height - footer_height + 20
            rect = fitz.Rect(x, y, x + barcode_width_pt, y + barcode_height_pt)
            base_page.insert_image(rect, stream=barcode_bytes)
            print(f"  ✓ Added barcode: {barcode_text}")

        # Write out via temporary file then replace
        tmp = output_pdf_path.replace(".pdf", "_tmp.pdf")
        base_doc.save(tmp)
        base_doc.close()
        if os.path.exists(output_pdf_path):
            os.remove(output_pdf_path)
        os.rename(tmp, output_pdf_path)
        print("  ✓ Final PDF saved with footer, text, and barcode")
        return True
    except Exception as exc:
        print(f"  ✗ Error overlaying footer and adding text: {exc}")
        return False


# ---------------------------------------------------------------------------
#   Processing functions
# ---------------------------------------------------------------------------

def process_wrapping_paper(image_path: str, output_dir: str, footer_path: str) -> None:
    """Generate 6 ft and 15 ft wrapping-paper variants for a single input image."""
    if not os.path.exists(image_path):
        print(f"✗ Image file not found: {image_path}")
        return

    base_name = os.path.splitext(os.path.basename(image_path))[0]
    print(f"\n🖼 Processing wrapping paper: {base_name}")

    # 6 ft variant (barcode ending 06)
    print("\n📄 Generating 6ft wrapping paper…")
    barcode_6ft = f"{base_name}06"
    pdf6 = os.path.join(output_dir, f"{barcode_6ft}.pdf")
    if create_tiled_image_pdf(pdf6, image_path, TEMPLATE_6FT_WIDTH, TEMPLATE_6FT_HEIGHT):
        overlay_footer_and_add_text(
            pdf6,
            footer_path,
            pdf6,
            TEMPLATE_6FT_WIDTH,
            TEMPLATE_6FT_HEIGHT,
            base_name,
            "30'",
            "6'",
            barcode_6ft,
        )

    # 15 ft variant (barcode ending 15)
    print("\n📄 Generating 15ft wrapping paper…")
    barcode_15ft = f"{base_name}15"
    pdf15 = os.path.join(output_dir, f"{barcode_15ft}.pdf")
    if create_tiled_image_pdf(pdf15, image_path, TEMPLATE_15FT_WIDTH, TEMPLATE_15FT_HEIGHT):
        overlay_footer_and_add_text(
            pdf15,
            footer_path,
            pdf15,
            TEMPLATE_15FT_WIDTH,
            TEMPLATE_15FT_HEIGHT,
            base_name,
            "30'",
            "15'",
            barcode_15ft,
        )

    print(f"\n✓ Completed wrapping paper processing: {base_name}")


def process_tablerunner(image_path: str, output_dir: str, footer_path: str) -> None:
    """Generate 15 ft and 30 ft tablerunner variants for a single input image."""
    if not os.path.exists(image_path):
        print(f"✗ Image file not found: {image_path}")
        return

    base_name = os.path.splitext(os.path.basename(image_path))[0]
    print(f"\n🏃 Processing tablerunner: {base_name}")

    # 15 ft tablerunner (barcode ending 71)
    print("\n📄 Generating 15ft tablerunner…")
    barcode_15ft = f"{base_name}71"
    pdf15 = os.path.join(output_dir, f"{barcode_15ft}.pdf")
    if create_tiled_image_pdf(
        pdf15,
        image_path,
        TABLERUNNER_15FT_WIDTH,
        TABLERUNNER_15FT_HEIGHT,
        horizontal_repeats=TABLERUNNER_HORIZONTAL_REPEATS,
    ):
        overlay_footer_and_add_text(
            pdf15,
            footer_path,
            pdf15,
            TABLERUNNER_15FT_WIDTH,
            TABLERUNNER_15FT_HEIGHT,
            base_name,
            "20'",
            "15'",
            barcode_15ft,
        )

    # 30 ft tablerunner (barcode ending 72)
    print("\n📄 Generating 30ft tablerunner…")
    barcode_30ft = f"{base_name}72"
    pdf30 = os.path.join(output_dir, f"{barcode_30ft}.pdf")
    if create_tiled_image_pdf(
        pdf30,
        image_path,
        TABLERUNNER_30FT_WIDTH,
        TABLERUNNER_30FT_HEIGHT,
        horizontal_repeats=TABLERUNNER_HORIZONTAL_REPEATS,
    ):
        overlay_footer_and_add_text(
            pdf30,
            footer_path,
            pdf30,
            TABLERUNNER_30FT_WIDTH,
            TABLERUNNER_30FT_HEIGHT,
            base_name,
            "20'",
            "30'",
            barcode_30ft,
        )

    print(f"\n✓ Completed tablerunner processing: {base_name}")


def process_image(image_path: str, output_dir: str, footer_path: str, is_tablerunner: bool = False) -> None:
    """Dispatch to the correct processing routine based on *is_tablerunner*."""
    if is_tablerunner:
        process_tablerunner(image_path, output_dir, footer_path)
    else:
        process_wrapping_paper(image_path, output_dir, footer_path)


# ---------------------------------------------------------------------------
#   CLI
# ---------------------------------------------------------------------------

def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate 6ft/15ft wrapping-paper PDFs or 15ft/30ft tablerunner PDFs from images.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "images",
        nargs="+",
        help="Path(s) to the source PNG/JPG image(s).",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        help="Directory where the generated PDFs will be written.",
    )
    parser.add_argument(
        "-f",
        "--footer",
        default=DEFAULT_FOOTER_PATH,
        help="Path to Footer.pdf.",
    )
    parser.add_argument(
        "--tablerunner",
        action="store_true",
        help="Generate tablerunner PDFs (15ft/30ft, 20\" width) instead of wrapping paper PDFs (6ft/15ft, 30\" width).",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
#   Entry-point
# ---------------------------------------------------------------------------

def main(argv: List[str] | None = None) -> None:
    args = parse_args(argv)

    # Decide default output directory based on product type if not overridden
    if args.output_dir is None:
        args.output_dir = DEFAULT_TABLERUNNER_DIR if args.tablerunner else DEFAULT_OUTPUT_DIR

    # Ensure output directory exists early so errors are easier to spot.
    os.makedirs(args.output_dir, exist_ok=True)

    product_type = "TABLERUNNER" if args.tablerunner else "WRAPPING PAPER"
    print(f"🎁 {product_type} PDF GENERATOR")
    print("=" * 40)
    print(f"Output directory: {args.output_dir}")
    print(f"Footer: {args.footer}")
    if args.tablerunner:
        print(f"Horizontal repeats: {TABLERUNNER_HORIZONTAL_REPEATS}")
        print("Generating: 15ft and 30ft tablerunners (20\" width)")
        print("Barcode endings: 71 (15ft), 72 (30ft)")
    else:
        print(f"Horizontal repeats: {HORIZONTAL_REPEATS}")
        print("Generating: 6ft and 15ft wrapping paper (30\" width)")
        print("Barcode endings: 06 (6ft), 15 (15ft)")
    print("=" * 40)

    if not os.path.exists(args.footer):
        print(f"⚠ Warning: Footer not found at {args.footer}\n   A placeholder will be drawn instead.")

    for img in args.images:
        process_image(img, args.output_dir, args.footer, args.tablerunner)

    print(f"\n🎉 {product_type} PDF generation complete!")


if __name__ == "__main__":
    main() 