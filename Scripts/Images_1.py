import os
import requests
from PIL import Image
from datetime import datetime
import subprocess
import boto3
from botocore.exceptions import NoCredentialsError
import sys
import json
import csv
import io
import time
import shutil
from dotenv import load_dotenv
import logging
import traceback

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Initialize the boto3 S3 client using environment variables
s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name='us-east-2'
)

# Base folder constants – must match the settings in your JSX script
BASE_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Go up one level to root
DOWNLOAD_BASE_FOLDER = os.path.join(BASE_FOLDER, 'Download')
OUTPUT_BASE_FOLDER = os.path.join(BASE_FOLDER, 'Output')
MOCKUP_FOLDER = os.path.join(BASE_FOLDER, 'Mockup')
BAGS_FOLDER = os.path.join(BASE_FOLDER, 'Bags & Tissues')
TEMPLATE_IMAGES_FOLDER = os.path.join(BASE_FOLDER, 'Templateimages')
BUCKET_NAME = 'compoundfoundry'

# Create dated subfolders (naming format: YYYY-MM-DD_HH-MM-SS)
current_date = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
download_folder = os.path.join(DOWNLOAD_BASE_FOLDER, current_date)
output_folder = os.path.join(OUTPUT_BASE_FOLDER, current_date)
os.makedirs(download_folder, exist_ok=True)
os.makedirs(output_folder, exist_ok=True)

print(f"Base folder: {BASE_FOLDER}")
print(f"Download folder: {download_folder}")
print(f"Output folder: {output_folder}")

