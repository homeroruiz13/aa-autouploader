import os
import sys
import subprocess
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_tissue_jsx():
    """
    Execute the tissue processing JSX script, following the same pattern as bags.jsx.
    """
    try:
        # Get script directory (same as your source3.jsx)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        jsx_script_path = os.path.join(script_dir, "tissues.jsx")
        
        if not os.path.exists(jsx_script_path):
            logger.error(f"Tissue JSX script not found at: {jsx_script_path}")
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
        
        logger.info(f"Executing tissue JSX script with Photoshop: {photoshop_exe}")
        
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
        
        logger.info(f"Tissue processing finished with return code: {process.returncode}")
        return process.returncode == 0
        
    except subprocess.TimeoutExpired:
        logger.error("Tissue processing timed out after 15 minutes")
        process.kill()
        return False
    except Exception as e:
        logger.error(f"Error running tissue JSX script: {e}")
        return False

def process_tissues():
    """
    Main function to process tissues. This follows the same pattern as bag processing.
    """
    try:
        logger.info("Starting tissue processing...")
        
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
        
        # Check if we have 6x6 tiled images (tissues use the same 6x6 tiles as your existing workflow)
        tiled_files = [f for f in os.listdir(most_recent_folder) if f.endswith('_6.png')]
        
        if not tiled_files:
            logger.warning("No 6x6 tiled images found for tissue processing")
            return False
        
        logger.info(f"Found {len(tiled_files)} 6x6 tiled images for tissue processing")
        
        # Run the tissue JSX script
        success = run_tissue_jsx()
        
        if success:
            logger.info("TISSUE_PROCESSING_COMPLETE")
            return True
        else:
            logger.error("Tissue processing failed")
            return False
            
    except Exception as e:
        logger.error(f"Error in tissue processing: {e}")
        return False

if __name__ == "__main__":
    success = process_tissues()
    sys.exit(0 if success else 1)
