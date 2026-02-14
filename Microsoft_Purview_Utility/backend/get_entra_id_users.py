from azure.identity import ClientSecretCredential 
import requests
import dotenv
import os
import pandas as pd

dotenv.load_dotenv()

def get_graph_client():
    scopes = ['https://graph.microsoft.com/.default']

    tenant_id = os.getenv("TENANTID")
    client_id = os.getenv("CLIENTID")
    client_secret = os.getenv("CLIENTSECRET")

    credential = ClientSecretCredential(
        tenant_id = tenant_id,
        client_id = client_id,
        client_secret = client_secret
    )

    return credential

def create_users_dataframe(users_data):
    # Extract only id and displayName from each user
    users_list = [{'id': user['id'], 'displayName': user['displayName']} for user in users_data['value']]
    # Create DataFrame
    df = pd.DataFrame(users_list)
    return df

async def get_entraid_users(credential):
    token = credential.get_token("https://graph.microsoft.com/.default")
    headers = {
        'Authorization': f'Bearer {token.token}',
        'Content-Type': 'application/json'
    }
    response = requests.get('https://graph.microsoft.com/v1.0/users', headers=headers)
    users_data = response.json()
    return create_users_dataframe(users_data)

async def main():
    credential = get_graph_client()
    return await get_entraid_users(credential)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
