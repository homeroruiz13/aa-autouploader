#!C:\Program Files\Python313\python.exe
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
from dotenv import load_dotenv
import time
import logging
import tempfile
from pathlib import Path
from botocore.exceptions import ClientError
from config import BASE_FOLDER, DOWNLOAD_BASE_FOLDER, OUTPUT_BASE_FOLDER, BUCKET_NAME
import shutil
import re
from bag_s3_uploader import upload_bag_files_to_s3
from tissue_s3_uploader import upload_tissue_files_to_s3
from tablerunner_s3_uploader import upload_tablerunner_files_to_s3  # NEW: Added table runner uploader import
import traceback

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# Initialize the boto3 S3 client using environment variables
s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION', 'us-east-2')
)

# Create dated subfolders (naming format: YYYY-MM-DD_HH-MM-SS)
current_date = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
download_folder = os.path.join(DOWNLOAD_BASE_FOLDER, current_date)
output_folder = os.path.join(OUTPUT_BASE_FOLDER, current_date)
os.makedirs(download_folder, exist_ok=True)
os.makedirs(output_folder, exist_ok=True)

print(f"Download folder: {download_folder}")
print(f"Output folder: {output_folder}")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Load Shopify credentials from environment variables to avoid committing secrets
SHOPIFY_API_KEY = os.getenv('SHOPIFY_API_KEY')
SHOPIFY_PASSWORD = os.getenv('SHOPIFY_PASSWORD')
SHOPIFY_STORE_NAME = os.getenv('SHOPIFY_STORE')
SHOPIFY_API_VERSION = os.getenv('SHOPIFY_API_VERSION', '2025-01')  # Default to 2025-01

# Construct the base URL only if all variables are present
if not all([SHOPIFY_API_KEY, SHOPIFY_PASSWORD, SHOPIFY_STORE_NAME]):
    raise RuntimeError("Missing one or more required Shopify environment variables: SHOPIFY_API_KEY, SHOPIFY_PASSWORD, SHOPIFY_STORE")

SHOPIFY_API_BASE = f"https://{SHOPIFY_STORE_NAME}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}"
SHOPIFY_HEADERS = {
    'X-Shopify-Access-Token': SHOPIFY_PASSWORD,
    'Content-Type': 'application/json'
}

# --------------------------------------------------------------
# Helper: derive Shopify-style handle from a product name
# (kebab-case, only a-z and 0-9, repeated separators collapsed)
# --------------------------------------------------------------

def derive_handle(product_name: str) -> str:
    """Convert *product_name* to the same handle/slug format that the
    web application and Shopify expect. Any sequence of non-alphanumeric
    characters is replaced by a single hyphen and leading/trailing hyphens
    are stripped.

    Example::

        >>> derive_handle('Home roo testing 2')
        'home-roo-testing-2'
    """
    slug = re.sub(r'[^a-z0-9]+', '-', product_name.lower())
    return slug.strip('-')

