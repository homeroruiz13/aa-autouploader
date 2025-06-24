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
load_dotenv()

# AWS S3 Configuration using environment variables
s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION', 'us-east-2')
)

# Constants with updated paths
BUCKET_NAME = 'compoundfoundry'
BASE_OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), 'printpanels', 'output')

# Load Shopify credentials from environment variables
SHOPIFY_API_KEY = os.getenv('SHOPIFY_API_KEY')
SHOPIFY_PASSWORD = os.getenv('SHOPIFY_PASSWORD')
SHOPIFY_STORE_NAME = os.getenv('SHOPIFY_STORE')

# Validate env vars
if not all([SHOPIFY_API_KEY, SHOPIFY_PASSWORD, SHOPIFY_STORE_NAME]):
    raise RuntimeError("Missing one or more required Shopify environment variables: SHOPIFY_API_KEY, SHOPIFY_PASSWORD, SHOPIFY_STORE")

SHOPIFY_API_BASE = f"https://{SHOPIFY_API_KEY}:{SHOPIFY_PASSWORD}@{SHOPIFY_STORE_NAME}.myshopify.com/admin/api/2023-04"

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
    current_date = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')  # Added hours, minutes, seconds
    output_folder = os.path.join(BASE_OUTPUT_FOLDER, current_date)
    os.makedirs(output_folder, exist_ok=True)
    print(f"Created output folder: {output_folder}")
    return output_folder

def detect_csv_delimiter(csv_path):
    """Detect the delimiter used in the CSV file."""
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            sample = f.read(1024)
            dialect = csv.Sniffer().sniff(sample)
            return dialect.delimiter
    except Exception as e:
        logging.warning(f"Could not detect CSV delimiter, defaulting to comma: {e}")
        return ','

def process_csv(csv_path):
    """Process the CSV file and return image paths."""
    try:
        logging.info(f"Processing CSV: {csv_path}")
        
        # Read CSV to determine delimiter
        with open(csv_path, 'r') as f:
            sample = f.read(1024)
            dialect = csv.Sniffer().sniff(sample)
            logging.info(f"Detected CSV delimiter: {dialect.delimiter}")
        
        # Get the latest download directory
        download_dir = get_latest_download_dir()
        if not download_dir:
            return []
            
        logging.info(f"Using download directory: {download_dir}")
        
        # Read CSV and get image paths
        image_paths = []
        with open(csv_path, 'r', newline='') as f:
            reader = csv.reader(f, dialect)
            for row in reader:
                if len(row) >= 2:
                    url, name = row[0].strip(), row[1].strip()
                    if url and name:
                        # Look for the image in the download directory
                        image_path = os.path.join(download_dir, f"{name}.png")
                        if os.path.exists(image_path):
                            image_paths.append(image_path)
                            logging.info(f"Found image: {image_path}")
                        else:
                            logging.error(f"Image not found: {image_path}")
        
        logging.info(f"Found {len(image_paths)} valid image paths")
        return image_paths
        
    except Exception as e:
        logging.error(f"Error processing CSV: {e}")
        return []

