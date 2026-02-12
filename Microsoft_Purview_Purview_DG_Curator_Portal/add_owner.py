import requests
import json
import os

# Environment variables
tenant_id = os.getenv("TENANTID")
client_id = os.getenv("CLIENTID")
client_secret = os.getenv("CLIENTSECRET")
purview_endpoint = os.getenv("PURVIEWENDPOINT")
purview_scan_endpoint = os.getenv("PURVIEWSCANENDPOINT")
purview_account_name = os.getenv("PURVIEWACCOUNTNAME")
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
    """
    Get the current entity details from Purview.
    
    Args:
        endpoint (str): The Purview endpoint URL
        guid (str): The GUID of the entity to get
        access_token (str): Bearer token for authentication
    
    Returns:
        dict: The entity details if successful, None otherwise
    """
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

def update_entity_contacts(endpoint, guid, owner_id=None, owner_info=None, expert_id=None, expert_info=None, access_token=None, type_name=None):
    """
    Update only the contacts (owner and/or expert) for an entity using the entity GUID.
    
    Args:
        endpoint (str): The Purview endpoint URL
        guid (str): The GUID of the entity to update
        owner_id (str, optional): UUID of the owner to update
        owner_info (str, optional): Information about the owner to update
        expert_id (str, optional): UUID of the expert to update
        expert_info (str, optional): Information about the expert to update
        access_token (str, optional): Bearer token for authentication
        type_name (str, optional): The type name of the entity
    """
    # First get the existing entity details
    existing_entity = get_entity_details(endpoint, guid, access_token)
    if not existing_entity:
        print("Failed to get existing entity details. Aborting update.")
        return

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
    
    # Build contacts object preserving existing contacts
    contacts = existing_contacts.copy() if existing_contacts else {}
    
    if owner_id or owner_info:
        if "Owner" not in contacts:
            contacts["Owner"] = [{}]
        if owner_id:
            contacts["Owner"][0]["id"] = owner_id
        if owner_info:
            contacts["Owner"][0]["info"] = owner_info
    
    if expert_id or expert_info:
        if "Expert" not in contacts:
            contacts["Expert"] = [{}]
        if expert_id:
            contacts["Expert"][0]["id"] = expert_id
        if expert_info:
            contacts["Expert"][0]["info"] = expert_info
    
    # Get the complete existing entity
    existing_entity_data = existing_entity.get('entity', {})
    
    # Full payload structure - preserve all original entity data
    payload = {
        "referredEntities": existing_entity.get('referredEntities', {}),
        "entity": {
            "guid": guid,
            "typeName": type_name or existing_entity_data.get('typeName', 'Asset'),
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
        print(f"Contacts updated successfully for entity {guid}")
    else:
        print(f"Failed to update contacts. Status code: {response.status_code}")
        print(f"Response: {response.text}")

def main(contact, guid, id, notes, type_name=None):
    print(contact)
    print(guid)
    print(id)
    print(notes)
    print(type_name)

    access_token = get_access_token()
    
    if access_token:
        entity_guid = guid
        
        # Update only owner contact
        if contact == "Owner":
            update_entity_contacts(
                endpoint=purview_endpoint,
                guid=entity_guid,
                owner_id=id,
                owner_info=notes,
                access_token=access_token,
                type_name=type_name
            )
        
        if contact == "Expert":
        # Update only expert contact
            update_entity_contacts(
                endpoint=purview_endpoint,
                guid=entity_guid,
                expert_id=id,
                expert_info=notes,
                access_token=access_token,
                type_name=type_name
            )
        
    else:
        print("Failed to get access token")

if __name__ == "__main__":
    main()