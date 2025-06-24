import os
from pathlib import Path

# Base directories
BASE_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOWNLOAD_BASE_FOLDER = os.path.join(BASE_FOLDER, 'Download')
OUTPUT_BASE_FOLDER = os.path.join(BASE_FOLDER, 'Output')

# Ensure base directories exist
os.makedirs(DOWNLOAD_BASE_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_BASE_FOLDER, exist_ok=True)

# AWS S3 bucket configuration
BUCKET_NAME = 'aspenarlo'  # Your S3 bucket name

# Logging configuration
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

# Image processing configuration
TILE_SIZES = [2, 3, 4]  # Different tile sizes for image processing
MAX_IMAGE_SIZE = (3000, 3000)  # Maximum dimensions for processed images
SUPPORTED_FORMATS = ['.png', '.jpg', '.jpeg']

# Photoshop configuration
PHOTOSHOP_SCRIPT_PATH = os.path.join(BASE_FOLDER, 'Scripts', 'source3.jsx')

# Output file naming
OUTPUT_PREFIX = 'processed_'
OUTPUT_SUFFIX = '_final' 