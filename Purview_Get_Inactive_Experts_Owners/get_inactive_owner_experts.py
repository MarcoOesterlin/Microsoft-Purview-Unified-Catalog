from azure.identity import ClientSecretCredential 
import requests
import dotenv
import os
import pandas as pd
import asyncio
from azure.purview.datamap import DataMapClient
from azure.identity import ClientSecretCredential 
from azure.core.exceptions import HttpResponseError
from datetime import datetime
import ast
dotenv.load_dotenv()


class PurviewConfig:
    """
    Configuration class for Azure Purview authentication and endpoints.
    
    This class manages all the necessary credentials and endpoints for connecting 
    to Azure Purview, including tenant ID, client ID, client secret, and Purview endpoints.
    All configuration values are loaded from environment variables.
    
    Attributes:
        tenant_id (str): Azure AD tenant ID
        client_id (str): Service principal client ID
        client_secret (str): Service principal client secret
        purview_endpoint (str): Purview catalog endpoint URL
        purview_scan_endpoint (str): Purview scan endpoint URL
        purview_account_name (str): Purview account name
        token_url (str): OAuth2 token endpoint URL
        resource (str): Azure Purview resource identifier
    """
    def __init__(self):
        """Initialize PurviewConfig with values from environment variables."""
        self.tenant_id = os.getenv("TENANTID")
        self.client_id = os.getenv("CLIENTID")
        self.client_secret = os.getenv("CLIENTSECRET")
        self.purview_endpoint = os.getenv("PURVIEWENDPOINT")
        self.purview_scan_endpoint = os.getenv("PURVIEWSCANENDPOINT")
        self.purview_account_name = os.getenv("PURVIEWACCOUNTNAME")
        self.token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/token"
        self.resource = "https://purview.azure.net"


