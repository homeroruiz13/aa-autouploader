import sys
import json
import requests
import logging
import re
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load Shopify credentials from environment variables
SHOPIFY_API_KEY = os.getenv('SHOPIFY_API_KEY')
SHOPIFY_PASSWORD = os.getenv('SHOPIFY_PASSWORD')
SHOPIFY_STORE_NAME = os.getenv('SHOPIFY_STORE')
SHOPIFY_API_VERSION = os.getenv('SHOPIFY_API_VERSION', '2025-01')  # Default to 2025-01

# Validate env vars
if not all([SHOPIFY_API_KEY, SHOPIFY_PASSWORD, SHOPIFY_STORE_NAME]):
    raise RuntimeError("Missing one or more required Shopify environment variables: SHOPIFY_API_KEY, SHOPIFY_PASSWORD, SHOPIFY_STORE")

SHOPIFY_API_BASE = f"https://{SHOPIFY_STORE_NAME}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}"
SHOPIFY_HEADERS = {
    'X-Shopify-Access-Token': SHOPIFY_PASSWORD,
    'Content-Type': 'application/json'
}

def print_json(data):
    """Print JSON data for the Node.js server to parse"""
    print(json.dumps(data, separators=(',', ':')))
    sys.stdout.flush()

def get_or_create_metafield(product_id, base_sku_value):
    """Get existing metafield or create new one with basesku key (no underscore!)"""
    
    # Get all metafields for the product
    metafields_url = f'{SHOPIFY_API_BASE}/products/{product_id}/metafields.json'
    response = requests.get(metafields_url, headers=SHOPIFY_HEADERS, timeout=30)
    response.raise_for_status()
    metafields = response.json().get('metafields', [])
    
    print_json({"debug": f"ALL_METAFIELDS", "product_id": product_id, "count": len(metafields)})
    
    # Print all metafields for debugging
    for mf in metafields:
        print_json({
            "debug": "METAFIELD_DETAIL",
            "namespace": mf.get('namespace'),
            "key": mf.get('key'),
            "value": mf.get('value'),
            "type": mf.get('type')
        })
    
    # Look for existing basesku metafield (without underscore!)
    existing_metafield = None
    for mf in metafields:
        if mf.get('namespace') == 'custom' and mf.get('key') == 'basesku':  # Changed from base_sku to basesku
            existing_metafield = mf
            break
    
    if existing_metafield:
        existing_value = existing_metafield['value'].strip()
        print_json({"debug": f"Found existing basesku metafield: {existing_value}"})
        
        # If the existing value is an AA product ID (starts with AA and has 6+ chars), keep it
        # If the new value is just a product name, don't overwrite the AA product ID
        if existing_value.startswith('AA') and len(existing_value) >= 8:
            if base_sku_value == existing_value:
                print_json({"debug": "Values match, no update needed"})
                return existing_metafield
            elif not base_sku_value.startswith('AA'):
                print_json({"debug": f"Keeping existing AA product ID '{existing_value}' instead of overwriting with '{base_sku_value}'"})
                return existing_metafield
        
        # Update the existing metafield
        metafield_id = existing_metafield['id']
        update_url = f'{SHOPIFY_API_BASE}/metafields/{metafield_id}.json'
        
        # Ensure value is exactly 8 characters but preserve meaningful content
        if len(base_sku_value) > 8:
            adjusted_value = base_sku_value[:8]  # Truncate if too long
        elif len(base_sku_value) < 8:
            # Pad with spaces instead of zeros to preserve readability
            adjusted_value = base_sku_value.ljust(8, ' ')
        else:
            adjusted_value = base_sku_value  # Perfect length
        
        update_data = {
            'metafield': {
                'id': metafield_id,
                'value': adjusted_value,
                'type': 'single_line_text_field'
            }
        }
        
        print_json({"debug": f"Updating metafield {metafield_id} with data: {update_data}"})
        
        response = requests.put(update_url, json=update_data, headers=SHOPIFY_HEADERS, timeout=30)
        print_json({"debug": f"PUT response status: {response.status_code}"})
        print_json({"debug": f"PUT response body: {response.text}"})
        
        if response.status_code == 200:
            return response.json()['metafield']
        else:
            print_json({"error": f"Failed to update metafield: {response.status_code} - {response.text}"})
            return None
    else:
        print_json({"debug": "No existing basesku metafield found, creating new one"})
        
        # Create new metafield with basesku key (no underscore!)
        create_url = f'{SHOPIFY_API_BASE}/products/{product_id}/metafields.json'
        
        # Ensure value is exactly 8 characters but preserve meaningful content
        if len(base_sku_value) > 8:
            adjusted_value = base_sku_value[:8]  # Truncate if too long
        elif len(base_sku_value) < 8:
            # Pad with spaces instead of zeros to preserve readability
            adjusted_value = base_sku_value.ljust(8, ' ')
        else:
            adjusted_value = base_sku_value  # Perfect length
        
        create_data = {
            'metafield': {
                'namespace': 'custom',
                'key': 'basesku',  # Changed from base_sku to basesku
                'value': adjusted_value,
                'type': 'single_line_text_field'
            }
        }
        
        print_json({"debug": f"Creating metafield with data: {create_data}"})
        
        response = requests.post(create_url, json=create_data, headers=SHOPIFY_HEADERS, timeout=30)
        print_json({"debug": f"POST response status: {response.status_code}"})
        print_json({"debug": f"POST response body: {response.text}"})
        
        if response.status_code == 201:
            return response.json()['metafield']
        else:
            print_json({"error": f"Failed to create metafield: {response.status_code} - {response.text}"})
            return None

