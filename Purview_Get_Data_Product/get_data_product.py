import os
import requests
from dotenv import load_dotenv
from azure.identity import ClientSecretCredential
import json

# Load environment variables from .env file
load_dotenv()

# Get configuration from environment variables
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENTID")
CLIENT_SECRET = os.getenv("CLIENTSECRET")

PURVIEW_ENDPOINT = os.getenv("PURVIEW_ENDPOINT", "https://api.purview-service.microsoft.com")

# Validate required environment variables
required_vars = {
    "TENANT_ID": TENANT_ID,
    "CLIENT_ID": CLIENT_ID,
    "CLIENT_SECRET": CLIENT_SECRET
}

missing_vars = [var for var, value in required_vars.items() if not value]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")


def get_access_token():
    """
    Get an access token using Azure AD authentication with client credentials.
    """
    try:
        credential = ClientSecretCredential(
            tenant_id=TENANT_ID,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET
        )
        
        # Get token for Purview scope
        token = credential.get_token("https://purview.azure.net/.default")
        return token.token
    except Exception as e:
        print(f"Error obtaining access token: {e}")
        raise


def list_data_products(skip=0, top=100, domain_id=None, order_by=None):
    """
    List data products from Microsoft Purview Unified Catalog.
    
    Args:
        skip (int): Number of results to skip (for pagination)
        top (int): Maximum number of results to return
        domain_id (str): Optional UUID to filter by domain
        order_by (str): Optional sort expression
        
    Returns:
        dict: Response containing data products
    """
    try:
        # Get access token
        access_token = get_access_token()
        
        # Construct the URL
        api_version = "2025-09-15-preview"
        url = f"{PURVIEW_ENDPOINT}/datagovernance/catalog/dataProducts"
        
        # Set up query parameters
        params = {
            "api-version": api_version
        }
        
        if skip > 0:
            params["skip"] = skip
        if top:
            params["top"] = top
        if domain_id:
            params["domainId"] = domain_id
        if order_by:
            params["orderBy"] = order_by
        
        # Set up headers
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Make the API request
        print(f"Requesting data products from: {url}")
        response = requests.get(url, headers=headers, params=params)
        
        # Check response status
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            print(f"Response: {response.text}")
            response.raise_for_status()
            
    except Exception as e:
        print(f"Error listing data products: {e}")
        raise


def list_all_data_products(domain_id=None, order_by=None):
    """
    List all data products, handling pagination automatically.
    
    Args:
        domain_id (str): Optional UUID to filter by domain
        order_by (str): Optional sort expression
        
    Returns:
        list: All data products
    """
    all_products = []
    skip = 0
    top = 100
    
    while True:
        result = list_data_products(skip=skip, top=top, domain_id=domain_id, order_by=order_by)
        
        if "value" in result:
            products = result["value"]
            all_products.extend(products)
            print(f"Retrieved {len(products)} data products (total: {len(all_products)})")
            
            # Check if there's a next page
            if "nextLink" in result and result["nextLink"]:
                skip += top
            else:
                break
        else:
            break
    
    return all_products


def display_data_products(products):
    """
    Display data products in a readable format.
    
    Args:
        products (list): List of data products
    """
    if not products:
        print("\nNo data products found.")
        return
    
    print(f"\n{'='*80}")
    print(f"Total Data Products Found: {len(products)}")
    print(f"{'='*80}\n")
    
    for idx, product in enumerate(products, 1):
        print(f"{idx}. {product.get('name', 'N/A')}")
        print(f"   ID: {product.get('id', 'N/A')}")
        print(f"   Type: {product.get('type', 'N/A')}")
        print(f"   Status: {product.get('status', 'N/A')}")
        print(f"   Domain: {product.get('domain', 'N/A')}")
        print(f"   Description: {product.get('description', 'N/A')[:100]}...")
        print(f"   Endorsed: {product.get('endorsed', False)}")
        
        if 'businessUse' in product:
            print(f"   Business Use: {product.get('businessUse', 'N/A')[:100]}...")
        
        if 'updateFrequency' in product:
            print(f"   Update Frequency: {product.get('updateFrequency', 'N/A')}")
        
        if 'additionalProperties' in product and 'assetCount' in product['additionalProperties']:
            print(f"   Asset Count: {product['additionalProperties']['assetCount']}")
        
        print()


if __name__ == "__main__":
    try:
        print("Fetching data products from Microsoft Purview Unified Catalog...")
        print("-" * 80)
        
        # List all data products
        products = list_all_data_products()
        
        # Display the results
        display_data_products(products)
        
      
        
        # Pretty print each product separately
        for idx, product in enumerate(products, 1):
            product_name = product.get('name', f'Data Product #{idx}')
            print(f"┌─ {product_name} " + "─"*(77 - len(product_name)))
            json_str = json.dumps(product, indent=2, ensure_ascii=False)
            for line in json_str.split('\n'):
                print(f"│ {line}")
            print("└" + "─"*78 + "\n")
        
    except Exception as e:
        print(f"\nFailed to retrieve data products: {e}")
        exit(1)
