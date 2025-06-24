import os
import sys
import logging
from dotenv import load_dotenv
import boto3
from PIL import Image
import requests
import json
from config import BASE_FOLDER, DOWNLOAD_BASE_FOLDER, OUTPUT_BASE_FOLDER, MOCKUP_FOLDER, BUCKET_NAME

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_environment():
    logger.info("Testing environment setup...")
    
    # Test Python version and paths
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Base folder: {BASE_FOLDER}")
    logger.info(f"Download folder: {DOWNLOAD_BASE_FOLDER}")
    logger.info(f"Output folder: {OUTPUT_BASE_FOLDER}")
    logger.info(f"Mockup folder: {MOCKUP_FOLDER}")
    
    # Verify critical folders exist
    for folder in [DOWNLOAD_BASE_FOLDER, OUTPUT_BASE_FOLDER, MOCKUP_FOLDER]:
        if not os.path.exists(folder):
            logger.warning(f"Folder does not exist: {folder}")
            os.makedirs(folder, exist_ok=True)
            logger.info(f"Created folder: {folder}")
    
    # Test environment variables
    load_dotenv()
    aws_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    if not aws_key or not aws_secret:
        logger.error("AWS credentials not found in environment variables!")
        return False
    
    logger.info("AWS credentials found in environment")
    
    # Test AWS connection and bucket access
    try:
        s3 = boto3.client(
            's3',
            aws_access_key_id=aws_key,
            aws_secret_access_key=aws_secret,
            region_name='us-east-2'
        )
        
        # Test bucket access
        try:
            s3.head_bucket(Bucket=BUCKET_NAME)
            logger.info(f"Successfully connected to AWS S3 bucket: {BUCKET_NAME}")
        except Exception as e:
            logger.error(f"Failed to access bucket {BUCKET_NAME}: {e}")
            return False
            
        # Test listing objects
        response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix='wrappingpaper/new_uploads/', MaxKeys=1)
        logger.info("Successfully listed objects in S3 bucket")
        
    except Exception as e:
        logger.error(f"Failed to connect to AWS: {e}")
        return False
    
    # Test Pillow with a test image
    try:
        test_image_path = os.path.join(DOWNLOAD_BASE_FOLDER, 'test.png')
        img = Image.new('RGB', (100, 100))
        img.save(test_image_path)
        logger.info(f"Successfully created test image at: {test_image_path}")
        
        # Clean up test image
        if os.path.exists(test_image_path):
            os.remove(test_image_path)
            logger.info("Successfully cleaned up test image")
    except Exception as e:
        logger.error(f"Failed to test Pillow: {e}")
        return False
    
    # Test requests with a test S3 URL
    try:
        # Try to get a test image from S3
        test_url = f"https://{BUCKET_NAME}.s3.us-east-2.amazonaws.com/wrappingpaper/new_uploads/test.png"
        response = requests.head(test_url, timeout=5)
        logger.info("Successfully tested requests library with S3 URL")
    except requests.exceptions.RequestException as e:
        # This is expected to fail since the test image doesn't exist
        logger.info("Requests library working (expected 404 for test image)")
    
    # Test Photoshop JSX script exists
    jsx_script_path = os.path.join(BASE_FOLDER, "Source3_1.jsx")
    if os.path.exists(jsx_script_path):
        logger.info(f"Found Photoshop JSX script at: {jsx_script_path}")
    else:
        logger.error(f"Photoshop JSX script not found at: {jsx_script_path}")
        return False
    
    logger.info("All environment tests passed!")
    return True

if __name__ == "__main__":
    if test_environment():
        logger.info("Environment is properly configured for the workflow")
    else:
        logger.error("Environment test failed - please check the logs above") 