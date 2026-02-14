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
    credential = ClientSecretCredential(
        tenant_id=tenant_id, 
        client_id=client_id, 
        client_secret=client_secret
    )
    token = credential.get_token("https://purview.azure.net/.default")
    return token.token

async def add_labels_to_entity_async(session, endpoint, guid, tag, access_token):
    """Add labels to entity asynchronously"""
    url = f"{endpoint}/datamap/api/atlas/v2/entity/guid/{guid}/labels"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    payload = [tag]
    
    try:
        async with session.put(url, headers=headers, json=payload) as response:
            if response.status == 204:
                print(f"Labels added successfully {guid}")
            else:
                text = await response.text()
                print(f"Failed to add labels to {guid}. Status code: {response.status}")
                print(f"Response: {text}")
    except Exception as e:
        print(f"ERROR adding labels to {guid}: {e}")

def add_labels_to_entity(endpoint, guid, tag, access_token):
    """Synchronous version for backwards compatibility"""
    url = f"{endpoint}/datamap/api/atlas/v2/entity/guid/{guid}/labels"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    payload = [tag]

    response = requests.put(url, headers=headers, json=payload)
    
    if response.status_code == 204:
        print("Labels added successfully " + str(guid))
    else:
        print(f"Failed to add labels. Status code: {response.status_code}")
        print(f"Response: {response.text}")

async def process_tags_async(guid_list, tag, access_token, endpoint):
    """Process tags for multiple GUIDs in parallel"""
    # Create SSL context that doesn't verify certificates (for self-signed certs)
    import ssl
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for guid in guid_list:
            task = add_labels_to_entity_async(session, endpoint, guid, tag, access_token)
            tasks.append(task)
        
        await asyncio.gather(*tasks)

def main(guid, tag, parallel=True):
    guid_list = guid
    tag = tag
    access_token = get_access_token(tenant_id, client_id, client_secret)

    if parallel and len(guid_list) > 1:
        print(f"Using parallel processing for {len(guid_list)} assets...")
        asyncio.run(process_tags_async(guid_list, tag, access_token, purview_endpoint))
    else:
        # Sequential processing
        for guid in guid_list:
            add_labels_to_entity(purview_endpoint, guid, tag, access_token)
    

if __name__ == "__main__":
    main()