class PurviewSearchClient:
    """
    Client for performing searches in Azure Purview.
    
    This class handles authentication and search operations against the Azure Purview catalog,
    with support for paginated results retrieval using continuation tokens. It provides
    methods to list collections and search for entities across all collections.
    
    Args:
        config (PurviewConfig): Configuration object containing Purview credentials and endpoints.
    
    Attributes:
        config (PurviewConfig): Configuration object with Purview settings
        credentials (ClientSecretCredential): Authenticated Azure credentials
        data_map_client (DataMapClient): Purview data map client for API operations
    """
    def __init__(self, config: PurviewConfig):
        """Initialize the PurviewSearchClient with configuration and create authenticated clients."""
        self.config = config
        self.credentials = self._get_credentials()
        self.data_map_client = self._get_data_map_client()
        
    def _get_credentials(self):
        """
        Create Azure client credentials object using service principal authentication.
        
        Returns:
            ClientSecretCredential: Authenticated credentials for Azure services.
        """
        return ClientSecretCredential(
            client_id=self.config.client_id,
            client_secret=self.config.client_secret,
            tenant_id=self.config.tenant_id
        )
    
    def _get_data_map_client(self):
        """
        Initialize the Purview DataMapClient for data map operations.
        
        Returns:
            DataMapClient: Authenticated client for Purview data map operations.
        """
        account_endpoint = f"https://{self.config.purview_account_name}.purview.azure.com"
        return DataMapClient(endpoint=account_endpoint, credential=self.credentials)

    def get_access_token(self):
        """
        Fetch the access token using client credentials flow.
        
        This method uses the OAuth2 client credentials flow to obtain an access token
        for Azure Purview API operations.
        
        Returns:
            str: Access token for Azure Purview API calls, or None if failed.
        """
        body = {
            'client_id': self.config.client_id,
            'client_secret': self.config.client_secret,
            'grant_type': 'client_credentials',
            'resource': self.config.resource
        }

        response = requests.post(self.config.token_url, data=body)

        if response.status_code == 200:
            access_token = response.json().get('access_token')
            return access_token
        else:
            print("Error occurred when getting access token for Purview data access.")
            return None

    def list_collections(self):
        """
        List all collections in Azure Purview with pagination support.
        
        This method retrieves all collections from the Purview catalog using the
        collections API with automatic pagination handling.
        
        Returns:
            list: List of collection names/IDs from the Purview catalog.
        """
        url = f"{self.config.purview_endpoint}/collections?api-version=2019-11-01-preview"
        headers = {
            "Authorization": f"Bearer {self.get_access_token()}",
            "Content-Type": "application/json"
        }
        
        collection_ids = []
        next_link = url

        while next_link:
            response = requests.get(next_link, headers=headers)

            if response.status_code != 200:
                print(f"Failed to retrieve collections. Status Code: {response.status_code}, Response: {response.text}")
                return collection_ids

            data = response.json()
            collections = data.get("value", [])
            collection_ids.extend([collection["name"] for collection in collections])

            next_link = data.get("nextLink")

        return collection_ids
    
    def search_entities(self, collection_ids: list, keywords: str = "*", limit: int = 1000) -> pd.DataFrame:
        """
        Search for entities in Purview with batching and pagination support.

        This method performs searches across multiple collections with automatic pagination
        to handle large datasets. It uses cursor-based pagination for efficient data retrieval.

        Args:
            collection_ids (list): List of collection IDs to search within
            keywords (str): Search keywords (default: "*" to match all entities)
            limit (int): Maximum number of records per page (max 1000 per API limitations)

        Returns:
            pd.DataFrame: DataFrame containing search results with all entity data
        """
        all_df_list = []
        total_records = 0

        for collection_id in collection_ids:
            df_list = []
            total_retrieved = 0
            last_entity_id = None

            try:
                print(f"Executing search with keywords: '{keywords}' for collection: '{collection_id}'")

                while True:
                    # Prepare search request with collection filter
                    search_request = {
                        "keywords": keywords,
                        "limit": limit,
                        "filter": {
                            "and": [{"collectionId": collection_id}]
                        },
                        "offset": 0,
                        "orderby": [{"id": "asc"}]
                    }

                    # Modify search request for pagination using ID-based cursor
                    if last_entity_id is not None:
                        search_request = {
                            "keywords": keywords,
                            "limit": limit,
                            "filter": {
                                "and": [
                                    {"collectionId": collection_id},
                                    {"id": {"operator": "gt", "value": last_entity_id}}
                                ]
                            },
                            "offset": 0,
                            "orderby": [{"id": "asc"}]
                        }

                    response = self.data_map_client.discovery.query(body=search_request)

                    if not response or "value" not in response:
                        print(f"No data or invalid response received. Response: {response}")
                        break

                    if response["value"]:
                        # Log all retrieved IDs for debugging
                        ids_in_request = [entity['id'] for entity in response['value']]

                        current_page_count = len(response["value"])
                        total_retrieved += current_page_count
                        total_records += current_page_count
                        print(f"Collection '{collection_id}', Page {total_retrieved // limit}: Retrieved {current_page_count} records (Total: {total_records})")

                        # Normalize JSON response to DataFrame
                        df = pd.json_normalize(
                            response["value"],
                            sep='_',
                            max_level=2
                        )

                        df_list.append(df)

                        # Update cursor for next page
                        last_entity_id = ids_in_request[-1]
                        print(f"Last entity ID for next page: {last_entity_id}")

                        # Check if we've retrieved all available records
                        if current_page_count < limit:
                            print("No more pages needed. All results retrieved.")
                            break
                    else:
                        print(f"Collection '{collection_id}': No results in current page")
                        break

                # Combine all pages for this collection
                if df_list:
                    final_df = pd.concat(df_list, ignore_index=True)
                    print(f"Successfully retrieved {len(final_df)} total records for collection '{collection_id}'")
                    all_df_list.append(final_df)

            except HttpResponseError as e:
                print(f"Search error for collection '{collection_id}': {e}")
                continue

        # Combine all collections into final DataFrame
        if all_df_list:
            combined_df = pd.concat(all_df_list, ignore_index=True)
            print(f"Successfully combined all records into a single dataframe with {len(combined_df)} total records")
            return combined_df
        else:
            print("No results found for any collection or unexpected response format")
            return pd.DataFrame()


def get_graph_client():
    """
    Create Azure client credentials for Microsoft Graph API access.
    
    This function creates a ClientSecretCredential object configured for
    Microsoft Graph API operations using environment variables.
    
    Returns:
        ClientSecretCredential: Authenticated credentials for Microsoft Graph API.
    """
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
    """
    Create a pandas DataFrame from Microsoft Graph users data.
    
    This function extracts only the essential user information (id and displayName)
    from the Microsoft Graph API response and creates a clean DataFrame.
    
    Args:
        users_data (dict): Raw response from Microsoft Graph users API
        
    Returns:
        pd.DataFrame: DataFrame containing user IDs and display names
    """
    # Extract only id and displayName from each user
    users_list = [{'id': user['id'], 'displayName': user['displayName']} for user in users_data['value']]
    # Create DataFrame
    df = pd.DataFrame(users_list)
    return df

async def get_entraid_users(credential):
    """
    Fetch all users from Azure Entra ID using Microsoft Graph API.
    
    This function retrieves the list of all active users in the Azure Entra ID tenant
    using the Microsoft Graph API. It handles authentication and data processing.
    
    Args:
        credential (ClientSecretCredential): Authenticated credentials for Microsoft Graph
        
    Returns:
        pd.DataFrame: DataFrame containing all active users with their IDs and display names
    """
    token = credential.get_token("https://graph.microsoft.com/.default")
    headers = {
        'Authorization': f'Bearer {token.token}',
        'Content-Type': 'application/json'
    }
    response = requests.get('https://graph.microsoft.com/v1.0/users', headers=headers)
    users_data = response.json()
    return create_users_dataframe(users_data)