def get_latest_download_dir():
    """Get the most recent download directory."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    download_dir = os.path.join(base_dir, 'Download')
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
    logging.info(f"Found latest download directory: {latest_dir}")
    return latest_dir

def run_pdf_generation(image_paths):
    """Run the PDF generation script for each image."""
    try:
        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        pdf_script = os.path.join(script_dir, "wrapping_paper_pdf_generator.py")

        if not os.path.exists(pdf_script):
            logging.error(f"PDF generator script not found: {pdf_script}")
            return False

        # Create timestamped base output directory
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        base_output_dir = os.path.join(script_dir, "printpanels", "output", timestamp)
        os.makedirs(base_output_dir, exist_ok=True)
        logging.info(f"Created base output folder: {base_output_dir}")

        footer_path = os.path.join(script_dir, "Footer.pdf")

        def _invoke(extra_flags, subfolder):
            out_dir = os.path.join(base_output_dir, subfolder)
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
            logging.info(f"Launching generator for {label}: {' '.join(cmd)}")
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", cwd=out_dir)
            stdout, stderr = proc.communicate()
            if stdout:
                for line in stdout.splitlines():
                    logging.info(line)
            if stderr:
                for line in stderr.splitlines():
                    logging.error(line)
            if proc.returncode != 0:
                logging.error(f"Generator exited with {proc.returncode} for {label}")
                return False
            return True

        ok_wrap = _invoke([], "WrappingPaper")
        ok_tr = _invoke(["--tablerunner"], "Tablerunner")

        return ok_wrap and ok_tr
        
    except Exception as e:
        logging.error(f"Error running PDF generation: {e}")
        return False

def upload_to_s3(local_file, bucket_name, s3_key):
    """Upload a file to S3 and make it public."""
    try:
        print(f"Uploading {local_file} to S3 bucket {bucket_name}...")
        extra_args = {'ACL': 'public-read', 'ContentType': 'application/pdf'}
        s3.upload_file(local_file, bucket_name, s3_key, ExtraArgs=extra_args)
        location = s3.get_bucket_location(Bucket=bucket_name)['LocationConstraint']
        if location is None:
            location = 'us-east-1'
        url = f"https://{bucket_name}.s3-{location}.amazonaws.com/{s3_key}"
        print(f"Uploaded successfully to {url}")
        return url
    except FileNotFoundError:
        print(f"File {local_file} not found.")
        return None
    except NoCredentialsError:
        print("AWS credentials not available.")
        return None
    except Exception as e:
        print(f"Error during upload: {e}")
        return None

def process_and_upload_files(output_folder):
    """Process PDF files in the output folder and upload to S3."""
    uploaded_files = []
    for root, dirs, files in os.walk(output_folder):
        for file in files:
            if file.endswith(".pdf"):
                local_file_path = os.path.join(root, file)
                # ----------------------------------------------------------
                # Use AA id (if any) in the S3 key so filenames become
                # AA12345606.pdf etc.  When no AA id exists we keep the
                # legacy *pattern name* prefix.
                # ----------------------------------------------------------

                basename = os.path.splitext(file)[0]
                if len(basename) > 2 and basename[-2:].isdigit():
                    suffix = basename[-2:]
                    pattern_prefix = basename[:-2]
                else:
                    suffix = ''
                    pattern_prefix = basename

                aa_id = None
                # Only attempt a lookup when the prefix is NOT already an AA id
                if not (pattern_prefix.upper().startswith('AA') and pattern_prefix[2:].isdigit()):
                    aa_id = _get_aa_id_for_handle(pattern_prefix)

                if aa_id:
                    s3_filename = f"{aa_id}{suffix}.pdf" if suffix else f"{aa_id}.pdf"
                else:
                    s3_filename = file  # keep original name

                s3_key = f"PrintFiles/{s3_filename}"
                uploaded_url = upload_to_s3(local_file_path, BUCKET_NAME, s3_key)
                if uploaded_url:
                    uploaded_files.append({
                        "file": file,
                        "url": uploaded_url,
                        "type": "print_panel"
                    })
    return uploaded_files

def _get_aa_id_for_handle(handle: str) -> str | None:
    """Return the AA###### product id stored in the *custom.basesku* metafield
    for *handle* or *None* if not available / network error.
    """
    try:
        resp = requests.get(f"{SHOPIFY_API_BASE}/products.json?handle={handle}", timeout=15)
        resp.raise_for_status()
        products = resp.json().get('products', [])
        if not products:
            return None
        product_id = products[0]['id']
        resp = requests.get(f"{SHOPIFY_API_BASE}/products/{product_id}/metafields.json", timeout=15)
        resp.raise_for_status()
        for mf in resp.json().get('metafields', []):
            if mf.get('namespace') == 'custom' and mf.get('key') in ('basesku', 'base_sku'):
                val = mf.get('value', '').strip().upper()
                if val.startswith('AA') and val[2:].isdigit():
                    return val
        return None
    except Exception as _e:
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
    if run_pdf_generation(image_paths):
        logging.info("PDF generation completed successfully")
        sys.exit(0)
    else:
        logging.error("PDF generation failed")
        sys.exit(1)

if __name__ == "__main__":
    main()