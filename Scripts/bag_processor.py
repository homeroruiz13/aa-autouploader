import os
import sys
import subprocess
import logging
from PIL import Image
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_bag_tiles(download_folder):
    """
    Create 3x3 and 4x4 tiled versions of images for bag processing.
    Uses smaller, more manageable tile sizes to avoid memory issues.
    """
    logger.info(f"Creating bag tiles from images in: {download_folder}")
    
    # Find all original PNG files (not the _6, _3, or _4 tiled ones)
    original_files = []
    for file in os.listdir(download_folder):
        if file.endswith('.png') and not any(file.endswith(f'_{i}.png') for i in [3, 4, 6]):
            original_files.append(os.path.join(download_folder, file))
    
    logger.info(f"Found {len(original_files)} original images to process")
    
    created_tiles = []
    for original_file in original_files:
        try:
            # Open the original image
            with Image.open(original_file) as img:
                # Resize original image to manageable size first to avoid memory issues
                max_dimension = 1000  # Limit individual tile to 1000px max
                if img.width > max_dimension or img.height > max_dimension:
                    ratio = min(max_dimension / img.width, max_dimension / img.height)
                    new_size = (int(img.width * ratio), int(img.height * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                width, height = img.size
                base_name = os.path.splitext(os.path.basename(original_file))[0]
                
                # Create 3x3 tiled version (for Bags 1, 3, 7)
                tiled_3x3 = Image.new(img.mode, (width * 3, height * 3))
                for i in range(3):
                    for j in range(3):
                        tiled_3x3.paste(img, (i * width, j * height))
                
                tiled_3x3_file = os.path.join(download_folder, f"{base_name}_3.png")
                tiled_3x3.save(tiled_3x3_file, optimize=True)
                created_tiles.append(tiled_3x3_file)
                logger.info(f"Created 3x3 tile: {tiled_3x3_file}")
                
                # Create 4x4 tiled version (for Bags 4, 5, 6)
                tiled_4x4 = Image.new(img.mode, (width * 4, height * 4))
                for i in range(4):
                    for j in range(4):
                        tiled_4x4.paste(img, (i * width, j * height))
                
                tiled_4x4_file = os.path.join(download_folder, f"{base_name}_4.png")
                tiled_4x4.save(tiled_4x4_file, optimize=True)
                created_tiles.append(tiled_4x4_file)
                logger.info(f"Created 4x4 tile: {tiled_4x4_file}")
                
        except Exception as e:
            logger.error(f"Error creating tiles for {original_file}: {e}")
    
    return created_tiles

def run_bag_jsx():
    """
    Execute the bag processing JSX script with better error handling.
    """
    try:
        # Get script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        jsx_script_path = os.path.join(script_dir, "bags.jsx")
        
        if not os.path.exists(jsx_script_path):
            logger.error(f"Bag JSX script not found at: {jsx_script_path}")
            return False
        
        # Find Photoshop executable
        photoshop_paths = [
            r"C:\Program Files\Adobe\Adobe Photoshop 2025\Photoshop.exe",
            r"C:\Program Files\Adobe\Adobe Photoshop 2024\Photoshop.exe",
            r"C:\Program Files\Adobe\Adobe Photoshop 2023\Photoshop.exe"
        ]
        
        photoshop_exe = None
        for path in photoshop_paths:
            if os.path.exists(path):
                photoshop_exe = path
                break
        
        if not photoshop_exe:
            logger.error("Photoshop executable not found")
            return False
        
        logger.info(f"Executing bag JSX script with Photoshop: {photoshop_exe}")
        
        # Close any existing Photoshop processes first
        try:
            subprocess.run(['taskkill', '/f', '/im', 'Photoshop.exe'], 
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except:
            pass
        
        # Run the script with longer timeout
        process = subprocess.Popen(
            [photoshop_exe, '-r', jsx_script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=script_dir
        )
        
        stdout, stderr = process.communicate(timeout=900)  # 15 minute timeout
        
        if stdout:
            logger.info(f"Photoshop output: {stdout.decode()}")
        if stderr:
            logger.error(f"Photoshop errors: {stderr.decode()}")
        
        logger.info(f"Bag processing finished with return code: {process.returncode}")
        return process.returncode == 0
        
    except subprocess.TimeoutExpired:
        logger.error("Bag processing timed out after 15 minutes")
        process.kill()
        return False
    except Exception as e:
        logger.error(f"Error running bag JSX script: {e}")
        return False

def process_bags():
    """
    Main function to process bags with corrected paths.
    """
    try:
        logger.info("Starting bag processing...")
        
        # Get script directory - this is Scripts folder
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up one level to get to the project root (aa-auto)
        project_root = os.path.dirname(script_dir)
        download_base = os.path.join(project_root, "Download")
        
        # Find the most recent download folder
        if not os.path.exists(download_base):
            logger.error(f"Download base folder not found: {download_base}")
            return False
        
        # Get the most recent timestamped folder
        timestamped_folders = [f for f in os.listdir(download_base) 
                             if os.path.isdir(os.path.join(download_base, f)) 
                             and len(f) == 19 and f[4] == '-' and f[7] == '-']  # YYYY-MM-DD_HH-MM-SS format
        
        if not timestamped_folders:
            logger.error("No timestamped folders found in Download directory")
            return False
        
        # Sort and get the most recent
        timestamped_folders.sort(reverse=True)
        most_recent_folder = os.path.join(download_base, timestamped_folders[0])
        
        logger.info(f"Using download folder: {most_recent_folder}")
        
        # Create 3x3 and 4x4 tiles with size optimization
        created_tiles = create_bag_tiles(most_recent_folder)
        
        if not created_tiles:
            logger.warning("No tiles were created - checking for existing tiles")
            # Check if tiles already exist
            existing_tiles = [f for f in os.listdir(most_recent_folder) 
                            if f.endswith('_3.png') or f.endswith('_4.png')]
            if not existing_tiles:
                logger.error("No bag tiles found")
                return False
            logger.info(f"Found {len(existing_tiles)} existing tiles")
        
        # Run the bag JSX script
        success = run_bag_jsx()
        
        if success:
            logger.info("BAG_PROCESSING_COMPLETE")
            return True
        else:
            logger.error("Bag processing failed")
            return False
            
    except Exception as e:
        logger.error(f"Error in bag processing: {e}")
        return False

if __name__ == "__main__":
    success = process_bags()
    sys.exit(0 if success else 1)