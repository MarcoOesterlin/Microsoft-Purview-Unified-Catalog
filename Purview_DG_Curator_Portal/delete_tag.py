from azure.purview.catalog import PurviewCatalogClient
from azure.identity import ClientSecretCredential 
from azure.core.exceptions import HttpResponseError
import pandas as pd
import requests
import os
import dotenv
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

def get_catalog_client():
	credentials = get_credentials()
	client = PurviewCatalogClient(endpoint=purview_endpoint, credential=credentials, logging_enable=True)
	return client

def get_access_token(tenant_id, client_id, client_secret):
    credential = ClientSecretCredential(
        tenant_id=tenant_id, 
        client_id=client_id, 
        client_secret=client_secret
    )
    token = credential.get_token("https://purview.azure.net/.default")
    return token.token

def delete_labels_of_entity(endpoint, guid, tags, access_token):
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

def main(guids, tags):
    # Convert single values to lists if needed
    guid_list = [guids] if isinstance(guids, str) else guids
    tag_list = [tags] if isinstance(tags, str) else tags
    
    access_token = get_access_token(tenant_id, client_id, client_secret)

    for guid in guid_list:
        delete_labels_of_entity(purview_endpoint, guid, tag_list, access_token)

if __name__ == "__main__":
    # Example usage:
    # Single GUID and tag: main("guid1", "tag1")
    # Multiple GUIDs and tags: main(["guid1", "guid2"], ["tag1", "tag2"])
    main()