def download_and_tile_image(url, filename, tile_size, max_retries=3):
    """Download an image and create a tiled version with retry logic."""
    for attempt in range(max_retries):
        try:
            logger.info(f"Downloading image from {url} (attempt {attempt+1}/{max_retries})")
            response = requests.get(url, timeout=30)  # Increased timeout
            response.raise_for_status()
            
            original_file_path = os.path.join(download_folder, f"{filename}.png")
            
            with open(original_file_path, 'wb') as f:
                f.write(response.content)
            logger.info(f"Image saved to {original_file_path}")
            
            # Verify the file exists and is a valid image
            try:
                original_image = Image.open(original_file_path)
                width, height = original_image.size
                
                # Create the tiled image
                tiled_image = Image.new('RGB', (width * tile_size, height * tile_size))
                for i in range(tile_size):
                    for j in range(tile_size):
                        tiled_image.paste(original_image, (i * width, j * height))
                
                tiled_filename = f"{filename}_{tile_size}.png"
                tiled_file_path = os.path.join(download_folder, tiled_filename)
                tiled_image.save(tiled_file_path)
                logger.info(f"Tiled image saved to {tiled_file_path}")
                return tiled_file_path
            except Exception as e:
                logger.error(f"Error processing downloaded image: {e}")
                # If we can't open it as an image, remove the file and retry
                if os.path.exists(original_file_path):
                    os.remove(original_file_path)
                raise
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download {filename} (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                # Wait before retrying with exponential backoff
                wait_time = 2 ** attempt
                logger.info(f"Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
            else:
                logger.error(f"Max retries reached for {filename}, giving up.")
                return None
        except Exception as e:
            logger.error(f"Error processing image {filename} (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.info(f"Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
            else:
                logger.error(f"Max retries reached for {filename}, giving up.")
                return None
    
    return None

def upload_to_s3_and_make_public(local_file, bucket_name, s3_key, max_retries=3):
    """Upload file to S3 and set ACL to public-read with retry logic."""
    if not os.path.exists(local_file):
        logger.error(f"ERROR: File not found for upload: {local_file}")
        return None
        
    for attempt in range(max_retries):
        try:
            logger.info(f"Uploading {local_file} to S3 bucket {bucket_name}... (attempt {attempt+1}/{max_retries})")
            content_type = 'image/png' if local_file.lower().endswith('.png') else 'application/octet-stream'
            extra_args = {'ACL': 'public-read', 'ContentType': content_type}
            
            s3.upload_file(local_file, bucket_name, s3_key, ExtraArgs=extra_args)
            
            # Verify the upload was successful by checking if the object exists
            try:
                s3.head_object(Bucket=bucket_name, Key=s3_key)
                location = s3.get_bucket_location(Bucket=bucket_name)['LocationConstraint']
                if location is None:
                    location = 'us-east-1'
                url = f"https://{bucket_name}.s3-{location}.amazonaws.com/{s3_key}"
                logger.info(f"Uploaded to {url}")
                return url
            except Exception as e:
                logger.error(f"Upload verification failed: {e}")
                raise
                
        except Exception as e:
            logger.error(f"Upload error (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.info(f"Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
            else:
                logger.error(f"Max retries reached for upload, giving up.")
                return None
    
    return None

def run_photoshop_jsx(max_retries=2):
    """Run the Photoshop JSX script with retry logic."""
    for attempt in range(max_retries):
        try:
            logger.info(f"Running Photoshop JSX script... (attempt {attempt+1}/{max_retries})")
            
            # Try to find Photoshop executable in common locations
            possible_photoshop_paths = [
                r"C:\Program Files\Adobe\Adobe Photoshop 2025\Photoshop.exe",
                r"C:\Program Files\Adobe\Adobe Photoshop 2024\Photoshop.exe",
                r"C:\Program Files\Adobe\Adobe Photoshop 2023\Photoshop.exe",
                r"C:\Program Files (x86)\Adobe\Adobe Photoshop 2025\Photoshop.exe",
                r"C:\Program Files (x86)\Adobe\Adobe Photoshop 2024\Photoshop.exe",
                r"C:\Program Files (x86)\Adobe\Adobe Photoshop 2023\Photoshop.exe"
            ]
            
            photoshop_exe = None
            for path in possible_photoshop_paths:
                if os.path.exists(path):
                    photoshop_exe = path
                    break
            
            if not photoshop_exe:
                logger.error("Could not find Photoshop executable in common locations")
                return False
                
            jsx_script_path = os.path.join(BASE_FOLDER, "Source3_1.jsx")
            
            # Debug output
            logger.info(f"Photoshop executable path: {photoshop_exe}")
            logger.info(f"JSX script path: {jsx_script_path}")
            logger.info(f"Checking if files exist:")
            logger.info(f"- Photoshop exists: {os.path.exists(photoshop_exe)}")
            logger.info(f"- JSX script exists: {os.path.exists(jsx_script_path)}")
            
            # Verify the script exists
            if not os.path.exists(jsx_script_path):
                logger.error(f"JSX script not found at {jsx_script_path}")
                return False
                
            logger.info("Starting Photoshop process...")
            # Use a timeout of 60 minutes
            process = subprocess.Popen(
                [photoshop_exe, '-r', jsx_script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=BASE_FOLDER  # Set working directory to script directory
            )
            
            try:
                stdout, stderr = process.communicate(timeout=3600)  # 60 minute timeout
                logger.info(f"Photoshop process output: {stdout.decode() if stdout else ''}")
                if stderr:
                    logger.error(f"Photoshop process errors: {stderr.decode()}")
                logger.info(f"Photoshop script finished with return code: {process.returncode}")
                
                if process.returncode == 0:
                    return True
                else:
                    logger.error(f"Photoshop process returned non-zero exit code: {process.returncode}")
                    if attempt < max_retries - 1:
                        logger.info("Retrying Photoshop process...")
                        time.sleep(5)
                    else:
                        logger.error("Max retries reached for Photoshop process")
                        return False
                        
            except subprocess.TimeoutExpired:
                logger.error("Photoshop process timed out after 60 minutes")
                process.kill()
                return False
                
        except Exception as e:
            logger.error(f"Error running Photoshop script: {str(e)}")
            if attempt < max_retries - 1:
                logger.info("Retrying Photoshop process...")
                time.sleep(5)
            else:
                logger.error("Max retries reached for Photoshop process")
                return False
    
    return False

def upload_photoshop_outputs(output_folder):
    """Scan the Output folder for image files and upload them to S3."""
    uploaded_files = []
    logger.info(f"Scanning {output_folder} for output files...")
    
    # Reduced wait time - check more frequently but for less total time
    wait_attempts = 0
    max_wait_attempts = 15  # Wait up to 2.5 minutes (10s intervals)
    
    # Wait for files to appear if the folder is empty initially
    files_found = []
    while wait_attempts < max_wait_attempts:
        files_found = []
        for root, dirs, files in os.walk(output_folder):
            files_found.extend([f for f in files if f.endswith(('.png', '.jpg', '.jpeg'))])
        
        if files_found:
            logger.info(f"Found {len(files_found)} files to upload")
            break
            
        logger.info(f"No output files found yet in {output_folder}, waiting (attempt {wait_attempts+1}/{max_wait_attempts})...")
        time.sleep(10)  # Wait 10 seconds between checks
        wait_attempts += 1
    
    if not files_found:
        logger.warning(f"WARNING: No output files found in {output_folder} after {max_wait_attempts * 10} seconds!")
    
    # Optimize upload loop - group files by directory to reduce redundant walks
    files_by_directory = {}
    for root, dirs, files in os.walk(output_folder):
        image_files = [f for f in files if f.endswith(('.png', '.jpg', '.jpeg'))]
        if image_files:
            files_by_directory[root] = image_files
    
    # Batch uploads from each directory
    for directory, files in files_by_directory.items():
        logger.info(f"Processing {len(files)} files from {directory}")
        for file in files:
            local_file_path = os.path.join(directory, file)
            s3_key = f"wrappingpaper/new_uploads/{file}"
            uploaded_url = upload_to_s3_and_make_public(local_file_path, BUCKET_NAME, s3_key)
            if uploaded_url:
                uploaded_files.append({
                    "file": file,
                    "url": uploaded_url,
                    "type": "photoshop_output"
                })
    
    logger.info(f"Uploaded {len(uploaded_files)} Photoshop output files to S3")
    return uploaded_files

def process_bags(csv_data, download_folder):
    """Process images through Bags.py to create bag mockups"""
    logger.info("Starting bag processing...")
    
    # Create temporary CSV file with URLs and names
    temp_csv_path = os.path.join(download_folder, "temp_bags_input.csv")
    with open(temp_csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['URL', 'Name'])
        
        # Parse the CSV data
        csv_reader = csv.reader(io.StringIO(csv_data.replace('\\n', '\n')))
        for row in csv_reader:
            if len(row) >= 2:
                url = row[0].strip()
                name = row[1].strip()
                writer.writerow([url, name])
    
    # Import and run bag processing function
    try:
        # Create a bags output folder
        bags_output_folder = os.path.join(output_folder, "bags")
        os.makedirs(bags_output_folder, exist_ok=True)
        
        # Import Bags module from the new location
        sys.path.append(BASE_FOLDER)
        from Bags_1 import process_bags_internal
        
        # Run bag processing
        logger.info(f"Calling bag processing with CSV: {temp_csv_path}, output folder: {bags_output_folder}")
        bag_results = process_bags_internal(temp_csv_path, bags_output_folder)
        logger.info(f"Bag processing complete. Generated {len(bag_results)} files.")
        
        # Verify all bag output files exist
        valid_results = []
        for file_path in bag_results:
            if os.path.exists(file_path):
                valid_results.append(file_path)
            else:
                logger.warning(f"WARNING: Bag output file not found: {file_path}")
        
        logger.info(f"Verified {len(valid_results)} valid bag output files")
        return valid_results
    except Exception as e:
        logger.error(f"Error during bag processing: {e}")
        traceback.print_exc()
        return []

def save_urls_to_csv(products):
    """Save processed product URLs to a CSV file."""
    try:
        # Use the CSV folder in the script directory
        csv_dir = os.path.join(BASE_FOLDER, 'csv')
        csv_path = os.path.join(csv_dir, 'meta_file_list.csv')
        
        # Ensure the directory exists
        os.makedirs(csv_dir, exist_ok=True)
        
        # Write the CSV file
        with open(csv_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Name', 'LocalPath'])  # Header row
            
            for product in products:
                if 'local_path' in product:
                    writer.writerow([product['name'], product['local_path']])
        
        logger.info(f"Saved CSV file to: {csv_path}")
        return csv_path
    except Exception as e:
        logger.error(f"Error saving CSV file: {e}")
        raise

def process_images(csv_data):
    try:
        # Parse CSV data
        csv_reader = csv.reader(io.StringIO(csv_data))
        products = []
        
        for row in csv_reader:
            if len(row) >= 2:
                url, name = row[0].strip(), row[1].strip()
                if url and name:
                    logger.info(f"Processing image: URL = {url}, Name = {name}")
                    
                    try:
                        # Download and tile the image
                        tiled_path = download_and_tile_image(url, name, 6)
                        if not tiled_path:
                            logger.error(f"Failed to download and tile image for {name}")
                            continue
                            
                        # Copy to output folder
                        output_path = os.path.join(output_folder, f"{name}.png")
                        shutil.copy2(tiled_path, output_path)
                        logger.info(f"Tiled image copied to output folder: {output_path}")
                        
                        # Upload tiled version to S3
                        s3_key = f"wrappingpaper/new_uploads/{name}_6.png"
                        s3_url = upload_to_s3_and_make_public(tiled_path, BUCKET_NAME, s3_key)
                        if s3_url:
                            logger.info(f"Uploaded tiled design to {s3_url}")
                            products.append({
                                "name": name,
                                "handle": name.lower().replace(' ', '-').replace(',', ''),
                                "s3_url": s3_url
                            })
                    except Exception as e:
                        logger.error(f"Error processing {name}: {e}")
                        logger.error(traceback.format_exc())
                        continue
        
        if not products:
            logger.error("No products were successfully processed")
            return False
            
        # Run Photoshop processing
        logger.info("Starting Photoshop JSX processing...")
        if not run_photoshop_jsx():
            logger.error("Photoshop processing failed")
            return False
            
        logger.info("PHOTOSHOP_COMPLETE")
        
        # Create CSV for Illustrator
        csv_path = os.path.join(BASE_FOLDER, 'printpanels', 'csv', 'meta_file_list.csv')
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            for product in products:
                writer.writerow([product['name']])
        
        logger.info(f"Saved CSV file to: {csv_path}")
        
        # Print JSON output for server
        print("JSON_OUTPUT_START")
        print(json.dumps(products))
        print("JSON_OUTPUT_END")
        
        return True
            
    except Exception as e:
        logger.error(f"Error in process_images: {e}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: No CSV data provided")
        sys.exit(1)
        
    csv_data = sys.argv[1]
    success = process_images(csv_data)
    sys.exit(0 if success else 1)