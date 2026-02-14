from azure.identity import ClientSecretCredential 
from azure.core.exceptions import HttpResponseError
import pandas as pd
import requests
import os
import dotenv
import asyncio
import aiohttp
from urllib.parse import quote
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

async def remove_classification_from_entity_async(session, endpoint, guid, classification_name, access_token):
    """Remove a specific classification from an entity asynchronously"""
    # URL encode the classification name to handle special characters like dots
    encoded_classification = quote(classification_name, safe='')
    url = f"{endpoint}/datamap/api/atlas/v2/entity/guid/{guid}/classification/{encoded_classification}?api-version=2023-09-01"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    print(f"\nRemoving classification '{classification_name}' from entity GUID: {guid}", flush=True)
    
    try:
        async with session.delete(url, headers=headers) as response:
            if response.status == 204:
                print(f"SUCCESS: Classification '{classification_name}' removed from {guid}", flush=True)
            else:
                text = await response.text()
                print(f"FAILED: Could not remove classification from {guid}. Status code: {response.status}", flush=True)
                print(f"Response: {text}", flush=True)
    except Exception as e:
        print(f"ERROR removing classification from {guid}: {e}", flush=True)

def remove_classification_from_entity(endpoint, guid, classification_name, access_token):
    """Remove a specific classification from an entity - synchronous version"""
    # URL encode the classification name to handle special characters like dots
    encoded_classification = quote(classification_name, safe='')
    url = f"{endpoint}/datamap/api/atlas/v2/entity/guid/{guid}/classification/{encoded_classification}?api-version=2023-09-01"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    print(f"\nRemoving classification '{classification_name}' from entity GUID: {guid}", flush=True)
    response = requests.delete(url, headers=headers)
    if response.status_code == 204:
        print(f"SUCCESS: Classification '{classification_name}' removed from {guid}", flush=True)
    else:
        print(f"FAILED: Could not remove classification from {guid}. Status code: {response.status_code}", flush=True)
        print(f"Response: {response.text}", flush=True)

async def process_classification_removal_async(guid_list, classification_type_names, access_token, endpoint):
    """Process classification removal for multiple GUIDs and classifications in parallel"""
    # Create SSL context that doesn't verify certificates (for self-signed certs)
    import ssl
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Process each GUID in parallel, but classifications for the same GUID sequentially
        # to avoid Purview API 412 PreConditionCheckFailed errors
        tasks = []
        for guid in guid_list:
            async def process_guid(g):
                for type_name in classification_type_names:
                    await remove_classification_from_entity_async(session, endpoint, g, type_name, access_token)
            tasks.append(process_guid(guid))
        
        await asyncio.gather(*tasks)

def main(guid_list, classification_type_names, parallel=True):
    print("Starting classification removal process...", flush=True)
    access_token = get_access_token(tenant_id, client_id, client_secret)
    
    # For each asset, remove from asset AND all its columns
    for guid in guid_list:
        # First, try to remove from the asset itself
        for classification_name in classification_type_names:
            remove_classification_from_entity(purview_endpoint, guid, classification_name, access_token)
        
        # Then, get the schema and remove from all columns
        try:
            import auto_classify
            entity_info = auto_classify.get_entity_schema_with_sdk(guid)
            
            if entity_info and entity_info.get('entity'):
                entity = entity_info['entity']
                
                # Check if entity has schema/columns
                if entity_info.get('columns'):
                    columns = entity_info['columns']
                    print(f"\nChecking {len(columns)} columns for classifications to remove...", flush=True)
                    
                    headers = {
                        'Authorization': f'Bearer {access_token}',
                        'Content-Type': 'application/json'
                    }
                    
                    for col_ref in columns:
                        if isinstance(col_ref, dict):
                            column_guid = col_ref.get('guid')
                            column_name = col_ref.get('displayName', 'unknown')
                            
                            if column_guid:
                                # Get column details to see if it has the classification
                                try:
                                    col_url = f"{purview_endpoint}/datamap/api/atlas/v2/entity/guid/{column_guid}?api-version=2023-09-01"
                                    col_response = requests.get(col_url, headers=headers, timeout=5)
                                    
                                    if col_response.status_code == 200:
                                        col_entity_data = col_response.json()
                                        col_entity = col_entity_data.get('entity', {})
                                        col_classifications = col_entity.get('classifications', [])
                                        
                                        # Check if column has any of the target classifications
                                        for col_class in col_classifications:
                                            class_name = col_class.get('typeName')
                                            if class_name in classification_type_names:
                                                print(f"  Found '{class_name}' on column '{column_name}' - removing...", flush=True)
                                                remove_classification_from_entity(purview_endpoint, column_guid, class_name, access_token)
                                except Exception as col_error:
                                    print(f"  Warning: Could not process column {column_name}: {col_error}", flush=True)
        except Exception as e:
            print(f"Error processing asset {guid} schema: {e}", flush=True)
    
    print("\nClassification removal process completed.", flush=True)

if __name__ == "__main__":
    # Example usage:
    # main(["your-entity-guid"], ["MICROSOFT.FINANCIAL.US.ABA_ROUTING_NUMBER"])
    main([], [])
