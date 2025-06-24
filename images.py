import sys
import os
from PIL import Image
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_image(input_path, product_id, download_dir, output_dir):
    """
    Process an image file.
    
    Args:
        input_path (str): Path to the input image
        product_id (str): Product ID
        download_dir (str): Directory where the image was downloaded
        output_dir (str): Directory where processed images should be saved
    """
    try:
        logger.info(f"Processing image: {input_path}")
        logger.info(f"Product ID: {product_id}")
        logger.info(f"Download directory: {download_dir}")
        logger.info(f"Output directory: {output_dir}")
        
        # Verify input file exists
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")
            
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Open and process the image
        with Image.open(input_path) as img:
            # Log image details
            logger.info(f"Image size: {img.size}")
            logger.info(f"Image mode: {img.mode}")
            
            # For now, just save a copy of the image
            output_path = os.path.join(output_dir, f"{product_id}_processed.png")
            img.save(output_path)
            logger.info(f"Saved processed image to: {output_path}")
            
        return True
        
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise

def main():
    if len(sys.argv) != 5:
        print("Usage: python images.py <input_image_path> <product_id> <download_dir> <output_dir>")
        sys.exit(1)
        
    input_path = sys.argv[1]
    product_id = sys.argv[2]
    download_dir = sys.argv[3]
    output_dir = sys.argv[4]
    
    try:
        process_image(input_path, product_id, download_dir, output_dir)
        print("Image processing completed successfully")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 