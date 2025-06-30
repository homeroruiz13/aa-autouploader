import os
import boto3
import logging
from pathlib import Path
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_s3_client():
    """Get S3 client using your existing credentials"""
    return boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name='us-east-2'  # Your existing region
    )

def extract_product_id_from_filename(filename):
    """
    Extract the base product ID from filename.
    Example: "ProductName_tissue1.png" -> "ProductName"
    """
    # Remove all possible tissue suffixes and extension
    base_name = filename
    for tissue_suffix in ['_tissue1.png', '_tissue2.png', '_tissue3.png']:
        base_name = base_name.replace(tissue_suffix, '')
    return base_name

def generate_tissue_sku(base_sku, tissue_number):
    """
    Generate tissue SKU by appending tissue code to existing Shopify SKU.
    tissue1 = 51, tissue2 = 52, tissue3 = 53
    
    Args:
        base_sku: The existing Shopify SKU (e.g., "AA123456")
        tissue_number: tissue type (tissue1, tissue2, tissue3)
    """
    tissue_codes = {
        'tissue1': '51',
        'tissue2': '52', 
        'tissue3': '53'
    }
    
    return f"{base_sku}{tissue_codes[tissue_number]}"

def find_product_by_name(products_data, filename):
    """
    Find the product data that matches the tissue filename.
    
    Args:
        products_data: List of product dictionaries
        filename: Tissue filename (e.g., "ProductName_tissue1.png")
    
    Returns:
        Product dictionary or None
    """
    # Extract product name from filename
    product_name = extract_product_id_from_filename(filename)
    
    # Find matching product in the data
    for product in products_data:
        # Try exact match first
        if product.get('name', '') == product_name:
            return product
        
        # Try handle match (in case name was processed)
        if product.get('handle', '') == product_name.lower().replace(' ', '-'):
            return product
    
    logger.warning(f"No product data found for filename: {filename}")
    return None

def upload_tissue_files_to_s3(output_folder, products_data, bucket_name='aspenarlo'):
    """
    Upload tissue files to S3 with proper SKU naming and folder structure.
    
    Args:
        output_folder: Path to the timestamped output folder containing tissue files
        products_data: List of product dictionaries with name and shopify SKU info
        bucket_name: S3 bucket name
    """
    try:
        s3_client = get_s3_client()
        uploaded_files = []
        
        logger.info(f"Scanning for tissue files in: {output_folder}")
        
        # Find all tissue files in the output folder
        tissue_files = []
        for root, dirs, files in os.walk(output_folder):
            for file in files:
                if file.endswith(('_tissue1.png', '_tissue2.png', '_tissue3.png')):
                    tissue_files.append(os.path.join(root, file))
        
        logger.info(f"Found {len(tissue_files)} tissue files to upload")
        
        if not products_data:
            logger.error("No product data provided for SKU lookup")
            return []
        
        for tissue_file_path in tissue_files:
            try:
                filename = os.path.basename(tissue_file_path)
                
                # Find the corresponding product data
                product_data = find_product_by_name(products_data, filename)
                if not product_data:
                    logger.error(f"No product data found for {filename}, skipping")
                    continue
                
                # Get the base SKU from Shopify product data
                base_sku = product_data.get('sku') or product_data.get('shopify_sku')
                if not base_sku:
                    logger.error(f"No SKU found in product data for {filename}, skipping")
                    continue
                
                # Determine tissue type
                if filename.endswith('_tissue1.png'):
                    tissue_type = 'tissue1'
                elif filename.endswith('_tissue2.png'):
                    tissue_type = 'tissue2'
                elif filename.endswith('_tissue3.png'):
                    tissue_type = 'tissue3'
                else:
                    logger.warning(f"Unknown tissue type for file: {filename}")
                    continue
                
                # Generate tissue SKU using the Shopify SKU
                tissue_sku = generate_tissue_sku(base_sku, tissue_type)
                
                # Create S3 key - put in tissues folder within aspenarlo bucket
                s3_key = f"tissues/{tissue_sku}.png"
                
                logger.info(f"Uploading {filename} as {s3_key} (base SKU: {base_sku})")
                
                # Upload to S3 with public-read ACL
                extra_args = {
                    'ACL': 'public-read',
                    'ContentType': 'image/png'
                }
                
                s3_client.upload_file(
                    tissue_file_path,
                    bucket_name,
                    s3_key,
                    ExtraArgs=extra_args
                )
                
                # Verify upload and get URL
                try:
                    s3_client.head_object(Bucket=bucket_name, Key=s3_key)
                    
                    # Generate the public URL
                    location = s3_client.get_bucket_location(Bucket=bucket_name)['LocationConstraint']
                    if location is None:
                        location = 'us-east-1'
                    
                    public_url = f"https://{bucket_name}.s3-{location}.amazonaws.com/{s3_key}"
                    
                    uploaded_files.append({
                        'original_file': filename,
                        'sku': tissue_sku,
                        'base_sku': base_sku,
                        'product_name': product_data.get('name', ''),
                        'tissue_type': tissue_type,
                        's3_key': s3_key,
                        'public_url': public_url,
                        'local_path': tissue_file_path
                    })
                    
                    logger.info(f"Successfully uploaded: {public_url}")
                    
                except Exception as verify_error:
                    logger.error(f"Upload verification failed for {s3_key}: {verify_error}")
                
            except Exception as file_error:
                logger.error(f"Error uploading {tissue_file_path}: {file_error}")
                continue
        
        logger.info(f"Successfully uploaded {len(uploaded_files)} tissue files to S3")
        
        # Print summary
        print("\n=== TISSUE UPLOAD SUMMARY ===")
        for upload in uploaded_files:
            print(f"Product: {upload['product_name']}")
            print(f"  Base SKU: {upload['base_sku']}")
            print(f"  Tissue SKU: {upload['sku']}")
            print(f"  Type: {upload['tissue_type']}")
            print(f"  URL: {upload['public_url']}")
            print()
        
        return uploaded_files
        
    except Exception as e:
        logger.error(f"Error in tissue S3 upload: {e}")
        return []

def get_most_recent_output_folder():
    """
    Find the most recent timestamped output folder.
    """
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_base = os.path.join(script_dir, "..", "Output")  # Go up one level to Output
        
        if not os.path.exists(output_base):
            logger.error(f"Output base folder not found: {output_base}")
            return None
        
        # Get timestamped folders
        timestamped_folders = [
            f for f in os.listdir(output_base) 
            if os.path.isdir(os.path.join(output_base, f)) 
            and re.match(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}-[0-9]{2}-[0-9]{2}$', f)
        ]
        
        if not timestamped_folders:
            logger.error("No timestamped folders found in Output directory")
            return None
        
        # Sort and get the most recent
        timestamped_folders.sort(reverse=True)
        most_recent_folder = os.path.join(output_base, timestamped_folders[0])
        
        logger.info(f"Using output folder: {most_recent_folder}")
        return most_recent_folder
        
    except Exception as e:
        logger.error(f"Error finding output folder: {e}")
        return None

if __name__ == "__main__":
    # Find the most recent output folder
    output_folder = get_most_recent_output_folder()
    
    if output_folder:
        # Upload tissue files (you'd need to pass products_data in real usage)
        uploaded_files = upload_tissue_files_to_s3(output_folder, [])
        
        if uploaded_files:
            print(f"\n✅ Successfully uploaded {len(uploaded_files)} tissue files!")
            print("TISSUE_UPLOAD_COMPLETE")
        else:
            print("❌ No tissue files were uploaded")
    else:
        print("❌ Could not find output folder")
