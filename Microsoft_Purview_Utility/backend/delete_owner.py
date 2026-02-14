import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Environment variables
tenant_id = os.getenv("TENANTID")
client_id = os.getenv("CLIENTID")
client_secret = os.getenv("CLIENTSECRET")
purview_endpoint = os.getenv("PURVIEWENDPOINT")
token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/token"
resource = "https://purview.azure.net"

def get_access_token():
    """Get access token for Purview API authentication."""
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'resource': resource
    }
    
    response = requests.post(token_url, headers=headers, data=data)
    
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        print(f"Failed to get access token. Status code: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def get_entity_details(endpoint, guid, access_token):
    """Get the current entity details from Purview."""
    url = f"{endpoint}/datamap/api/atlas/v2/entity/guid/{guid}"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    params = {
        "api-version": "4"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to get entity details. Status code: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def remove_entity_contact(endpoint, guid, contact_type, access_token):
    """
    Remove owner or expert contact from an entity.
    
    Args:
        endpoint (str): The Purview endpoint URL
        guid (str): The GUID of the entity to update
        contact_type (str): Either "Owner" or "Expert"
        access_token (str): Bearer token for authentication
    """
    # First get the existing entity details
    existing_entity = get_entity_details(endpoint, guid, access_token)
    if not existing_entity:
        print("Failed to get existing entity details. Aborting update.")
        return False

    url = f"{endpoint}/datamap/api/atlas/v2/entity"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    params = {
        "api-version": "4"
    }
    
    # Get existing contacts from the entity
    existing_contacts = existing_entity.get('entity', {}).get('contacts', {})
    
    # Build contacts object, removing the specified contact type
    contacts = existing_contacts.copy() if existing_contacts else {}
    
    # Remove the specified contact type
    if contact_type in contacts:
        del contacts[contact_type]
    
    # Get the complete existing entity
    existing_entity_data = existing_entity.get('entity', {})
    
    # Full payload structure - preserve all original entity data
    payload = {
        "referredEntities": existing_entity.get('referredEntities', {}),
        "entity": {
            "guid": guid,
            "typeName": existing_entity_data.get('typeName', 'Asset'),
            "attributes": existing_entity_data.get('attributes', {}),
            "contacts": contacts,
            "status": existing_entity_data.get('status', 'ACTIVE'),
            "createdBy": existing_entity_data.get('createdBy', 'ExampleCreator'),
            "updatedBy": existing_entity_data.get('updatedBy', 'ExampleUpdator'),
            "version": existing_entity_data.get('version', 0),
            "classifications": existing_entity_data.get('classifications', []),
            "meanings": existing_entity_data.get('meanings', []),
            "relationshipAttributes": existing_entity_data.get('relationshipAttributes', {})
        }
    }
    
    response = requests.post(url, headers=headers, params=params, json=payload)
    
    if response.status_code == 200:
        print(f"{contact_type} contact removed successfully for entity {guid}")
        return True
    else:
        print(f"Failed to remove {contact_type} contact. Status code: {response.status_code}")
        print(f"Response: {response.text}")
        return False

def main(guids, contact_type):
    """
    Remove owner or expert contact from multiple entities.
    
    Args:
        guids (list): List of entity GUIDs
        contact_type (str): Either "Owner" or "Expert"
    """
    print(f"Removing {contact_type} from {len(guids)} entities")
    
    access_token = get_access_token()
    
    if not access_token:
        print("Failed to get access token")
        return False
    
    success = True
    for guid in guids:
        if not remove_entity_contact(purview_endpoint, guid, contact_type, access_token):
            success = False
    
    return success

if __name__ == "__main__":
    main()
