import os
import sys
import logging
import time
import traceback
from datetime import datetime
import fitz  # PyMuPDF
from PIL import Image
import shutil
from config import BASE_FOLDER, SCRIPTS_FOLDER, TEMPLATE_IMAGES_FOLDER, TEMPLATE_6FT_WIDTH, TEMPLATE_6FT_HEIGHT, TEMPLATE_15FT_WIDTH, TEMPLATE_15FT_HEIGHT

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("batch_pdf_generator.log"),
        logging.StreamHandler()
    ]
)

# Configuration
INPUT_FOLDER = os.path.join(BASE_FOLDER, 'Download')
OUTPUT_FOLDER = os.path.join(BASE_FOLDER, 'Output')

# Footer path
FOOTER_PATH = os.path.join(SCRIPTS_FOLDER, 'Footer.pdf')

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
        temp_dir = os.path.join(OUTPUT_FOLDER, "temp")
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

        # Insert tiles
        y = 0
        insertion_count = 0
        while y < template_height:
            x = 0
            while x + tile_width <= template_width:
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

def create_simple_footer(output_path, width, height):
    """Create a simple footer PDF as a fallback."""
    logging.info(f"Creating simple footer PDF: {output_path}")
    doc = fitz.open()
    page = doc.new_page(width=width, height=height)
    
    # Add a light grey background
    rect = fitz.Rect(0, 0, width, height)
    page.draw_rect(rect, color=(0.95, 0.95, 0.95), fill=(0.95, 0.95, 0.95))
    
    # Add some lines
    page.draw_line(fitz.Point(0, 0), fitz.Point(width, 0), color=(0.8, 0.8, 0.8), width=1)
    
    # Add placeholder text
    page.insert_text(fitz.Point(50, 20), "Pattern:", fontsize=12)
    page.insert_text(fitz.Point(50, 40), "Width:", fontsize=12)
    page.insert_text(fitz.Point(50, 60), "Length:", fontsize=12)
    
    doc.save(output_path)
    doc.close()
    logging.info(f"Simple footer created: {output_path}")
    return True

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
            
            # Try fallback paths
            fallback_paths = [
                os.path.join(TEMPLATE_IMAGES_FOLDER, "Footer.pdf"),
                os.path.join(SCRIPTS_FOLDER, "Footer.pdf"),
                os.path.join(OUTPUT_FOLDER, "Footer.pdf")
            ]
            
            for fallback_path in fallback_paths:
                if os.path.exists(fallback_path):
                    logging.info(f"Using fallback footer path: {fallback_path}")
                    footer_path = fallback_path
                    break
            else:
                # If no footer found, create a simple one
                logging.warning(f"No footer found in any location, creating a simple replacement footer")
                simple_footer_path = os.path.join(OUTPUT_FOLDER, "simple_footer.pdf")
                try:
                    create_simple_footer(simple_footer_path, template_width, 100)
                    footer_path = simple_footer_path
                except Exception as e:
                    logging.error(f"Failed to create simple footer: {e}")
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
            black_color = (0, 0, 0)
            font_name = "Helvetica"
            
            # Add pattern name
            pattern_position = (140, template_height - 75)
            base_page.insert_text(
                point=pattern_position,
                text=pattern_name,
                fontsize=font_size,
                fontname=font_name,
                color=black_color
            )
            logging.info(f"Added pattern name: {pattern_name}")
            
            # Add width
            width_position = (1430, template_height - 60)
            base_page.insert_text(
                point=width_position,
                text=roll_width,
                fontsize=font_size,
                fontname=font_name,
                color=black_color
            )
            logging.info(f"Added width: {roll_width}")
            
            # Add length
            length_position = (1430, template_height - 74)
            base_page.insert_text(
                point=length_position,
                text=roll_length,
                fontsize=font_size,
                fontname=font_name,
                color=black_color
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

def process_image(image_path, max_retries=3):
    """Process a single image to create 6ft and 15ft PDFs."""
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    logging.info(f"Processing image: {base_name} from {image_path}")
    
    # Prepare output paths
    pdf_6ft_path = os.path.join(OUTPUT_FOLDER, f"{base_name}_6ft.pdf")
    pdf_15ft_path = os.path.join(OUTPUT_FOLDER, f"{base_name}_15ft.pdf")
    
    # Process 6ft PDF
    success_6ft = False
    for attempt in range(max_retries):
        try:
            logging.info(f"Creating 6ft PDF (attempt {attempt+1}/{max_retries})")
            if create_tiled_image_pdf(pdf_6ft_path, image_path, TEMPLATE_6FT_WIDTH, TEMPLATE_6FT_HEIGHT, horizontal_repeats=6):
                if overlay_footer_and_add_text(pdf_6ft_path, FOOTER_PATH, pdf_6ft_path, TEMPLATE_6FT_WIDTH, TEMPLATE_6FT_HEIGHT, base_name, "30'", "6'"):
                    success_6ft = True
                    logging.info(f"Successfully created 6ft PDF: {pdf_6ft_path}")
                    break
        except Exception as e:
            logging.error(f"Error on attempt {attempt+1}/{max_retries} for 6ft PDF: {e}")
            traceback.print_exc()
        
        if attempt < max_retries - 1:
            logging.info(f"Retrying 6ft PDF generation (attempt {attempt+2}/{max_retries})...")
            time.sleep(3)
    
    # Process 15ft PDF
    success_15ft = False
    for attempt in range(max_retries):
        try:
            logging.info(f"Creating 15ft PDF (attempt {attempt+1}/{max_retries})")
            if create_tiled_image_pdf(pdf_15ft_path, image_path, TEMPLATE_15FT_WIDTH, TEMPLATE_15FT_HEIGHT, horizontal_repeats=6):
                if overlay_footer_and_add_text(pdf_15ft_path, FOOTER_PATH, pdf_15ft_path, TEMPLATE_15FT_WIDTH, TEMPLATE_15FT_HEIGHT, base_name, "30'", "15'"):
                    success_15ft = True
                    logging.info(f"Successfully created 15ft PDF: {pdf_15ft_path}")
                    break
        except Exception as e:
            logging.error(f"Error on attempt {attempt+1}/{max_retries} for 15ft PDF: {e}")
            traceback.print_exc()
        
        if attempt < max_retries - 1:
            logging.info(f"Retrying 15ft PDF generation (attempt {attempt+2}/{max_retries})...")
            time.sleep(3)
    
    return success_6ft, success_15ft

def main():
    start_time = datetime.now()
    logging.info(f"=== BATCH PDF GENERATION STARTED AT {start_time} ===")
    
    # Create output folder if needed
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        logging.info(f"Created output folder: {OUTPUT_FOLDER}")
    
    # Create temp folder if needed
    temp_folder = os.path.join(OUTPUT_FOLDER, "temp")
    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder, exist_ok=True)
        logging.info(f"Created temp folder: {temp_folder}")
    
    # Verify input folder exists
    if not os.path.exists(INPUT_FOLDER):
        logging.error(f"Input folder not found: {INPUT_FOLDER}")
        return 1
    
    # Get all image files
    image_extensions = ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']
    image_files = []
    
    for filename in os.listdir(INPUT_FOLDER):
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext in image_extensions:
            image_files.append(os.path.join(INPUT_FOLDER, filename))
    
    if not image_files:
        logging.error(f"No image files found in {INPUT_FOLDER}")
        return 1
    
    logging.info(f"Found {len(image_files)} image files to process")
    
    # Process each image
    success_count = 0
    failed_count = 0
    
    for i, image_path in enumerate(image_files, 1):
        logging.info(f"Processing image {i}/{len(image_files)}: {os.path.basename(image_path)}")
        
        success_6ft, success_15ft = process_image(image_path)
        
        if success_6ft and success_15ft:
            success_count += 1
            logging.info(f"Successfully processed image {i}/{len(image_files)}")
        else:
            failed_count += 1
            logging.error(f"Failed to process image {i}/{len(image_files)}")
    
    end_time = datetime.now()
    duration = end_time - start_time
    
    logging.info(f"=== BATCH PDF GENERATION COMPLETED AT {end_time} ===")
    logging.info(f"Total duration: {duration}")
    logging.info(f"Successfully processed {success_count} images")
    logging.info(f"Failed to process {failed_count} images")
    
    print(f"\nBatch PDF Generation Complete!")
    print(f"Successfully processed: {success_count} images")
    print(f"Failed to process: {failed_count} images")
    print(f"Output saved to: {OUTPUT_FOLDER}")
    
    # Clean up temp folder
    try:
        if os.path.exists(temp_folder):
            shutil.rmtree(temp_folder)
            logging.info(f"Cleaned up temp folder: {temp_folder}")
    except Exception as e:
        logging.warning(f"Failed to clean up temp folder: {e}")
    
    return 0 if failed_count == 0 else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        logging.error(f"Unhandled exception: {e}")
        traceback.print_exc()
        sys.exit(1)