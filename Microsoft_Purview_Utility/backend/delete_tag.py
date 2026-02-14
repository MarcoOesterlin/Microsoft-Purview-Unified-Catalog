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

def get_access_token(tenant_id, client_id, client_secret):
    credential = ClientSecretCredential(
        tenant_id=tenant_id, 
        client_id=client_id, 
        client_secret=client_secret
    )
    token = credential.get_token("https://purview.azure.net/.default")
    return token.token

async def delete_labels_of_entity_async(session, endpoint, guid, tags, access_token):
    """Delete labels from entity asynchronously"""
    url = f"{endpoint}/datamap/api/atlas/v2/entity/guid/{guid}/labels"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    clean_tags = [tag.strip("'[]").strip() for tag in tags]
    payload = clean_tags
    
    try:
        async with session.delete(url, headers=headers, json=payload) as response:
            if response.status == 204:
                print(f"Labels {clean_tags} deleted successfully for GUID: {guid}")
            else:
                text = await response.text()
                print(f"Failed to delete labels for GUID {guid}. Status code: {response.status}")
                print(f"Response: {text}")
    except Exception as e:
        print(f"ERROR deleting labels from {guid}: {e}")

def delete_labels_of_entity(endpoint, guid, tags, access_token):
    """Synchronous version for backwards compatibility"""
    url = f"{endpoint}/datamap/api/atlas/v2/entity/guid/{guid}/labels"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Clean and process multiple tags
    clean_tags = [tag.strip("'[]").strip() for tag in tags]
    payload = clean_tags

    response = requests.delete(url, headers=headers, json=payload)
    
    if response.status_code == 204:
        print(f"Labels {clean_tags} deleted successfully for GUID: {guid}")
    else:
        print(f"Failed to delete labels for GUID {guid}. Status code: {response.status_code}")
        print(f"Response: {response.text}")

async def process_tag_deletion_async(guid_list, tag_list, access_token, endpoint):
    """Process tag deletion for multiple GUIDs in parallel"""
    # Create SSL context that doesn't verify certificates (for self-signed certs)
    import ssl
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for guid in guid_list:
            task = delete_labels_of_entity_async(session, endpoint, guid, tag_list, access_token)
            tasks.append(task)
        
        await asyncio.gather(*tasks)

def main(guids, tags, parallel=True):
    # Convert single values to lists if needed
    guid_list = [guids] if isinstance(guids, str) else guids
    tag_list = [tags] if isinstance(tags, str) else tags
    
    access_token = get_access_token(tenant_id, client_id, client_secret)

    if parallel and len(guid_list) > 1:
        print(f"Using parallel processing for {len(guid_list)} assets...")
        asyncio.run(process_tag_deletion_async(guid_list, tag_list, access_token, purview_endpoint))
    else:
        # Sequential processing
        for guid in guid_list:
            delete_labels_of_entity(purview_endpoint, guid, tag_list, access_token)

if __name__ == "__main__":
    # Example usage:
    # Single GUID and tag: main("guid1", "tag1")
    # Multiple GUIDs and tags: main(["guid1", "guid2"], ["tag1", "tag2"])
    main()