async def main():
    """
    Main function that orchestrates the entire inactive users detection process.
    
    This function performs the following steps:
    1. Initialize Purview configuration and clients
    2. Retrieve all collections from Purview
    3. Search for all entities across collections
    4. Extract and process contact information
    5. Fetch active users from Azure Entra ID
    6. Compare contact IDs with active users to identify inactive contacts
    7. Generate and display the final report
    """
    # Initialize configurations
    purview_config = PurviewConfig()
    
    # Create Purview client and get collections
    purview_client = PurviewSearchClient(purview_config)
    collection_ids = purview_client.list_collections()
    credential = get_graph_client()
    
    # Perform search using search_entities method
    search_results = purview_client.search_entities(collection_ids=collection_ids)
    
    if search_results is not None:
        # Process results
        jdf = search_results.copy()
        
        # Filter jdf to keep only 'id', 'name', and 'contact' columns
        columns_to_keep = [col for col in ['id', 'name', 'contact'] if col in jdf.columns]
        jdf = jdf[columns_to_keep]
        
        # Count unique values in 'id' column for summary
        if 'id' in jdf.columns:
            unique_id_count = jdf['id'].nunique()
            print(f"Number of unique values in 'id' column: {unique_id_count}")
        else:
            print("Column 'id' not found in the DataFrame.")
        
        # Convert all dictionary/object columns to strings for processing
        for column in jdf.columns:
            if jdf[column].dtype == 'object':
                jdf[column] = jdf[column].apply(lambda x: str(x) if isinstance(x, (dict, list)) else x)

        # Unnest 'contact' column and extract name, id, owner, and expert ids into a new DataFrame
        extracted_rows = []
        for _, row in jdf.iterrows():
            contact_val = row.get('contact')
            if pd.notnull(contact_val) and contact_val != '':
                # Parse string to list if needed (handle different data formats)
                if isinstance(contact_val, str):
                    try:
                        contact_list = ast.literal_eval(contact_val)
                    except Exception:
                        continue
                elif isinstance(contact_val, list):
                    contact_list = contact_val
                else:
                    continue
                
                # Extract owner and expert IDs from contact information
                owner_ids = [c['id'] for c in contact_list if isinstance(c, dict) and c.get('contactType') == 'Owner']
                expert_ids = [c['id'] for c in contact_list if isinstance(c, dict) and c.get('contactType') == 'Expert']
                
                # Convert arrays to clean comma-separated strings without brackets or quotes
                owner_ids_str = str(tuple(owner_ids)).replace('(', '').replace(',', '').replace(')', '').replace("'", '') if owner_ids else ''
                expert_ids_str = str(tuple(expert_ids)).replace('(', '').replace(',', '').replace(')', '').replace("'", '') if expert_ids else ''
                
                # Add extracted data to results
                extracted_rows.append({
                    'name': row.get('name'),
                    'id': row.get('id'),
                    'owner_ids': owner_ids_str,
                    'expert_ids': expert_ids_str
                })
        extracted_df = pd.DataFrame(extracted_rows)

        try:
            print(extracted_df)

        except Exception as e:
            print(f"Export error: {e}")

        # Fetch active users from Azure Entra ID
        users_df = await get_entraid_users(credential)
        print(users_df)

        # Compare owner_ids and expert_ids with users_df to identify inactive users
        active_user_ids = set(users_df['id'].tolist())
        
        inactive_assets = []
        for _, row in extracted_df.iterrows():
            owner_ids_str = row['owner_ids']
            expert_ids_str = row['expert_ids']
            
            # Parse owner_ids and expert_ids back to lists for comparison
            owner_ids = [id.strip() for id in owner_ids_str.split(',')] if owner_ids_str else []
            expert_ids = [id.strip() for id in expert_ids_str.split(',')] if expert_ids_str else []
            
            # Check if any owner or expert is inactive (not in active users list)
            inactive_owners = [id for id in owner_ids if id and id not in active_user_ids]
            inactive_experts = [id for id in expert_ids if id and id not in active_user_ids]
            
            # If there are any inactive users, add to results
            if inactive_owners or inactive_experts:
                inactive_assets.append({
                    'name': row['name'],
                    'id': row['id'],
                    'owner_ids': owner_ids_str,
                    'expert_ids': expert_ids_str,
                })
        
        # Create final report DataFrame
        inactive_df = pd.DataFrame(inactive_assets)
        print("Assets with inactive owners/experts:")
        print(inactive_df)

if __name__ == "__main__":
    # Run the main function asynchronously
    asyncio.run(main())
