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

def add_classification_to_entity(endpoint, guid, classifications, access_token):
    url = f"{endpoint}/datamap/api/atlas/v2/entity/guid/{guid}/classifications?api-version=2023-09-01"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    # classifications should be a list of dicts, each with 'typeName' (string)
    print(f"\nSending classifications to entity GUID: {guid}")
    print(f"Payload: {classifications}")
    response = requests.post(url, headers=headers, json=classifications)
    if response.status_code == 204:
        print(f"SUCCESS: Classifications added to {guid}")
    else:
        print(f"FAILED: Could not add classifications to {guid}. Status code: {response.status_code}")
        print(f"Response: {response.text}")

def main(guid_list, classification_type_names):
    print("Starting classification addition process...")
    access_token = get_access_token(tenant_id, client_id, client_secret)
    for guid in guid_list:
        # For each guid, build a list of classification dicts (one per typeName)
        classifications = [
            {"typeName": type_name}
            for type_name in classification_type_names
        ]
        add_classification_to_entity(purview_endpoint, guid, classifications, access_token)
    print("\nClassification addition process completed.")

if __name__ == "__main__":
    # Example usage:
    # main(["your-entity-guid"], ["MICROSOFT.FINANCIAL.US.ABA_ROUTING_NUMBER", "MICROSOFT.FINANCIAL.CREDIT_CARD_NUMBER"])
    main([], [])