import requests
import json
import os

# Load Shopify credentials from environment variables
SHOPIFY_API_KEY = os.getenv('SHOPIFY_API_KEY')
SHOPIFY_PASSWORD = os.getenv('SHOPIFY_PASSWORD')
SHOPIFY_STORE_NAME = os.getenv('SHOPIFY_STORE')

# Validate env vars
if not all([SHOPIFY_API_KEY, SHOPIFY_PASSWORD, SHOPIFY_STORE_NAME]):
    raise RuntimeError("Missing one or more required Shopify environment variables: SHOPIFY_API_KEY, SHOPIFY_PASSWORD, SHOPIFY_STORE")

SHOPIFY_API_BASE = f"https://{SHOPIFY_API_KEY}:{SHOPIFY_PASSWORD}@{SHOPIFY_STORE_NAME}.myshopify.com/admin/api/2023-04"

def check_product_metafields(handle):
    """Check all metafields for a product by handle"""
    
    # First get the product
    url = f'{SHOPIFY_API_BASE}/products.json?handle={handle}'
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        products = response.json().get('products', [])
        
        if not products:
            print(f"❌ No product found with handle: {handle}")
            return
            
        product = products[0]
        product_id = product['id']
        print(f"✅ Found product: {product['title']} (ID: {product_id})")
        
        # Get all metafields for this product
        metafields_url = f'{SHOPIFY_API_BASE}/products/{product_id}/metafields.json'
        meta_response = requests.get(metafields_url, timeout=30)
        meta_response.raise_for_status()
        metafields = meta_response.json().get('metafields', [])
        
        print(f"\n📋 METAFIELDS COUNT: {len(metafields)}")
        print("=" * 60)
        
        if not metafields:
            print("❌ No metafields found on this product")
            return
            
        for i, mf in enumerate(metafields, 1):
            print(f"\n🏷️  METAFIELD #{i}:")
            print(f"   Namespace: {mf.get('namespace')}")
            print(f"   Key: {mf.get('key')}")
            print(f"   Value: {mf.get('value')}")
            print(f"   Type: {mf.get('type')}")
            print(f"   ID: {mf.get('id')}")
            
            # Highlight the base_sku fields
            namespace = mf.get('namespace')
            key = mf.get('key')
            if namespace == 'custom' and key in ['base_sku', 'basesku']:
                print(f"   ⭐ THIS IS THE BASE SKU METAFIELD! ⭐")
        
        # Also check for specific variants and their SKUs
        print(f"\n🎯 PRODUCT VARIANTS:")
        print("=" * 60)
        for i, variant in enumerate(product.get('variants', []), 1):
            print(f"Variant #{i}: SKU = {variant.get('sku', 'No SKU')}")
        
    except requests.RequestException as e:
        print(f"❌ API Error: {e}")

if __name__ == "__main__":
    print("🔍 SHOPIFY METAFIELD CHECKER")
    print("=" * 60)
    
    # Check the Panda Test product
    check_product_metafields("panda-test")
    
    print("\n" + "=" * 60)
    print("✅ Check complete!")