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
    Example: "ProductName_tablerunner1.png" -> "ProductName"
    """
    # Remove all possible table runner suffixes and extension
    base_name = filename
    for tablerunner_suffix in ['_tablerunner1.png', '_tablerunner2.png', '_tablerunner3.png']:
        base_name = base_name.replace(tablerunner_suffix, '')
    return base_name

def generate_tablerunner_sku(base_sku, tablerunner_number):
    """
    Generate table runner SKU by appending table runner code to existing Shopify SKU.
    tablerunner1 = 61, tablerunner2 = 62, tablerunner3 = 63
    
    Args:
        base_sku: The existing Shopify SKU (e.g., "AA123456")
        tablerunner_number: table runner type (tablerunner1, tablerunner2, tablerunner3)
    """
    tablerunner_codes = {
        'tablerunner1': '61',
        'tablerunner2': '62', 
        'tablerunner3': '63'
    }
    
    return f"{base_sku}{tablerunner_codes[tablerunner_number]}"

def find_product_by_name(products_data, filename):
    """
    Find the product data that matches the table runner filename.
    
    Args:
        products_data: List of product dictionaries
        filename: Table runner filename (e.g., "ProductName_tablerunner1.png")
    
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

def upload_tablerunner_files_to_s3(output_folder, products_data, bucket_name='aspenarlo'):
    """
    Upload table runner files to S3 with proper SKU naming and folder structure.
    
    Args:
        output_folder: Path to the timestamped output folder containing table runner files
        products_data: List of product dictionaries with name and shopify SKU info
        bucket_name: S3 bucket name
    """
    try:
        s3_client = get_s3_client()
        uploaded_files = []
        
        logger.info(f"Scanning for table runner files in: {output_folder}")
        
        # Find all table runner files in the output folder
        tablerunner_files = []
        for root, dirs, files in os.walk(output_folder):
            for file in files:
                if file.endswith(('_tablerunner1.png', '_tablerunner2.png', '_tablerunner3.png')):
                    tablerunner_files.append(os.path.join(root, file))
        
        logger.info(f"Found {len(tablerunner_files)} table runner files to upload")
        
        if not products_data:
            logger.error("No product data provided for SKU lookup")
            return []
        
        for tablerunner_file_path in tablerunner_files:
            try:
                filename = os.path.basename(tablerunner_file_path)
                
                # Find the corresponding product data
                product_data = find_product_by_name(products_data, filename)
                if not product_data:
                    logger.error(f"No product data found for {filename}, skipping")
                    continue
                
                # Get the base SKU from Shopify product data
                base_sku = product_data.get('sku') or product_data.get('shopify_sku') or product_data.get('base_sku')
                if not base_sku:
                    logger.error(f"No SKU found in product data for {filename}, skipping")
                    continue
                
                # Determine table runner type
                if filename.endswith('_tablerunner1.png'):
                    tablerunner_type = 'tablerunner1'
                elif filename.endswith('_tablerunner2.png'):
                    tablerunner_type = 'tablerunner2'
                elif filename.endswith('_tablerunner3.png'):
                    tablerunner_type = 'tablerunner3'
                else:
                    logger.warning(f"Unknown table runner type for file: {filename}")
                    continue
                
                # Generate table runner SKU using the Shopify SKU
                tablerunner_sku = generate_tablerunner_sku(base_sku, tablerunner_type)
                
                # Create S3 key - put in tablerunners folder within aspenarlo bucket
                s3_key = f"tablerunners/{tablerunner_sku}.png"
                
                logger.info(f"Uploading {filename} as {s3_key} (base SKU: {base_sku})")
                
                # Upload to S3 with public-read ACL
                extra_args = {
                    'ACL': 'public-read',
                    'ContentType': 'image/png'
                }
                
                s3_client.upload_file(
                    tablerunner_file_path,
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
                        'sku': tablerunner_sku,
                        'base_sku': base_sku,
                        'product_name': product_data.get('name', ''),
                        'tablerunner_type': tablerunner_type,
                        's3_key': s3_key,
                        'public_url': public_url,
                        'local_path': tablerunner_file_path
                    })
                    
                    logger.info(f"Successfully uploaded: {public_url}")
                    
                except Exception as verify_error:
                    logger.error(f"Upload verification failed for {s3_key}: {verify_error}")
                
            except Exception as file_error:
                logger.error(f"Error uploading {tablerunner_file_path}: {file_error}")
                continue
        
        logger.info(f"Successfully uploaded {len(uploaded_files)} table runner files to S3")
        
        # Print summary
        print("\n=== TABLE RUNNER UPLOAD SUMMARY ===")
        for upload in uploaded_files:
            print(f"Product: {upload['product_name']}")
            print(f"  Base SKU: {upload['base_sku']}")
            print(f"  Table Runner SKU: {upload['sku']}")
            print(f"  Type: {upload['tablerunner_type']}")
            print(f"  URL: {upload['public_url']}")
            print()
        
        return uploaded_files
        
    except Exception as e:
        logger.error(f"Error in table runner S3 upload: {e}")
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
        # Upload table runner files (you'd need to pass products_data in real usage)
        uploaded_files = upload_tablerunner_files_to_s3(output_folder, [])
        
        if uploaded_files:
            print(f"\n✅ Successfully uploaded {len(uploaded_files)} table runner files!")
            print("TABLERUNNER_UPLOAD_COMPLETE")
        else:
            print("❌ No table runner files were uploaded")
    else:
        print("❌ Could not find output folder")
