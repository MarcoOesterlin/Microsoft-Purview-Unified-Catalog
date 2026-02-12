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
    # Check if the response contains the expected 'value' key
    if 'value' not in users_data:
        print("="*80)
        print("ERROR: Microsoft Graph API returned an unexpected response")
        print("="*80)
        if 'error' in users_data:
            error_details = users_data.get('error', {})
            print(f"Error Code: {error_details.get('code', 'Unknown')}")
            print(f"Error Message: {error_details.get('message', 'No message provided')}")
        else:
            print(f"Full Response: {users_data}")
        print("\nPossible causes:")
        print("  1. Invalid credentials (TENANTID, CLIENTID, or CLIENTSECRET)")
        print("  2. Missing API permissions (User.Read.All)")
        print("  3. Admin consent not granted")
        print("="*80)
        # Return empty DataFrame if no valid data
        return pd.DataFrame(columns=['id', 'displayName'])
    
    # Extract only id and displayName from each user
    users_list = [{'id': user['id'], 'displayName': user['displayName']} for user in users_data['value']]
    # Create DataFrame
    df = pd.DataFrame(users_list)
    return df

async def get_entraid_users(credential):
    try:
        token = credential.get_token("https://graph.microsoft.com/.default")
        headers = {
            'Authorization': f'Bearer {token.token}',
            'Content-Type': 'application/json'
        }
        response = requests.get('https://graph.microsoft.com/v1.0/users', headers=headers)
        
        # Check if request was successful
        if response.status_code != 200:
            print("="*80)
            print(f"ERROR: Microsoft Graph API request failed")
            print("="*80)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            print("="*80)
            return pd.DataFrame(columns=['id', 'displayName'])
        
        users_data = response.json()
        return create_users_dataframe(users_data)
    except Exception as e:
        print("="*80)
        print(f"EXCEPTION: Error while fetching Entra ID users")
        print("="*80)
        print(f"Exception Type: {type(e).__name__}")
        print(f"Exception Message: {str(e)}")
        print("="*80)
        return pd.DataFrame(columns=['id', 'displayName'])

async def main():
    credential = get_graph_client()
    return await get_entraid_users(credential)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