def process_product(product_data):
    """Process a single product and update its metafields and images"""
    
    product_name = product_data.get('name')
    product_handle = product_data.get('handle')
    base_sku = product_data.get('base_sku')
    
    # Skip metafield update if base_sku is just the product name
    # We only want to update if we have an actual AA product ID
    if base_sku == product_name:
        print_json({"debug": f"Skipping metafield update - base_sku '{base_sku}' matches product name"})
        skip_metafield_update = True
    else:
        skip_metafield_update = False
    
    print_json({"status": "processing", "product": product_name})
    print_json({"debug": f"Searching for product with handle: {product_handle}"})
    
    # Find the product by handle
    url = f'{SHOPIFY_API_BASE}/products.json?handle={product_handle}'
    try:
        response = requests.get(url, headers=SHOPIFY_HEADERS, timeout=30)
        response.raise_for_status()
        products = response.json().get('products', [])
        
        if not products:
            print_json({"debug": f"No product found with handle: {product_handle}"})
            print_json({"status": "not_found", "product": product_name})
            return
            
        product = products[0]
        product_id = product['id']
        print_json({"debug": f"Found product: {product['title']} (ID: {product_id})"})
        
        # Only update the metafield if we have a proper AA product ID, not just the product name
        if not skip_metafield_update:
            # Update the metafield
            metafield_result = get_or_create_metafield(product_id, base_sku)
        else:
            print_json({"debug": "Skipping metafield update - keeping existing AA product ID"})
            metafield_result = True  # Simulate success
        
        # Process mockup images if they exist
        process_product_images(product_data, product_id)
        
        if metafield_result:
            print_json({"debug": "Metafields after update:"})
            
            # Verify the update by fetching metafields again
            metafields_url = f'{SHOPIFY_API_BASE}/products/{product_id}/metafields.json'
            response = requests.get(metafields_url, headers=SHOPIFY_HEADERS, timeout=30)
            response.raise_for_status()
            metafields = response.json().get('metafields', [])
            
            print_json({"debug": f"ALL_METAFIELDS", "product_id": product_id, "count": len(metafields)})
            
            for mf in metafields:
                print_json({
                    "debug": "METAFIELD_DETAIL",
                    "namespace": mf.get('namespace'),
                    "key": mf.get('key'),
                    "value": mf.get('value'),
                    "type": mf.get('type')
                })
            
            print_json({"status": "updated", "product": product_name})
        else:
            print_json({"status": "failed", "product": product_name})
            
    except requests.RequestException as e:
        print_json({"error": f"Request failed for {product_name}: {str(e)}"})
        print_json({"status": "error", "product": product_name})

