from azure.identity import ClientSecretCredential 
from azure.core.exceptions import HttpResponseError
import pandas as pd
import requests
import os
import dotenv
import asyncio
import aiohttp
dotenv.load_dotenv()


tenant_id = os.getenv("TENANTID")
client_id = os.getenv("CLIENTID")
client_secret = os.getenv("CLIENTSECRET")
purview_endpoint = os.getenv("PURVIEWENDPOINT")
purview_scan_endpoint = os.getenv("PURVIEWSCANENDPOINT")
purview_account_name = os.getenv("PURVIEWACCOUNTNAME")
token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/token"
resource = "https://purview.azure.net"

def get_credentials():
    credentials = ClientSecretCredential(client_id=client_id, client_secret=client_secret, tenant_id=tenant_id)
    return credentials

def get_access_token(tenant_id, client_id, client_secret):
    print("Authenticating with Azure AD to get access token...")
    credential = ClientSecretCredential(
        tenant_id=tenant_id, 
        client_id=client_id, 
        client_secret=client_secret
    )
    token = credential.get_token("https://purview.azure.net/.default")
    print("Access token acquired.")
    return token.token

async def add_classification_to_entity_async(session, endpoint, guid, classifications, access_token):
    """Add classifications to entity asynchronously"""
    url = f"{endpoint}/datamap/api/atlas/v2/entity/guid/{guid}/classifications?api-version=2023-09-01"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    print(f"\nSending classifications to entity GUID: {guid}")
    print(f"Payload: {classifications}")
    
    try:
        async with session.post(url, headers=headers, json=classifications) as response:
            if response.status == 204:
                print(f"SUCCESS: Classifications added to {guid}")
            else:
                text = await response.text()
                print(f"FAILED: Could not add classifications to {guid}. Status code: {response.status}")
                print(f"Response: {text}")
    except Exception as e:
        print(f"ERROR adding classifications to {guid}: {e}")

def add_classification_to_entity(endpoint, guid, classifications, access_token):
    """Synchronous wrapper for backwards compatibility"""
    url = f"{endpoint}/datamap/api/atlas/v2/entity/guid/{guid}/classifications?api-version=2023-09-01"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    print(f"\nSending classifications to entity GUID: {guid}")
    print(f"Payload: {classifications}")
    response = requests.post(url, headers=headers, json=classifications)
    if response.status_code == 204:
        print(f"SUCCESS: Classifications added to {guid}")
    else:
        print(f"FAILED: Could not add classifications to {guid}. Status code: {response.status_code}")
        print(f"Response: {response.text}")

async def process_classifications_async(guid_list, classification_type_names, access_token, endpoint):
    """Process classifications for multiple GUIDs in parallel"""
    # Create SSL context that doesn't verify certificates (for self-signed certs)
    import ssl
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Process each GUID in parallel
        # All classifications for the same GUID are added in a single API call
        tasks = []
        for guid in guid_list:
            classifications = [{"typeName": type_name} for type_name in classification_type_names]
            task = add_classification_to_entity_async(session, endpoint, guid, classifications, access_token)
            tasks.append(task)
        
        await asyncio.gather(*tasks)

def main(guid_list, classification_type_names, parallel=True):
    print("Starting classification addition process...")
    access_token = get_access_token(tenant_id, client_id, client_secret)
    
    if parallel and len(guid_list) > 1:
        print(f"Using parallel processing for {len(guid_list)} assets...")
        asyncio.run(process_classifications_async(guid_list, classification_type_names, access_token, purview_endpoint))
    else:
        # Sequential processing for single items or when parallel is disabled
        for guid in guid_list:
            classifications = [{"typeName": type_name} for type_name in classification_type_names]
            add_classification_to_entity(purview_endpoint, guid, classifications, access_token)
    
    print("\nClassification addition process completed.")

if __name__ == "__main__":
    # Example usage:
    # main(["your-entity-guid"], ["MICROSOFT.FINANCIAL.US.ABA_ROUTING_NUMBER", "MICROSOFT.FINANCIAL.CREDIT_CARD_NUMBER"])
    main([], [])