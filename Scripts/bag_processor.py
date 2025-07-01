#!C:\Program Files\Python313\python.exe
"""Bag pattern tiling + Photoshop automation for Bag 1–3 templates.

This script is invoked by *Scripts/images.py* after the regular wrapping-paper
Photoshop pass.  It performs three steps:

1. Locate the most-recent Download folder created earlier in the run.
2. Build 3 × 3 tiled versions ( *_3.png* ) of every original design image it
   finds there (the 6 × 6 tiles already exist from the main pipeline).
3. Launch Photoshop with *bags.jsx* which applies each tile to Bag 1, Bag 2 and
   Bag 3 PSD templates and exports *_bag1.png*, *_bag2.png* & *_bag3.png* files
   into the matching Output/<timestamp>/ folder.

The script is intentionally self-contained so failures here never abort the
wrapping-paper workflow – *images.py* treats a non-zero exit as non-fatal.
"""

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
    Create 3x3, 4x4, and 6x6 tiled versions of images for bag processing.
    Your existing workflow already creates 6x6 tiles, we need to add 3x3 and 4x4.
    """
    logger.info(f"Creating bag tiles from images in: {download_folder}")
    
    # Find all original PNG files (not the _6 tiled ones)
    original_files = []
    for file in os.listdir(download_folder):
        if file.endswith('.png') and not file.endswith('_6.png'):
            original_files.append(os.path.join(download_folder, file))
    
    logger.info(f"Found {len(original_files)} original images to process")
    
    created_tiles = []
    for original_file in original_files:
        try:
            # Open the original image
            with Image.open(original_file) as img:
                width, height = img.size
                base_name = os.path.splitext(os.path.basename(original_file))[0]
                
                # Create 3x3 tiled version (for Bags 1, 3, 7)
                tiled_3x3 = Image.new(img.mode, (width * 3, height * 3))
                for i in range(3):
                    for j in range(3):
                        tiled_3x3.paste(img, (i * width, j * height))
                
                tiled_3x3_file = os.path.join(download_folder, f"{base_name}_3.png")
                tiled_3x3.save(tiled_3x3_file)
                created_tiles.append(tiled_3x3_file)
                logger.info(f"Created 3x3 tile: {tiled_3x3_file}")
                
                # Create 4x4 tiled version (for Bags 4, 5, 6)
                tiled_4x4 = Image.new(img.mode, (width * 4, height * 4))
                for i in range(4):
                    for j in range(4):
                        tiled_4x4.paste(img, (i * width, j * height))
                
                tiled_4x4_file = os.path.join(download_folder, f"{base_name}_4.png")
                tiled_4x4.save(tiled_4x4_file)
                created_tiles.append(tiled_4x4_file)
                logger.info(f"Created 4x4 tile: {tiled_4x4_file}")
                
        except Exception as e:
            logger.error(f"Error creating tiles for {original_file}: {e}")
    
    return created_tiles

def run_bag_jsx():
    """
    Execute the bag processing JSX script, following the same pattern as your source3.jsx execution.
    """
    try:
        # Get script directory (same as your source3.jsx)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        jsx_script_path = os.path.join(script_dir, "bags.jsx")
        
        if not os.path.exists(jsx_script_path):
            logger.error(f"Bag JSX script not found at: {jsx_script_path}")
            return False
        
        # Find Photoshop executable (same logic as your existing code)
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
        
        # Run the script (Photoshop will quit itself via the JSX)
        process = subprocess.Popen(
            [photoshop_exe, jsx_script_path],
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
    Main function to process bags. This follows the same pattern as your existing workflow.
    """
    try:
        logger.info("Starting bag processing...")
        
        # Get script directory and go up one level to find Download folder
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)  # Go up one level from Scripts to project root
        download_base = os.path.join(project_root, "Download")
        
        # Find the most recent download folder (same logic as source3.jsx)
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
        
        # Create 3x3 and 4x4 tiles (your workflow already creates 6x6)
        created_tiles = create_bag_tiles(most_recent_folder)
        
        if not created_tiles:
            logger.warning("No 3x3 tiles were created")
            return False
        
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
