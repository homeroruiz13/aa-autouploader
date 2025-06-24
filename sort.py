from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import os
from pathlib import Path
import shutil
from typing import Tuple
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ImageSorter:
    def __init__(self, source_dir: str, max_workers: int = 4):
        """Initialize the image sorter.
        
        Args:
            source_dir (str): Directory containing images to sort
            max_workers (int): Maximum number of concurrent threads
        """
        self.source_dir = Path(source_dir)
        self.max_workers = max_workers
        self.supported_formats = {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}
        
    def get_image_dimensions(self, image_path: Path) -> Tuple[int, int]:
        """Get the dimensions of an image.
        
        Args:
            image_path (Path): Path to the image file
            
        Returns:
            Tuple[int, int]: Width and height of the image
        """
        try:
            with Image.open(image_path) as img:
                return img.size
        except Exception as e:
            logger.error(f"Error reading {image_path.name}: {str(e)}")
            return (0, 0)
            
    def get_destination_folder(self, dimensions: Tuple[int, int]) -> str:
        """Generate folder name based on image dimensions.
        
        Args:
            dimensions (Tuple[int, int]): Width and height of the image
            
        Returns:
            str: Folder name in format {width}x{height}
        """
        width, height = dimensions
        return f"{width}x{height}"
        
    def process_image(self, image_path: Path) -> None:
        """Process a single image - get dimensions and move to appropriate folder.
        
        Args:
            image_path (Path): Path to the image file
        """
        try:
            # Skip if not a supported image format
            if image_path.suffix.lower() not in self.supported_formats:
                logger.warning(f"Skipping unsupported format: {image_path.name}")
                return
                
            # Get image dimensions
            dimensions = self.get_image_dimensions(image_path)
            if dimensions == (0, 0):
                return
                
            # Create destination folder
            folder_name = self.get_destination_folder(dimensions)
            dest_folder = self.source_dir / folder_name
            dest_folder.mkdir(exist_ok=True)
            
            # Move the image
            dest_path = dest_folder / image_path.name
            shutil.move(str(image_path), str(dest_path))
            logger.info(f"Moved {image_path.name} to {folder_name}/")
            
        except Exception as e:
            logger.error(f"Error processing {image_path.name}: {str(e)}")
            
    def sort_images(self) -> None:
        """Sort all images in the source directory using thread pool."""
        try:
            # Get list of all files in source directory
            image_files = [
                f for f in self.source_dir.iterdir() 
                if f.is_file() and f.suffix.lower() in self.supported_formats
            ]
            
            if not image_files:
                logger.warning("No supported image files found in directory")
                return
                
            total_files = len(image_files)
            logger.info(f"Found {total_files} images to process")
            
            # Process images concurrently
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                executor.map(self.process_image, image_files)
                
            # Print summary of organized folders
            self.print_summary()
            
        except Exception as e:
            logger.error(f"Error during sorting: {str(e)}")
            
    def print_summary(self) -> None:
        """Print summary of organized folders and their contents."""
        try:
            logger.info("\nOrganization Summary:")
            total_images = 0
            
            # Get all subdirectories (dimension folders)
            folders = [f for f in self.source_dir.iterdir() if f.is_dir()]
            
            for folder in sorted(folders):
                # Count images in each folder
                images = list(folder.glob('*'))
                num_images = len(images)
                total_images += num_images
                logger.info(f"{folder.name}: {num_images} images")
                
            logger.info(f"\nTotal: {total_images} images organized into {len(folders)} folders")
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")

def main():
    # Configuration
    source_dir = r"C:\Users\john\Downloads\printify_images"  # Your specific path
    max_workers = 8  # Adjust based on your CPU
    
    # Create and run sorter
    try:
        sorter = ImageSorter(source_dir, max_workers)
        logger.info(f"Starting image organization in: {source_dir}")
        sorter.sort_images()
        logger.info("Organization complete!")
        
    except Exception as e:
        logger.error(f"Program error: {str(e)}")
        
if __name__ == "__main__":
    main()