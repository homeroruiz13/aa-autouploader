import os
import sys
import logging
import time
import traceback
from datetime import datetime
import fitz  # PyMuPDF
from PIL import Image

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("pdf_generator.log"),
        logging.StreamHandler()
    ]
)

def create_tiled_image_pdf(output_pdf_path, image_path, template_width, template_height, dpi=300, horizontal_repeats=6):
    """Create a PDF with tiled image pattern."""
    try:
        logging.info(f"Creating tiled PDF for {image_path}")
        logging.info(f"Output path: {output_pdf_path}")
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_pdf_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            logging.info(f"Created output directory: {output_dir}")
        
        # Verify image file exists
        if not os.path.exists(image_path):
            logging.error(f"ERROR: Image file not found at {image_path}")
            return False
        
        # Verify image is valid
        try:
            image = Image.open(image_path)
            image_format = image.format
            image_size = image.size
            logging.info(f"Image format: {image_format}, size: {image_size}")
        except Exception as e:
            logging.error(f"ERROR: Could not open image {image_path}: {e}")
            return False

        # Create a new document
        try:
            doc = fitz.open()
            page = doc.new_page(width=template_width, height=template_height)
            logging.info(f"Created new document page: {template_width}x{template_height}")
        except Exception as e:
            logging.error(f"ERROR: Failed to create document: {e}")
            return False

        # Calculate tile dimensions
        tile_width = template_width / horizontal_repeats
        tile_height = tile_width / (image.width / image.height)  # Maintain aspect ratio
        logging.info(f"Calculated tile dimensions: {tile_width}x{tile_height}")

        # Convert to pixels for resizing
        tile_width_px = int(tile_width * (dpi / 72))
        tile_height_px = int(tile_height * (dpi / 72))
        logging.info(f"Pixel dimensions for {dpi} DPI: {tile_width_px}x{tile_height_px}")

        # Create a temp directory for intermediary files if it doesn't exist
        temp_dir = os.path.join(os.path.dirname(output_pdf_path), "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        scaled_image_path = os.path.join(temp_dir, f"scaled_image_{os.path.basename(image_path)}")
        logging.info(f"Temp scaled image path: {scaled_image_path}")
        
        try:
            image = image.resize((tile_width_px, tile_height_px), Image.Resampling.LANCZOS)
            image.save(scaled_image_path, "PNG")
            logging.info(f"Saved resized image to {scaled_image_path}")
        except Exception as e:
            logging.error(f"ERROR: Could not resize or save image: {e}")
            return False

        # Verify scaled image exists
        if not os.path.exists(scaled_image_path):
            logging.error(f"ERROR: Scaled image not found at {scaled_image_path}")
            return False

        # Insert tiles
        y = 0
        insertion_count = 0
        while y < template_height:
            x = 0
            while x + tile_width <= template_width:  # Ensure correct number of repetitions
                rect = fitz.Rect(x, y, x + tile_width, y + tile_height)
                try:
                    page.insert_image(rect, filename=scaled_image_path)
                    insertion_count += 1
                except Exception as e:
                    logging.error(f"ERROR: Failed to insert image at position {x},{y}: {e}")
                x += tile_width
            y += tile_height

        # Save the PDF
        try:
            doc.save(output_pdf_path)
            doc.close()
            logging.info(f"Tiled PDF saved successfully: {output_pdf_path} (inserted {insertion_count} tiles)")
            
            # Verify the PDF was created
            if os.path.exists(output_pdf_path):
                file_size = os.path.getsize(output_pdf_path)
                logging.info(f"Verified PDF file exists: {output_pdf_path}, size: {file_size} bytes")
                return True
            else:
                logging.error(f"ERROR: PDF file was not created at {output_pdf_path}")
                return False
        except Exception as e:
            logging.error(f"ERROR: Failed to save PDF {output_pdf_path}: {e}")
            return False
            
    except Exception as e:
        logging.error(f"ERROR creating tiled PDF for {image_path}: {e}")
        traceback.print_exc()
        return False

def overlay_footer_and_add_text(base_pdf_path, footer_path, output_pdf_path, template_width, template_height, pattern_name, roll_width, roll_length):
    """Add footer and text to the base PDF."""
    try:
        logging.info(f"Adding footer and text to {base_pdf_path}")
        
        # Check if base PDF exists
        if not os.path.exists(base_pdf_path):
            logging.error(f"ERROR: Base PDF not found at {base_pdf_path}")
            return False
            
        # Check for footer PDF
        if not os.path.exists(footer_path):
            logging.error(f"ERROR: Footer PDF not found at {footer_path}")
            return False
        
        try:
            base_doc = fitz.open(base_pdf_path)
            if base_doc.page_count == 0:
                logging.error(f"ERROR: Base PDF has no pages")
                base_doc.close()
                return False
                
            base_page = base_doc[0]
            logging.info(f"Opened base PDF: {base_pdf_path}")

            footer_doc = fitz.open(footer_path)
            if footer_doc.page_count == 0:
                logging.error(f"ERROR: Footer PDF has no pages")
                base_doc.close()
                footer_doc.close()
                return False
                
            footer_page = footer_doc[0]
            logging.info(f"Opened footer PDF: {footer_path}")
            
            footer_pixmap = footer_page.get_pixmap()
            logging.info(f"Got footer pixmap: {footer_pixmap.width}x{footer_pixmap.height}")
        except Exception as e:
            logging.error(f"ERROR: Failed to open PDFs: {e}")
            return False

        # Calculate footer position
        footer_width = template_width
        footer_height = footer_pixmap.height / footer_pixmap.width * footer_width
        footer_rect = fitz.Rect(0, template_height - footer_height, footer_width, template_height)
        logging.info(f"Footer rectangle: {footer_rect}")
        
        try:
            base_page.insert_image(footer_rect, pixmap=footer_pixmap, keep_proportion=True)
            logging.info(f"Inserted footer image")
        except Exception as e:
            logging.error(f"ERROR: Could not insert footer image: {e}")
            base_doc.close()
            footer_doc.close()
            return False

        # Add the pattern name, width, and length
        try:
            # Settings for text
            font_size = 13
            grey_color = (0.4, 0.4, 0.4)
            font_name = "Helvetica"
            
            # Add pattern name
            pattern_position = (template_width - 195, template_height - footer_height + 22)
            base_page.insert_text(
                point=pattern_position,
                text=pattern_name,
                fontsize=font_size,
                fontname=font_name,
                color=grey_color
            )
            logging.info(f"Added pattern name: {pattern_name}")
            
            # Add width
            width_position = (template_width - 170, template_height - footer_height + 37)
            base_page.insert_text(
                point=width_position,
                text=roll_width,
                fontsize=font_size,
                fontname=font_name,
                color=grey_color
            )
            logging.info(f"Added width: {roll_width}")
            
            # Add length
            length_position = (template_width - 170, template_height - footer_height + 55)
            base_page.insert_text(
                point=length_position,
                text=roll_length,
                fontsize=font_size,
                fontname=font_name,
                color=grey_color
            )
            logging.info(f"Added length: {roll_length}")
            
        except Exception as e:
            logging.warning(f"WARNING: Error adding text: {e}")
            # Continue despite text error - we'll still have the footer image

        # Save the final PDF
        try:
            temp_output_path = output_pdf_path.replace(".pdf", "_temp.pdf")
            base_doc.save(temp_output_path)
            logging.info(f"Saved temporary PDF: {temp_output_path}")
            
            base_doc.close()
            footer_doc.close()
            
            # Safely replace the original file
            if os.path.exists(output_pdf_path):
                try:
                    os.remove(output_pdf_path)
                    logging.info(f"Removed existing output file: {output_pdf_path}")
                except Exception as e:
                    logging.warning(f"WARNING: Could not remove existing output file: {e}")
                    # Try to use a different filename
                    output_pdf_path = output_pdf_path.replace(".pdf", "_new.pdf")
                    logging.info(f"Using alternative output path: {output_pdf_path}")
            
            os.replace(temp_output_path, output_pdf_path)
            logging.info(f"Final PDF with footer and text saved: {output_pdf_path}")
            
            # Verify file existence
            if os.path.exists(output_pdf_path):
                file_size = os.path.getsize(output_pdf_path)
                logging.info(f"Verified final PDF exists: {output_pdf_path}, size: {file_size} bytes")
                return True
            else:
                logging.error(f"ERROR: Final PDF was not created at {output_pdf_path}")
                return False
        except Exception as e:
            logging.error(f"ERROR: Failed to save final PDF: {e}")
            return False
            
    except Exception as e:
        logging.error(f"ERROR overlaying footer and adding text: {e}")
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description="Generate PDFs with tiled images and overlay footers")
    parser.add_argument("image_paths", type=str, nargs="+", help="List of image paths to process")
    args = parser.parse_args()

    template_6ft_width = 2171.53
    template_6ft_height = 5285.94
    template_15ft_width = 2171.53
    template_15ft_height = 13061.90

    script_dir = os.path.dirname(os.path.abspath(__file__))
    footer_path = os.path.join(script_dir, "Footer.pdf")
    output_dir = os.getcwd()  # Get the current working directory

    # Check for required files at startup
    if not os.path.exists(footer_path):
        logging.error(f"ERROR: Footer PDF not found at {footer_path}")
        return

    for image_path in args.image_paths:
        if not os.path.exists(image_path):
            logging.error(f"ERROR: Image file not found: {image_path}")
            continue

        try:
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            logging.info(f"Processing {base_name} from {image_path}")

            # Create 6ft PDF with absolute path
            tiled_pdf_6 = os.path.join(output_dir, f"{base_name}_6ft.pdf")
            logging.info(f"Generating 6ft tiled PDF at: {tiled_pdf_6}")
            
            if create_tiled_image_pdf(tiled_pdf_6, image_path, template_6ft_width, template_6ft_height, horizontal_repeats=6):
                if overlay_footer_and_add_text(tiled_pdf_6, footer_path, tiled_pdf_6, template_6ft_width, template_6ft_height, base_name, "30'", "6'"):
                    logging.info(f"Successfully created 6ft PDF: {tiled_pdf_6}")

            # Create 15ft PDF with absolute path
            tiled_pdf_15 = os.path.join(output_dir, f"{base_name}_15ft.pdf")
            logging.info(f"Generating 15ft tiled PDF at: {tiled_pdf_15}")
            
            if create_tiled_image_pdf(tiled_pdf_15, image_path, template_15ft_width, template_15ft_height, horizontal_repeats=6):
                if overlay_footer_and_add_text(tiled_pdf_15, footer_path, tiled_pdf_15, template_15ft_width, template_15ft_height, base_name, "30'", "15'"):
                    logging.info(f"Successfully created 15ft PDF: {tiled_pdf_15}")

        except Exception as e:
            logging.error(f"Error processing {image_path}: {e}")
            continue

    logging.info("PDF generation complete.")

if __name__ == "__main__":
    import argparse
    main()
