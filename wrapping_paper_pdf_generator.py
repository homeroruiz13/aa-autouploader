"""
Fixed Wrapping Paper and Tablerunner PDF Generator
Addresses image size limits to prevent decompression bomb errors

Key fixes:
1. Resize large images before processing
2. Add image size validation
3. Improved error handling for large files
4. Memory optimization for tile processing
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from datetime import datetime
from typing import List

# Ensure we can print Unicode characters
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Third-party imports with runtime checks
try:
    import fitz  # PyMuPDF
except ImportError as exc:
    sys.exit("[ERROR] PyMuPDF (fitz) is not installed. Run `pip install PyMuPDF`.\n")

try:
    from PIL import Image
    # Set PIL's image size limits to handle larger images safely
    Image.MAX_IMAGE_PIXELS = None  # Remove default limit
    MAX_SAFE_PIXELS = 150_000_000  # Our custom safe limit (150MP)
except ImportError:
    sys.exit("[ERROR] Pillow is not installed. Run `pip install Pillow`.\n")

try:
    from barcode import Code128
    from barcode.writer import ImageWriter
except ImportError:
    sys.exit("[ERROR] python-barcode is not installed. Run `pip install python-barcode`.\n")

# Configuration with fallbacks
try:
    import config
    TEMPLATE_6FT_WIDTH: float = getattr(config, "TEMPLATE_6FT_WIDTH", 2171.53)
    TEMPLATE_6FT_HEIGHT: float = getattr(config, "TEMPLATE_6FT_HEIGHT", 5285.94)
    TEMPLATE_15FT_WIDTH: float = getattr(config, "TEMPLATE_15FT_WIDTH", 2171.53)
    TEMPLATE_15FT_HEIGHT: float = getattr(config, "TEMPLATE_15FT_HEIGHT", 13061.90)
    TABLERUNNER_15FT_WIDTH: float = getattr(config, "TABLERUNNER_15FT_WIDTH", 1447.69)
    TABLERUNNER_15FT_HEIGHT: float = getattr(config, "TABLERUNNER_15FT_HEIGHT", 13061.90)
    TABLERUNNER_30FT_WIDTH: float = getattr(config, "TABLERUNNER_30FT_WIDTH", 1447.69)
    TABLERUNNER_30FT_HEIGHT: float = getattr(config, "TABLERUNNER_30FT_HEIGHT", 26123.80)
    DEFAULT_OUTPUT_DIR = getattr(config, "OUTPUT_BASE_FOLDER", os.path.join(os.getcwd(), "Output"))
    DEFAULT_TABLERUNNER_DIR = getattr(config, "TABLERUNNER_FOLDER", os.path.join(os.getcwd(), "Output", "Tablerunner"))
    DEFAULT_FOOTER_PATH = os.path.join(getattr(config, "SCRIPTS_FOLDER", os.getcwd()), "Footer.pdf")
except ModuleNotFoundError:
    # Fallback defaults
    TEMPLATE_6FT_WIDTH = 2171.53
    TEMPLATE_6FT_HEIGHT = 5285.94
    TEMPLATE_15FT_WIDTH = 2171.53
    TEMPLATE_15FT_HEIGHT = 13061.90
    TABLERUNNER_15FT_WIDTH = 1447.69
    TABLERUNNER_15FT_HEIGHT = 13061.90
    TABLERUNNER_30FT_WIDTH = 1447.69
    TABLERUNNER_30FT_HEIGHT = 26123.80
    DEFAULT_OUTPUT_DIR = os.path.join(os.getcwd(), "Output")
    DEFAULT_TABLERUNNER_DIR = os.path.join(os.getcwd(), "Output", "Tablerunner")
    DEFAULT_FOOTER_PATH = os.path.join(os.getcwd(), "Footer.pdf")

DPI = 300
HORIZONTAL_REPEATS = 6
TABLERUNNER_HORIZONTAL_REPEATS = 4

# ASCII-safe print function
import builtins as _builtins

def _ascii_print(*args, **kwargs):
    """Print function that removes non-ASCII characters for compatibility."""
    processed = [str(arg).encode("ascii", "ignore").decode("ascii") for arg in args]
    _builtins.print(*processed, **kwargs)

print = _ascii_print

def validate_and_resize_image(image_path: str, max_pixels: int = MAX_SAFE_PIXELS) -> Image.Image:
    """
    Load and validate image, resizing if necessary to prevent memory issues.
    
    Args:
        image_path: Path to the image file
        max_pixels: Maximum number of pixels allowed
        
    Returns:
        PIL Image object, resized if necessary
        
    Raises:
        ValueError: If image cannot be processed
    """
    try:
        # First, get image info without loading the full image
        with Image.open(image_path) as img_info:
            width, height = img_info.size
            total_pixels = width * height
            
            print(f"  Image dimensions: {width}x{height} ({total_pixels:,} pixels)")
            
            if total_pixels > max_pixels:
                # Calculate resize ratio to stay under the limit
                ratio = (max_pixels / total_pixels) ** 0.5
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                
                print(f"  Resizing large image to {new_width}x{new_height} for safety")
                
                # Load and resize the image
                img = Image.open(image_path)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                return img
            else:
                # Image is safe to load as-is
                return Image.open(image_path)
                
    except Exception as e:
        raise ValueError(f"Cannot process image {image_path}: {e}")

def generate_barcode(code_text: str, width_points: int = 250, height_points: int = 40) -> bytes | None:
    """Return a PNG byte stream containing a cropped Code128 barcode."""
    try:
        writer = ImageWriter()
        writer.set_options({
            "module_height": 18.0,
            "font_size": 0,
            "text_distance": 0,
            "quiet_zone": 1.0,
            "write_text": False,
        })

        barcode_obj = Code128(code_text, writer=writer)
        buffer = io.BytesIO()
        barcode_obj.write(buffer)
        buffer.seek(0)

        barcode_img = Image.open(buffer)
        width, height = barcode_img.size
        crop_box = (0, 0, width, int(height * 0.50))
        cropped = barcode_img.crop(crop_box)

        width_px = int(width_points * (DPI / 72))
        height_px = int(height_points * (DPI / 72))
        resized = cropped.resize((width_px, height_px), Image.Resampling.NEAREST)

        out_buffer = io.BytesIO()
        resized.save(out_buffer, format="PNG")
        out_buffer.seek(0)
        return out_buffer.getvalue()
    except Exception as exc:
        print(f"  Warning: Error generating barcode: {exc}")
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
        
        # Load and validate the image
        try:
            image = validate_and_resize_image(image_path)
        except ValueError as e:
            print(f"  Error: {e}")
            return False
        
        doc = fitz.open()
        page = doc.new_page(width=template_width, height=template_height)

        tile_width = template_width / horizontal_repeats
        tile_height = tile_width / (image.width / image.height)

        # Calculate target tile size in pixels
        tile_width_px = int(tile_width * (dpi / 72))
        tile_height_px = int(tile_height * (dpi / 72))
        
        # Ensure tile dimensions are reasonable
        max_tile_dimension = 2000  # pixels
        if tile_width_px > max_tile_dimension or tile_height_px > max_tile_dimension:
            scale_factor = min(max_tile_dimension / tile_width_px, max_tile_dimension / tile_height_px)
            tile_width_px = int(tile_width_px * scale_factor)
            tile_height_px = int(tile_height_px * scale_factor)
            print(f"  Scaled tile size to {tile_width_px}x{tile_height_px} for performance")

        resized = image.resize((tile_width_px, tile_height_px), Image.Resampling.LANCZOS)

        # Save temporary scaled image
        temp_scaled = os.path.join(os.path.dirname(output_pdf_path), "temp_scaled_image.png")
        resized.save(temp_scaled, "PNG", dpi=(dpi, dpi), optimize=True)

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
        
        # Clean up
        image.close()
        if os.path.exists(temp_scaled):
            os.remove(temp_scaled)
            
        print(f"  Success: Tiled PDF saved: {output_pdf_path}")
        return True
        
    except Exception as exc:
        print(f"  Error creating tiled PDF: {exc}")
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
    """Embed the footer, descriptive texts and a barcode onto base_pdf_path."""

    try:
        print("  Adding footer, text, and barcode...")

        base_doc = fitz.open(base_pdf_path)
        base_page = base_doc[0]

        footer_height = 100
        if os.path.exists(footer_path):
            footer_doc = fitz.open(footer_path)
            footer_page = footer_doc[0]
            footer_rect_original = footer_page.rect
            scale = template_width / footer_rect_original.width
            footer_height = footer_rect_original.height * scale
            footer_rect = fitz.Rect(0, template_height - footer_height, template_width, template_height)
            base_page.show_pdf_page(footer_rect, footer_doc, 0)
            footer_doc.close()
            print("  Success: Footer embedded")
        else:
            print(f"  Warning: Footer not found at {footer_path}, using placeholder")
            placeholder = fitz.Rect(0, template_height - footer_height, template_width, template_height)
            base_page.draw_rect(placeholder, color=(0.95, 0.95, 0.95), fill=(0.95, 0.95, 0.95))

        # Determine product type and set appropriate positioning
        is_tablerunner = template_width < 2000

        if is_tablerunner:
            pattern_offset = 132
            width_offset   = 115
            length_offset  = 115
            barcode_offset = 320
            font_size = 9
            barcode_width_pt  = 120
            barcode_height_pt = 30
            text_y_offsets = {"pattern": 15, "width": 26, "length": 37}
        else:
            pattern_offset = 195
            width_offset   = 177
            length_offset  = 170
            barcode_offset = 500
            font_size = 13
            barcode_width_pt  = 200
            barcode_height_pt = 50
            text_y_offsets = {"pattern": 21, "width": 38, "length": 54.5}

        # Insert texts
        grey = (0.35, 0.35, 0.35)
        texts = [
            (pattern_name, (template_width - pattern_offset, template_height - footer_height + text_y_offsets["pattern"])),
            (roll_width,   (template_width - width_offset,   template_height - footer_height + text_y_offsets["width"])),
            (roll_length,  (template_width - length_offset,  template_height - footer_height + text_y_offsets["length"])),
        ]
        for text, pos in texts:
            base_page.insert_text(point=pos, text=text, fontsize=font_size, color=grey)

        # Add barcode
        barcode_bytes = generate_barcode(barcode_text, barcode_width_pt, barcode_height_pt)
        if barcode_bytes:
            x = template_width - barcode_offset
            y = template_height - footer_height + 20
            rect = fitz.Rect(x, y, x + barcode_width_pt, y + barcode_height_pt)
            base_page.insert_image(rect, stream=barcode_bytes)
            print(f"  Success: Added barcode: {barcode_text}")

        # Save with temporary file handling
        tmp = output_pdf_path.replace(".pdf", "_tmp.pdf")
        base_doc.save(tmp)
        base_doc.close()
        if os.path.exists(output_pdf_path):
            os.remove(output_pdf_path)
        os.rename(tmp, output_pdf_path)
        print("  Success: Final PDF saved with footer, text, and barcode")
        return True
        
    except Exception as exc:
        print(f"  Error overlaying footer and adding text: {exc}")
        return False

def process_wrapping_paper(image_path: str, output_dir: str, footer_path: str) -> None:
    """Generate 6 ft and 15 ft wrapping-paper variants for a single input image."""
    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        return

    base_name = os.path.splitext(os.path.basename(image_path))[0]
    print(f"\nProcessing wrapping paper: {base_name}")

    # 6 ft variant
    print("\nGenerating 6ft wrapping paper")
    barcode_6ft = f"{base_name}06"
    pdf6 = os.path.join(output_dir, f"{barcode_6ft}.pdf")
    if create_tiled_image_pdf(pdf6, image_path, TEMPLATE_6FT_WIDTH, TEMPLATE_6FT_HEIGHT):
        overlay_footer_and_add_text(pdf6, footer_path, pdf6, TEMPLATE_6FT_WIDTH, TEMPLATE_6FT_HEIGHT,
                                   base_name, "30'", "6'", barcode_6ft)

    # 15 ft variant
    print("\nGenerating 15ft wrapping paper")
    barcode_15ft = f"{base_name}15"
    pdf15 = os.path.join(output_dir, f"{barcode_15ft}.pdf")
    if create_tiled_image_pdf(pdf15, image_path, TEMPLATE_15FT_WIDTH, TEMPLATE_15FT_HEIGHT):
        overlay_footer_and_add_text(pdf15, footer_path, pdf15, TEMPLATE_15FT_WIDTH, TEMPLATE_15FT_HEIGHT,
                                   base_name, "30'", "15'", barcode_15ft)

    print(f"\nCompleted wrapping paper processing: {base_name}")

def process_tablerunner(image_path: str, output_dir: str, footer_path: str) -> None:
    """Generate 15 ft and 30 ft tablerunner variants for a single input image."""
    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        return

    base_name = os.path.splitext(os.path.basename(image_path))[0]
    print(f"\nProcessing tablerunner: {base_name}")

    # 15 ft tablerunner
    print("\nGenerating 15ft tablerunner")
    barcode_15ft = f"{base_name}71"
    pdf15 = os.path.join(output_dir, f"{barcode_15ft}.pdf")
    if create_tiled_image_pdf(pdf15, image_path, TABLERUNNER_15FT_WIDTH, TABLERUNNER_15FT_HEIGHT,
                             horizontal_repeats=TABLERUNNER_HORIZONTAL_REPEATS):
        overlay_footer_and_add_text(pdf15, footer_path, pdf15, TABLERUNNER_15FT_WIDTH, TABLERUNNER_15FT_HEIGHT,
                                   base_name, "20'", "15'", barcode_15ft)

    # 30 ft tablerunner
    print("\nGenerating 30ft tablerunner")
    barcode_30ft = f"{base_name}72"
    pdf30 = os.path.join(output_dir, f"{barcode_30ft}.pdf")
    if create_tiled_image_pdf(pdf30, image_path, TABLERUNNER_30FT_WIDTH, TABLERUNNER_30FT_HEIGHT,
                             horizontal_repeats=TABLERUNNER_HORIZONTAL_REPEATS):
        overlay_footer_and_add_text(pdf30, footer_path, pdf30, TABLERUNNER_30FT_WIDTH, TABLERUNNER_30FT_HEIGHT,
                                   base_name, "20'", "30'", barcode_30ft)

    print(f"\nCompleted tablerunner processing: {base_name}")

def process_image(image_path: str, output_dir: str, footer_path: str, is_tablerunner: bool = False) -> None:
    """Dispatch to the correct processing routine."""
    if is_tablerunner:
        process_tablerunner(image_path, output_dir, footer_path)
    else:
        process_wrapping_paper(image_path, output_dir, footer_path)

def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate 6ft/15ft wrapping-paper PDFs or 15ft/30ft tablerunner PDFs from images.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("images", nargs="+", help="Path(s) to the source PNG/JPG image(s).")
    parser.add_argument("-o", "--output-dir", help="Directory where the generated PDFs will be written.")
    parser.add_argument("-f", "--footer", default=DEFAULT_FOOTER_PATH, help="Path to Footer.pdf.")
    parser.add_argument("--tablerunner", action="store_true",
                       help="Generate tablerunner PDFs (15ft/30ft, 20\" width) instead of wrapping paper PDFs (6ft/15ft, 30\" width).")
    return parser.parse_args(argv)

def main(argv: List[str] | None = None) -> None:
    args = parse_args(argv)

    if args.output_dir is None:
        args.output_dir = DEFAULT_TABLERUNNER_DIR if args.tablerunner else DEFAULT_OUTPUT_DIR

    os.makedirs(args.output_dir, exist_ok=True)

    product_type = "TABLERUNNER" if args.tablerunner else "WRAPPING PAPER"
    print(f"{product_type} PDF GENERATOR")
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
        print(f"Warning: Footer not found at {args.footer}")
        print("A placeholder will be drawn instead.")

    for img in args.images:
        process_image(img, args.output_dir, args.footer, args.tablerunner)

    print(f"\n{product_type} PDF generation complete!")

if __name__ == "__main__":
    main()