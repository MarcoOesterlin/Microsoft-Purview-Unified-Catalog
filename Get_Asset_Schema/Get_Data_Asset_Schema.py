from azure.purview.datamap import DataMapClient
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.core.exceptions import HttpResponseError
import os
from dotenv import load_dotenv
import json

# Load environment variables from .env file
load_dotenv()

def get_asset_schema(asset_id):
    """Get the schema of a specific asset from Azure Purview."""
    # Get credentials and endpoint
    tenant_id = os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    purview_account_name = os.getenv("PURVIEW_ACCOUNT_NAME")
    purview_endpoint = os.getenv("PURVIEW_ENDPOINT")
    
    # Construct endpoint if needed
    if not purview_endpoint and purview_account_name:
        purview_endpoint = f"https://{purview_account_name}.purview.azure.com"
    
    # Create credential
    if all([tenant_id, client_id, client_secret]):
        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )
    else:
        credential = DefaultAzureCredential()
    
    # Create client
    client = DataMapClient(endpoint=purview_endpoint, credential=credential)
    
    try:
        # Get entity by ID using the entity API
        response = client.entity.get_by_ids(guid=[asset_id])
        
        if not response or 'entities' not in response or not response['entities']:
            return None
        
        # Extract schema information - the response structure is different with get_by_ids
        entity = response['entities'][0]
        
        # Check for columns in relationshipAttributes
        if 'relationshipAttributes' in entity and 'columns' in entity['relationshipAttributes']:
            return entity['relationshipAttributes']['columns']
        
        # Check for columns in the entity
        if 'columns' in entity:
            return entity['columns']
        
        # Check for columns in attributes
        if 'attributes' in entity and 'columns' in entity['attributes']:
            return entity['attributes']['columns']
        
        return None
        
    except HttpResponseError as e:
        print(f"Error retrieving entity: {e}")
        return None

def main():
    # Target asset ID
    asset_id = "INSET GUID HERE"
    
    # Get schema
    schema = get_asset_schema(asset_id)
    
    # Print schema if found
    if schema:
        print(json.dumps(schema, indent=2))

if __name__ == "__main__":
    main()