def process_product_images(product_data, product_id):
    """Attach Photoshop mock-ups (hero, 011, etc.) to the Shopify product.

    *Only* the mock-ups should be uploaded – the huge 20-megapixel tile (``s3_url``)
    exceeds Shopify's limit and therefore produces a *422* error.  We therefore
    skip that URL and anything else that obviously contains the original 6-tile
    image.
    """

    # Collect every "*_url" field *except* the main ``s3_url`` (20-MP tile)
    image_urls = [
        value for key, value in product_data.items()
        if key.endswith("_url") and key != "s3_url" and value
    ]

    if not image_urls:
        print_json({"debug": "No mock-up image URLs found – nothing to upload"})
        return

    # Fetch existing images once so we can avoid duplicates
    try:
        images_endpoint = f"{SHOPIFY_API_BASE}/products/{product_id}/images.json"
        resp = requests.get(images_endpoint, headers=SHOPIFY_HEADERS, timeout=30)
        resp.raise_for_status()
        existing_sources = {img.get("src") for img in resp.json().get("images", [])}
    except requests.RequestException as e:
        print_json({"error": f"Could not query existing images for {product_id}: {str(e)}"})
        existing_sources = set()

    for url in image_urls:
        if url in existing_sources:
            print_json({"debug": f"Image already attached – skipping {url}"})
            continue

        try:
            resp = requests.post(images_endpoint, json={"image": {"src": url}}, headers=SHOPIFY_HEADERS, timeout=30)
            if resp.status_code in (200, 201, 202):
                print_json({"debug": f"Attached mock-up: {url}"})
            else:
                print_json({"error": f"Failed to attach {url}: {resp.status_code} – {resp.text[:300]}"})
        except requests.RequestException as e:
            print_json({"error": f"Network error while attaching {url}: {str(e)}"})

def main():
    if len(sys.argv) != 2:
        print_json({"error": "Usage: python process_products.py <processed_products.json>"})
        sys.exit(1)
    
    json_file_path = sys.argv[1]
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            products_data = json.load(f)
        
        print_json({"status": "start", "product_count": len(products_data)})
        
        # 1) Identify the *main* product record
        main_product = None
        for item in products_data:
            if (
                isinstance(item, dict)
                and item.get('name')
                and item.get('handle')
                and item.get('base_sku') is not None
            ):
                main_product = item
                break

        # 2) Merge any Photoshop output URLs into the main product so
        #    ``process_product_images`` can pick them up.
        if main_product:
            for item in products_data:
                if item is main_product:
                    continue
                if isinstance(item, dict) and item.get('type') == 'photoshop_output' and item.get('url'):
                    image_type = item.get('image_type', '').lower() or 'extra'
                    safe_key = re.sub(r'[^a-z0-9]+', '_', image_type) + '_url'
                    # Do not overwrite if the key already exists (idempotent)
                    if safe_key not in main_product:
                        main_product[safe_key] = item['url']

        if main_product:
            print_json({"debug": f"Found main product: {main_product.get('name')}"})
            process_product(main_product)
        else:
            print_json({"error": "No main product data found in the JSON file"})
            print_json({"debug": f"JSON structure: {json.dumps(products_data, indent=2)}"})
        
        print_json({"status": "complete", "message": "All products processed"})
        
    except FileNotFoundError:
        print_json({"error": f"File not found: {json_file_path}"})
        sys.exit(1)
    except json.JSONDecodeError as e:
        print_json({"error": f"Invalid JSON in file: {str(e)}"})
        sys.exit(1)
    except Exception as e:
        print_json({"error": f"Unexpected error: {str(e)}"})
        sys.exit(1)

if __name__ == "__main__":
    main()