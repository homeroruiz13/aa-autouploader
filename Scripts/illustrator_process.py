#!C:\Program Files\Python313\python.exe
import os
import subprocess
import time
from datetime import datetime
import boto3
from botocore.exceptions import NoCredentialsError
import sys
import json
import csv
from dotenv import load_dotenv
import logging
import re
import requests

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# AWS S3 Configuration using environment variables
s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION', 'us-east-2')
)

# Constants
BUCKET_NAME = 'aspenarlo'
BASE_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_OUTPUT_FOLDER = os.path.join(BASE_FOLDER, 'printpanels', 'output')

# Load Shopify credentials from environment variables
SHOPIFY_API_KEY = os.getenv('SHOPIFY_API_KEY')
SHOPIFY_PASSWORD = os.getenv('SHOPIFY_PASSWORD')
SHOPIFY_STORE_NAME = os.getenv('SHOPIFY_STORE')
SHOPIFY_API_VERSION = os.getenv('SHOPIFY_API_VERSION', '2025-01')  # Default to 2025-01

# Validate that all necessary env vars are set
if not all([SHOPIFY_API_KEY, SHOPIFY_PASSWORD, SHOPIFY_STORE_NAME]):
    raise RuntimeError("Missing one or more required Shopify environment variables: SHOPIFY_API_KEY, SHOPIFY_PASSWORD, SHOPIFY_STORE")

SHOPIFY_API_BASE = f"https://{SHOPIFY_STORE_NAME}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}"
SHOPIFY_HEADERS = {
    'X-Shopify-Access-Token': SHOPIFY_PASSWORD,
    'Content-Type': 'application/json'
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("illustrator_process.log"),
        logging.StreamHandler()
    ]
)

def create_dated_output_folder():
    """Create a new output folder with current date and time."""
    current_date = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    output_folder = os.path.join(BASE_OUTPUT_FOLDER, current_date)
    os.makedirs(output_folder, exist_ok=True)
    logging.info(f"Created output folder: {output_folder}")
    return output_folder

def get_latest_download_dir():
    """Get the most recent download directory."""
    download_dir = os.path.join(BASE_FOLDER, 'Download')
    if not os.path.exists(download_dir):
        logging.error(f"Download directory not found: {download_dir}")
        return None
        
    # Get all timestamped directories (format: YYYY-MM-DD_HH-MM-SS)
    dirs = []
    for d in os.listdir(download_dir):
        full_path = os.path.join(download_dir, d)
        if os.path.isdir(full_path) and d[0].isdigit():  # Only consider timestamped directories
            try:
                # Parse timestamp to ensure it's valid
                datetime.strptime(d, "%Y-%m-%d_%H-%M-%S")
                dirs.append(d)
            except ValueError:
                continue  # Skip directories that don't match timestamp format
    
    if not dirs:
        logging.error("No timestamped download directories found")
        return None
        
    # Sort by timestamp (newest first)
    dirs.sort(reverse=True)
    latest_dir = os.path.join(download_dir, dirs[0])
    logging.info(f"Using download directory: {latest_dir}")
    return latest_dir

def derive_handle(product_name: str) -> str:
    """Convert product name to handle format (kebab-case)."""
    slug = re.sub(r'[^a-z0-9]+', '-', product_name.lower())
    return slug.strip('-')