def find_photoshop():
    """Find the latest version of Photoshop installed."""
    possible_paths = [
        r"C:\Program Files\Adobe\Adobe Photoshop 2025\Photoshop.exe",
        r"C:\Program Files\Adobe\Adobe Photoshop 2024\Photoshop.exe",
        r"C:\Program Files\Adobe\Adobe Photoshop 2023\Photoshop.exe"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            logging.info(f"Found Photoshop at: {path}")
            return path
            
    raise FileNotFoundError("No Photoshop installation found")

def ensure_photoshop_closed():
    """Ensure Photoshop is completely closed."""
    try:
        subprocess.run(['taskkill', '/f', '/im', 'Photoshop.exe'], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE)
        time.sleep(2)  # Wait for process to fully terminate
    except subprocess.CalledProcessError:
        pass  # Photoshop might not be running

def run_photoshop_jsx():
    """Run the Photoshop JSX script with proper error handling."""
    try:
        ensure_photoshop_closed()
        
        photoshop_exe = find_photoshop()
        jsx_script_path = os.path.join(os.path.dirname(__file__), "source3.jsx")
        
        if not os.path.exists(jsx_script_path):
            raise FileNotFoundError(f"JSX script not found: {jsx_script_path}")
            
        logging.info("Running Photoshop JSX script...")
        process = subprocess.Popen(
            [photoshop_exe, '-r', jsx_script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        try:
            stdout, stderr = process.communicate(timeout=600)  # 10 minute timeout
            if process.returncode != 0:
                logging.error(f"Photoshop script failed with code {process.returncode}")
                logging.error(f"Error output: {stderr.decode()}")
                return False
                
            logging.info("Photoshop script finished successfully")
            return True
            
        except subprocess.TimeoutExpired:
            logging.error("Photoshop script timed out after 10 minutes")
            process.kill()
            return False
            
    except Exception as e:
        logging.error(f"Error running Photoshop script: {e}")
        return False
        
    finally:
        ensure_photoshop_closed()

def download_and_tile_image(url, name, tile_size):
    """Download and tile an image with proper error handling."""
    try:
        print(f"Downloading image from {url}")
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        image_path = os.path.join(download_folder, f"{name}.png")
        with open(image_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        print(f"Image saved to {image_path}")
        
        # Create tiled version
        tiled_path = os.path.join(download_folder, f"{name}_{tile_size}.png")
        original_image = Image.open(image_path)
        width, height = original_image.size
        tiled_image = Image.new('RGB', (width * tile_size, height * tile_size))
        for i in range(tile_size):
            for j in range(tile_size):
                tiled_image.paste(original_image, (i * width, j * height))
        tiled_image.save(tiled_path)
        print(f"Tiled image saved to {tiled_path}")
        
        return tiled_path
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Error downloading image {name}: {e}")
        return None
    except Exception as e:
        logging.error(f"Error processing image {name}: {e}")
        return None

def upload_to_s3_and_make_public(local_file, bucket_name, s3_key):
    """Upload file to S3 and set ACL to public-read."""
    try:
        print(f"Uploading {local_file} to S3 bucket {bucket_name}...")
        extra_args = {'ACL': 'public-read', 'ContentType': 'image/png'}
        s3.upload_file(local_file, bucket_name, s3_key, ExtraArgs=extra_args)
        location = s3.get_bucket_location(Bucket=bucket_name)['LocationConstraint']
        if location is None:
            location = 'us-east-1'
        # Append a unix timestamp query param so browsers always fetch the
        # latest upload instead of serving a cached copy.
        timestamp = int(datetime.now().timestamp())
        url = f"https://{bucket_name}.s3-{location}.amazonaws.com/{s3_key}?v={timestamp}"
        print(f"Uploaded to {url}")
        return url
    except Exception as e:
        print(f"Upload error: {e}")
        return None

def upload_photoshop_outputs(output_folder, aa_id: str | None = None):
    """Scan the Output folder for image files and upload them to S3."""
    uploaded_files = []
    print(f"Scanning {output_folder} for output files...")
    
    # Define the order of image types for consistent processing
    image_types = ['hero', 'rolled', '011', '05-(2)', '04-(2)', 'bag1', 'bag2', 'bag3', 'tissue1', 'tissue2', 'tissue3', 'tablerunner1', 'tablerunner2', 'tablerunner3']
    
    # First, collect all files and sort them by type
    files_by_type = {type: [] for type in image_types}
    for root, dirs, files in os.walk(output_folder):
        for file in files:
            if file.endswith(('.png', '.jpg', '.jpeg')):
                # Determine the type of image
                image_type = None
                if '_6_hero.png' in file:
                    image_type = 'hero'
                elif '_rolled.png' in file:
                    image_type = 'rolled'
                elif '_011.png' in file:
                    image_type = '011'
                elif '_05-(2).png' in file:
                    image_type = '05-(2)'
                elif '_04-(2).png' in file:
                    image_type = '04-(2)'
                elif '_bag1.png' in file:
                    image_type = 'bag1'
                elif '_bag2.png' in file:
                    image_type = 'bag2'
                elif '_bag3.png' in file:
                    image_type = 'bag3'
                elif '_tissue1.png' in file:
                    image_type = 'tissue1'
                elif '_tissue2.png' in file:
                    image_type = 'tissue2'
                elif '_tissue3.png' in file:
                    image_type = 'tissue3'
                elif '_tablerunner1.png' in file:
                    image_type = 'tablerunner1'
                elif '_tablerunner2.png' in file:
                    image_type = 'tablerunner2'
                elif '_tablerunner3.png' in file:
                    image_type = 'tablerunner3'
                
                if image_type:
                    files_by_type[image_type].append(os.path.join(root, file))
    
    # Process files in the defined order
    for image_type in image_types:
        for file_path in files_by_type[image_type]:
            file_name = os.path.basename(file_path)
            # --- Rename outputs when the original prefix is an AA ID ---
            # The Photoshop output filenames are like '<prefix>_6_hero.png' or '<prefix>_6_011.png'.
            # If <prefix> looks like an AA product ID (aa123456) we convert it to uppercase and
            # remove the '_' before the tile size so the key becomes 'AA12345606_hero.png'.
            prefix, rest = file_name.split('_6_', 1) if '_6_' in file_name else (None, None)

            # If the caller provided an AA id we prefer that, otherwise we
            # fall back to any AA-looking prefix already present in the file
            # name.  If neither is available we keep the original name so
            # legacy products continue to work.

            chosen_aa = None
            if aa_id and aa_id.upper().startswith('AA') and aa_id[2:].isdigit():
                chosen_aa = aa_id.upper()
            elif prefix and prefix.lower().startswith('aa') and prefix[2:].isdigit():
                chosen_aa = prefix.upper()

            if chosen_aa and rest:
                s3_file_name = f"{chosen_aa}06_{rest}"
            else:
                s3_file_name = file_name

            s3_key = f"wrappingpaper/new_uploads/{s3_file_name}"
            uploaded_url = upload_to_s3_and_make_public(file_path, BUCKET_NAME, s3_key)
            if uploaded_url:
                uploaded_files.append({
                    "file": file_name,
                    "url": uploaded_url,
                    "type": "photoshop_output",
                    "image_type": image_type  # Add image type to the output
                })
    
    return uploaded_files

def fetch_aa_id_from_shopify(product_handle: str) -> str | None:
    """Return AA product ID (basesku metafield) for a Shopify product handle, or None."""
    try:
        url = f"{SHOPIFY_API_BASE}/products.json?handle={product_handle}"
        resp = requests.get(url, headers=SHOPIFY_HEADERS, timeout=15)
        resp.raise_for_status()
        products = resp.json().get('products', [])
        if not products:
            return None
        product_id = products[0]['id']
        metafields_url = f"{SHOPIFY_API_BASE}/products/{product_id}/metafields.json"
        mf_resp = requests.get(metafields_url, headers=SHOPIFY_HEADERS, timeout=15)
        mf_resp.raise_for_status()
        for mf in mf_resp.json().get('metafields', []):
            if mf.get('namespace') == 'custom' and mf.get('key') in ('basesku', 'base_sku'):
                val = mf.get('value', '').strip().upper()
                if val.startswith('AA') and val[2:].isdigit():
                    return val
        return None
    except Exception as _e:
        # Network issues should not break the whole pipeline – just ignore
        return None

def process_images(csv_data):
    """Process images with improved error handling and logging."""
    try:
        csv_data = csv_data.replace('\\n', '\n')
        csv_reader = csv.reader(io.StringIO(csv_data))
        processed_products = []
        
        for index, row in enumerate(csv_reader, start=1):
            if not row or len(row) < 2:
                logging.warning(f"Skipping line {index}: insufficient data {row}")
                continue
                
            url = row[0].strip()
            raw_sku = row[1].strip()

            # --------------------------------------------------------------
            # ALWAYS use a consistent, shop-style handle for *both* `handle`
            # and `base_sku` so every run of the same product name produces
            # identical filenames and S3 keys (e.g. "afinaltesting_6_hero.png").
            # --------------------------------------------------------------

            handle = derive_handle(raw_sku)

            # ----------------------------------------------------------
            # Attempt to fetch the previously-stored AA product id for
            # this pattern from Shopify.  If we find one it will become
            # the authoritative *base_sku* value for the remainder of
            # the pipeline (metafield update, S3 filenames, etc.).
            # ----------------------------------------------------------

            aa_id = fetch_aa_id_from_shopify(handle)

            # If Shopify returned something that looks like a valid AA id
            # ("AA" followed by 6 digits) we use that.  Otherwise we fall
            # back to the kebab-case handle which preserves legacy
            # behaviour for products that do not yet have an AA id.
            if aa_id:
                base_sku = aa_id
            else:
                base_sku = handle

            logging.info(f"Processing image {index}: URL = {url}, Raw SKU = '{raw_sku}', Base SKU = '{base_sku}'")
            
            try:
                # First, create the tiled image using the existing pipeline handle so downstream
                # processes (Photoshop, Illustrator, etc.) continue to work unchanged.
                image_path = download_and_tile_image(url, handle, 6)
                if not image_path:
                    continue
                    
                # Duplicate the tiled image so that a copy exists on disk using the base SKU name
                # (e.g. ABC_6.png). This satisfies the new requirement without disrupting the
                # existing naming convention that other scripts rely on.
                try:
                    # Keep base-SKU copies in a separate folder so they are not picked up by downstream
                    # Photoshop processing (which scans only the top-level of the Download folder).
                    base_dir = os.path.join(os.path.dirname(image_path), "tiles_by_sku")
                    os.makedirs(base_dir, exist_ok=True)
                    base_tiled_path = os.path.join(base_dir, f"{handle}_6.png")
                    if not os.path.exists(base_tiled_path):
                        shutil.copy2(image_path, base_tiled_path)
                        logging.info(f"Created base SKU copy: {base_tiled_path}")
                except Exception as copy_err:
                    logging.warning(f"Could not create base SKU copy for {raw_sku}: {copy_err}")
                    
                formatted_tile = f"{6:02d}"
                if base_sku.startswith('AA') and len(base_sku) >= 8 and base_sku[2:].isdigit():
                    # Use the AA product id directly, ensure it stays uppercase in the key
                    s3_filename = f"{base_sku}{formatted_tile}.png"
                else:
                    # Fallback to the previous handle logic (kebab-case name with _6)
                    s3_filename = f"{handle}_{6}.png"

                s3_key = f"wrappingpaper/new_uploads/{s3_filename}"
                uploaded_url = upload_to_s3_and_make_public(image_path, BUCKET_NAME, s3_key)
                
                if uploaded_url:
                    processed_products.append({
                        "name": raw_sku,
                        "handle": handle,  # Shopify/product handle
                        "base_sku": base_sku,
                        "s3_url": uploaded_url
                    })
                    
            except Exception as e:
                logging.error(f"Error processing {raw_sku}: {e}")
                continue
        
        if not processed_products:
            logging.error("No products were successfully processed")
            return
            
        logging.info("Starting Photoshop JSX processing...")
        photoshop_ok = run_photoshop_jsx()
        if not photoshop_ok:
            logging.error("Photoshop processing failed – continuing without Photoshop outputs")
        else:
            logging.info("PHOTOSHOP_COMPLETE")
            
            # ----------------------------------------------------------
            # Run dedicated bag-processing pipeline (creates 3×3 tiles,
            # runs bags.jsx and deposits *_bag1.png / *_bag2.png /
            # *_bag3.png files in the same Output/<ts> directory).
            # ----------------------------------------------------------

            try:
                logging.info("Starting bag processing…")
                bag_processor_path = os.path.join(os.path.dirname(__file__), "bag_processor.py")

                if os.path.exists(bag_processor_path):
                    result = subprocess.run([sys.executable, bag_processor_path],
                                            capture_output=True, text=True, timeout=900)

                    if result.returncode == 0:
                        logging.info("Bag processor finished successfully")
                        if result.stdout:
                            logging.debug(result.stdout)
                            
                        # Upload bag files to S3 with SKU naming convention
                        logging.info("Starting bag file upload to S3...")
                        try:
                            # Pass the products data so we can use the Shopify SKUs
                            bag_uploads = upload_bag_files_to_s3(output_folder, processed_products)
                            
                            if bag_uploads:
                                logging.info(f"Successfully uploaded {len(bag_uploads)} bag files to S3")
                                
                                # Log the SKUs for reference
                                for upload in bag_uploads:
                                    logging.info(f"Uploaded bag: {upload['sku']} -> {upload['public_url']}")
                                    
                                # Add bag upload info to processed products for tracking
                                for upload in bag_uploads:
                                    processed_products.append({
                                        "file": upload['original_file'],
                                        "url": upload['public_url'],
                                        "type": "bag_output",
                                        "sku": upload['sku'],
                                        "base_sku": upload['base_sku'],
                                        "bag_type": upload['bag_type'],
                                        "product_name": upload['product_name']
                                    })
                            else:
                                logging.warning("No bag files were uploaded to S3")
                                
                        except Exception as upload_error:
                            logging.error(f"Error uploading bag files to S3: {upload_error}")
                            # Don't fail the entire process if bag upload fails
                            
                    else:
                        logging.error(f"Bag processor exited with code {result.returncode}")
                        if result.stderr:
                            logging.error(result.stderr)
                else:
                    logging.warning(f"Bag processor script not found at {bag_processor_path}; skipping bag step")

                # Tissue processing
                logger.info("Starting tissue processing...")
                try:
                    # Get the script directory
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    tissue_processor_path = os.path.join(script_dir, "tissue_processor.py")
                    
                    if os.path.exists(tissue_processor_path):
                        # Run tissue processor as a subprocess
                        result = subprocess.run([
                            sys.executable, tissue_processor_path
                        ], capture_output=True, text=True, timeout=900)  # 15 minute timeout
                        
                        if result.returncode == 0:
                            logger.info("Tissue processing completed successfully")
                            
                            # Upload tissue files to S3 with SKUs
                            logger.info("Starting tissue file upload to S3...")
                            try:
                                # Pass the products data so we can use the Shopify SKUs
                                tissue_uploads = upload_tissue_files_to_s3(output_folder, processed_products)
                                
                                if tissue_uploads:
                                    logger.info(f"Successfully uploaded {len(tissue_uploads)} tissue files to S3")
                                    
                                    # Log the SKUs for reference
                                    for upload in tissue_uploads:
                                        logger.info(f"Uploaded tissue: {upload['sku']} -> {upload['public_url']}")
                                        
                                    # Add tissue upload info to processed products for tracking
                                    for upload in tissue_uploads:
                                        processed_products.append({
                                            "file": upload['original_file'],
                                            "url": upload['public_url'],
                                            "type": "tissue_output",
                                            "sku": upload['sku'],
                                            "base_sku": upload['base_sku'],
                                            "tissue_type": upload.get('tissue_type', 'unknown'),
                                            "product_name": upload['product_name']
                                        })
                                else:
                                    logger.warning("No tissue files were uploaded to S3")
                                    
                            except Exception as upload_error:
                                logger.error(f"Error uploading tissue files to S3: {upload_error}")
                        
                        else:
                            logger.error(f"Tissue processing failed with return code {result.returncode}")
                            logger.error(f"Tissue processor stderr: {result.stderr}")
                    else:
                        logger.warning(f"Tissue processor not found at: {tissue_processor_path}")
                        
                except subprocess.TimeoutExpired:
                    logger.error("Tissue processing timed out after 15 minutes")
                except Exception as e:
                    logger.error(f"Error in tissue processing: {e}")

                # NEW: Table runner processing
                logger.info("Starting table runner processing...")
                try:
                    # Get the script directory
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    tablerunner_processor_path = os.path.join(script_dir, "tablerunner_processor.py")
                    
                    if os.path.exists(tablerunner_processor_path):
                        # Run table runner processor as a subprocess
                        result = subprocess.run([
                            sys.executable, tablerunner_processor_path
                        ], capture_output=True, text=True, timeout=900)  # 15 minute timeout
                        
                        if result.returncode == 0:
                            logger.info("Table runner processing completed successfully")
                            
                            # Upload table runner files to S3 with SKUs
                            logger.info("Starting table runner file upload to S3...")
                            try:
                                # Pass the products data so we can use the Shopify SKUs
                                tablerunner_uploads = upload_tablerunner_files_to_s3(output_folder, processed_products)
                                
                                if tablerunner_uploads:
                                    logger.info(f"Successfully uploaded {len(tablerunner_uploads)} table runner files to S3")
                                    
                                    # Log the SKUs for reference
                                    for upload in tablerunner_uploads:
                                        logger.info(f"Uploaded table runner: {upload['sku']} -> {upload['public_url']}")
                                        
                                    # Add table runner upload info to processed products for tracking
                                    for upload in tablerunner_uploads:
                                        processed_products.append({
                                            "file": upload['original_file'],
                                            "url": upload['public_url'],
                                            "type": "tablerunner_output",
                                            "sku": upload['sku'],
                                            "base_sku": upload['base_sku'],
                                            "tablerunner_type": upload.get('tablerunner_type', 'unknown'),
                                            "product_name": upload['product_name']
                                        })
                                else:
                                    logger.warning("No table runner files were uploaded to S3")
                                    
                            except Exception as upload_error:
                                logger.error(f"Error uploading table runner files to S3: {upload_error}")
                        
                        else:
                            logger.error(f"Table runner processing failed with return code {result.returncode}")
                            logger.error(f"Table runner processor stderr: {result.stderr}")
                    else:
                        logger.warning(f"Table runner processor not found at: {tablerunner_processor_path}")
                        
                except subprocess.TimeoutExpired:
                    logger.error("Table runner processing timed out after 15 minutes")
                except Exception as e:
                    logger.error(f"Error in table runner processing: {e}")
                    # Don't fail the entire process if table runner processing fails

                # After all Photoshop work (regular + (attempted) bags + tissue + table runners) is done,
                # upload every PNG once so there are no duplicates.
                all_outputs = upload_photoshop_outputs(
                    output_folder,
                    aa_id=base_sku if base_sku.startswith('AA') else None
                )
                processed_products.extend(all_outputs)

            except subprocess.TimeoutExpired:
                logging.error("Bag processor timed-out after 15 minutes – continuing without bag outputs")
            except Exception as bag_err:
                logging.error(f"Unexpected error while running bag processor: {bag_err}")

        # Create CSV file list
        csv_path = os.path.join(BASE_FOLDER, 'printpanels', 'csv', 'meta_file_list.csv')
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            for product in processed_products:
                if 'name' in product:  # Only write products with names (not individual file uploads)
                    writer.writerow([product['name']])
        
        logger.info(f"Saved CSV file to: {csv_path}")

        # Even if Photoshop failed we still want to emit whatever information we collected so
        # that the rest of the pipeline (Illustrator print-panel generation, etc.) can proceed.
        # Without this the calling Node process treats the run as a total failure.
        print("JSON_OUTPUT_START")
        print(json.dumps(processed_products))
        print("JSON_OUTPUT_END")

        # If Photoshop *did* fail we return a non-zero exit code so the caller can decide whether
        # that is fatal or not, but we have already given it the data it needs.
        if not photoshop_ok:
            sys.exit(2)
        return

    except Exception as e:
        logger.error(f"Error in process_images: {e}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    try:
        if len(sys.argv) < 2:
            print("Usage: python images.py <csv_data>")
            sys.exit(1)
            
        process_images(sys.argv[1])
        
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)
        
    finally:
        ensure_photoshop_closed()