def process_csv(csv_path):
    """Process the CSV file and return image paths."""
    try:
        logging.info(f"Processing CSV: {csv_path}")
        
        # Get the latest download directory
        download_dir = get_latest_download_dir()
        if not download_dir:
            return []
        
        # Debug: List all files in the download directory
        logging.info(f"Files in download directory:")
        try:
            all_files = os.listdir(download_dir)
            png_files = [f for f in all_files if f.endswith('.png')]
            logging.info(f"Found {len(png_files)} PNG files in download directory:")
            for file in png_files:
                logging.info(f"  - {file}")
        except Exception as e:
            logging.error(f"Error listing download directory: {e}")
            
        # Process the CSV - handle both formats:
        # Format 1: Just product names (current): productname
        # Format 2: URL + ProductName: url,productname,tags...
        image_paths = []
        with open(csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            row_count = 0
            for row in reader:
                row_count += 1
                logging.info(f"Processing CSV row {row_count}: {row}")
                
                if len(row) >= 1 and row[0].strip():  # At least one column with content
                    # Determine CSV format
                    if len(row) >= 2 and row[0].startswith('http'):
                        # Format 2: URL, ProductName, Tags...
                        url = row[0].strip()
                        product_name = row[1].strip()
                        logging.info(f"Found URL+ProductName format: '{product_name}' from {url}")
                    else:
                        # Format 1: Just product name
                        product_name = row[0].strip()
                        url = None
                        logging.info(f"Found ProductName-only format: '{product_name}'")
                    
                    if product_name:
                        logging.info(f"Looking for local image for product: '{product_name}'")

                        # Create possible filename variations
                        possible_names = []
                        
                        # 1. Exact product name (as-is)
                        possible_names.append(product_name)
                        
                        # 2. Original product name as handle
                        handle = derive_handle(product_name)
                        possible_names.append(handle)
                        
                        # 3. If we have S3 URL, extract filename from it
                        if url and 'wrappingpaper/new_uploads/' in url:
                            s3_filename = url.split('/')[-1]  # Get filename from URL
                            base_name = os.path.splitext(s3_filename)[0]  # Remove .png extension
                            possible_names.append(base_name)
                            
                        # 4. Try to get AA ID from Shopify
                        try:
                            aa_id = _fetch_aa_id(handle)
                            if aa_id:
                                possible_names.append(aa_id)
                                possible_names.append(f"{aa_id}06")
                        except Exception as e:
                            logging.debug(f"Shopify lookup failed for {handle}: {e}")
                        
                        # 5. Extract any AA ID from product name
                        aa_match = re.search(r"AA\d{6,8}", product_name, re.IGNORECASE)
                        if aa_match:
                            aa_id = aa_match.group(0).upper()
                            possible_names.append(aa_id)
                            possible_names.append(f"{aa_id}06")
                        
                        # Remove duplicates while preserving order
                        seen = set()
                        unique_names = []
                        for pname in possible_names:
                            if pname and pname not in seen:
                                seen.add(pname)
                                unique_names.append(pname)
                        
                        logging.info(f"Searching for filename variations: {unique_names}")
                        
                        # Search for the image file
                        found = False
                        for pname in unique_names:
                            if found:
                                break
                                
                            # Try different variations
                            variations = [
                                f"{pname}_6.png",    # 6x6 tiled version (most common for PDF generation)
                                f"{pname}.png",      # Original
                                f"{pname}_6.jpg",
                                f"{pname}.jpg",
                            ]
                            
                            for variation in variations:
                                image_path = os.path.join(download_dir, variation)
                                logging.debug(f"  Checking: {variation}")
                                if os.path.exists(image_path):
                                    image_paths.append(image_path)
                                    logging.info(f"Found image: {image_path}")
                                    found = True
                                    break

                        if not found:
                            logging.warning(f"No local image found for: {product_name}")
                            logging.warning(f"  Tried variations: {unique_names}")
                            
                            # As a fallback, try to download from S3 URL if available
                            if url:
                                try:
                                    logging.info(f"Attempting to download from S3: {url}")
                                    temp_filename = f"{handle}_6.png"
                                    temp_path = os.path.join(download_dir, temp_filename)
                                    
                                    response = requests.get(url, timeout=30)
                                    response.raise_for_status()
                                    
                                    with open(temp_path, 'wb') as f:
                                        f.write(response.content)
                                    
                                    image_paths.append(temp_path)
                                    logging.info(f"Downloaded and saved: {temp_path}")
                                    found = True
                                    
                                except Exception as download_error:
                                    logging.error(f"Failed to download {url}: {download_error}")
                            else:
                                logging.warning(f"No S3 URL available for fallback download")
        
        logging.info(f"Found {len(image_paths)} valid image paths out of {row_count} CSV rows")
        
        # Debug: Show what we found
        for path in image_paths:
            logging.info(f"  Valid image: {os.path.basename(path)}")
        
        return image_paths
        
    except Exception as e:
        logging.error(f"Error processing CSV: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return []

def run_pdf_generation(image_paths):
    """Run the PDF generator and return the root output folder if successful."""
    try:
        # Directory containing this script:  .../aa-auto/Scripts
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # The new generator sits one level above Scripts
        pdf_script = os.path.abspath(os.path.join(script_dir, "..", "wrapping_paper_pdf_generator.py"))

        if not os.path.exists(pdf_script):
            logging.error(f"PDF generator script not found: {pdf_script}")
            return None

        # Create output directory with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        base_output_dir = os.path.join(script_dir, "..", "printpanels", "output", timestamp)
        base_output_dir = os.path.abspath(base_output_dir)
        os.makedirs(base_output_dir, exist_ok=True)
        logging.info(f"Created base output folder: {base_output_dir}")

        footer_path = os.path.abspath(os.path.join(script_dir, "..", "Footer.pdf"))

        # Helper to invoke the generator
        def _run_generator(extra_flags: list[str], subfolder_name: str) -> bool:
            out_dir = os.path.join(base_output_dir, subfolder_name)
            os.makedirs(out_dir, exist_ok=True)

            cmd = [
                sys.executable,
                pdf_script,
                *image_paths,
                "--output-dir",
                out_dir,
                "--footer",
                footer_path,
                *extra_flags,
            ]
            label = "TABLERUNNER" if "--tablerunner" in extra_flags else "WRAPPING"
            logging.info(f"Launching PDF generator for {label}: {' '.join(cmd)}")

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=out_dir,
            )
            stdout, stderr = proc.communicate()
            if stdout:
                for line in stdout.splitlines():
                    logging.info(line)
            if stderr:
                for line in stderr.splitlines():
                    logging.error(line)
            if proc.returncode != 0:
                logging.error(f"Generator returned non-zero exit code ({proc.returncode}) for {label}")
                return False
            return True

        ok_wrap = _run_generator([], "WrappingPaper")
        ok_tr   = _run_generator(["--tablerunner"], "Tablerunner")

        return base_output_dir if (ok_wrap and ok_tr) else None

    except Exception as e:
        logging.error(f"Error running PDF generation: {e}")
        return None

def upload_to_s3(local_file, bucket_name, s3_key):
    """Upload a file to S3 and make it public."""
    try:
        logging.info(f"Uploading {local_file} to S3 bucket {bucket_name}...")
        extra_args = {'ACL': 'public-read', 'ContentType': 'application/pdf'}
        s3.upload_file(local_file, bucket_name, s3_key, ExtraArgs=extra_args)
        location = s3.get_bucket_location(Bucket=bucket_name)['LocationConstraint']
        if location is None:
            location = 'us-east-1'
        url = f"https://{bucket_name}.s3-{location}.amazonaws.com/{s3_key}"
        logging.info(f"Uploaded successfully to {url}")
        return url
    except FileNotFoundError:
        logging.error(f"File {local_file} not found.")
        return None
    except NoCredentialsError:
        logging.error("AWS credentials not available.")
        return None
    except Exception as e:
        logging.error(f"Error during upload: {e}")
        return None

def process_and_upload_files(output_folder):
    """Process PDF files in the output folder and upload to S3."""
    uploaded_files = []
    for root, dirs, files in os.walk(output_folder):
        for file in files:
            if file.endswith(".pdf"):
                local_file_path = os.path.join(root, file)

                # Build S3 key: prefer AA id prefix when available so files
                # become AA12345606.pdf instead of pattern slug.

                basename = os.path.splitext(file)[0]
                # extract trailing two-digit code (06/15/71/72) if present
                suffix = basename[-2:] if len(basename) > 2 and basename[-2:].isdigit() else ''
                prefix = basename[:-2] if suffix else basename

                aa_id = None
                if not (prefix.upper().startswith('AA') and prefix[2:].isdigit()):
                    aa_id = _get_aa_id_for_handle(prefix)

                if aa_id:
                    s3_filename = f"{aa_id}{suffix}.pdf" if suffix else f"{aa_id}.pdf"
                else:
                    s3_filename = file  # keep original

                s3_key = f"PrintFiles/{s3_filename}"

                uploaded_url = upload_to_s3(local_file_path, BUCKET_NAME, s3_key)
                if uploaded_url:
                    uploaded_files.append({
                        "file": file,
                        "url": uploaded_url,
                        "type": "print_panel"
                    })
    return uploaded_files

def _fetch_aa_id(handle: str) -> str | None:
    try:
        url = f"{SHOPIFY_API_BASE}/products.json?handle={handle}"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        products = r.json().get('products', [])
        if not products:
            return None
        pid = products[0]['id']
        mf_url = f"{SHOPIFY_API_BASE}/products/{pid}/metafields.json"
        mfr = requests.get(mf_url, timeout=10)
        mfr.raise_for_status()
        for mf in mfr.json().get('metafields', []):
            if mf.get('namespace') == 'custom' and mf.get('key') in ('basesku', 'base_sku'):
                val = mf.get('value', '').strip().upper()
                if val.startswith('AA') and val[2:].isdigit():
                    return val
        return None
    except Exception:
        return None

def _get_aa_id_for_handle(handle: str) -> str | None:
    """Return AA###### from custom.basesku or None."""
    try:
        resp = requests.get(f"{SHOPIFY_API_BASE}/products.json?handle={handle}", headers=SHOPIFY_HEADERS, timeout=15)
        resp.raise_for_status()
        products = resp.json().get('products', [])
        if not products:
            return None
        product_id = products[0]['id']
        mf_resp = requests.get(f"{SHOPIFY_API_BASE}/products/{product_id}/metafields.json", headers=SHOPIFY_HEADERS, timeout=15)
        mf_resp.raise_for_status()
        for mf in mf_resp.json().get('metafields', []):
            if mf.get('namespace') == 'custom' and mf.get('key') in ('basesku', 'base_sku'):
                val = mf.get('value', '').strip().upper()
                if val.startswith('AA') and val[2:].isdigit():
                    return val
        return None
    except Exception:
        return None

def main():
    if len(sys.argv) < 2:
        logging.error("Usage: python illustrator_process.py <csv_path>")
        sys.exit(1)
        
    csv_path = sys.argv[1]
    if not os.path.exists(csv_path):
        logging.error(f"CSV file not found: {csv_path}")
        sys.exit(1)
        
    # Process CSV and get image paths
    image_paths = process_csv(csv_path)
    if not image_paths:
        logging.error("No valid image paths found")
        sys.exit(1)
        
    # Run PDF generation
    output_folder = run_pdf_generation(image_paths)
    if output_folder:
        logging.info("PDF generation completed successfully")
        # Upload PDFs to S3 PrintFiles folder
        process_and_upload_files(output_folder)
        sys.exit(0)
    else:
        logging.error("PDF generation failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
