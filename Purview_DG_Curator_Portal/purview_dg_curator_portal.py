from azure.purview.datamap import DataMapClient
from azure.identity import ClientSecretCredential 
from azure.core.exceptions import HttpResponseError
import pandas as pd
from datetime import datetime
import os
import requests
import dotenv
dotenv.load_dotenv()



class PurviewConfig:
    """Configuration class for Azure Purview authentication and endpoints.

    
    Stores the necessary credentials and endpoints for connecting to Azure Purview,
    including tenant ID, client ID, client secret, and Purview endpoints.
    """
    def __init__(self):
        self.tenant_id = os.getenv("TENANTID")
        self.client_id = os.getenv("CLIENTID")
        self.client_secret = os.getenv("CLIENTSECRET")
        self.purview_endpoint = os.getenv("PURVIEWENDPOINT")
        self.purview_scan_endpoint = os.getenv("PURVIEWSCANENDPOINT")
        self.purview_account_name = os.getenv("PURVIEWACCOUNTNAME")
        self.token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/token"
        self.resource = "https://purview.azure.net"


class PurviewSearchClient:
    """Client for performing searches in Azure Purview.
    
    Handles authentication and search operations against the Azure Purview catalog,
    with support for paginated results retrieval using continuation tokens.
    
    Args:
        config (PurviewConfig): Configuration object containing Purview credentials and endpoints.
    """
    def __init__(self, config: PurviewConfig):
        self.config = config
        self.credentials = self._get_credentials()
        self.data_map_client = self._get_data_map_client()
        
    def _get_credentials(self):
        """Create Azure client credentials object.
        
        Returns:
            ClientSecretCredential: Authenticated credentials for Azure services.
        """
        return ClientSecretCredential(
            client_id=self.config.client_id,
            client_secret=self.config.client_secret,
            tenant_id=self.config.tenant_id
        )
    
    def _get_data_map_client(self):
        """Initialize the Purview DataMapClient.
        
        Returns:
            DataMapClient: Authenticated client for Purview data map operations.
        """
        account_endpoint = f"https://{self.config.purview_account_name}.purview.azure.com"
        return DataMapClient(endpoint=account_endpoint, credential=self.credentials)

    def get_access_token(self):
        """Fetch the access token using client credentials."""
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
        """List all collections in Azure Purview with pagination."""
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
        """Search for entities in Purview with batching support.

        Args:
            keywords: Search keywords (default: "*" to match all)
            limit: Maximum number of records per page (max 1000 per API limitations)

        Returns:
            DataFrame containing search results
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
                    # Prepare search request
                    search_request = {
                        "keywords": keywords,
                        "limit": limit,
                        "filter": {
                            "and": [{"collectionId": collection_id}]
                        },
                        "offset": 0,
                        "orderby": [{"id": "asc"}]
                    }

                    if last_entity_id is not None:
                        # Modify search request for pagination using ID
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
                        # Log all retrieved IDs
                        ids_in_request = [entity['id'] for entity in response['value']]

                        current_page_count = len(response["value"])
                        total_retrieved += current_page_count
                        total_records += current_page_count
                        print(f"Collection '{collection_id}', Page {total_retrieved // limit}: Retrieved {current_page_count} records (Total: {total_records})")

                        df = pd.json_normalize(
                            response["value"],
                            sep='_',
                            max_level=2
                        )

                        df_list.append(df)

                        # Ensure that the last ID is correctly updated
                        last_entity_id = ids_in_request[-1]
                        print(f"Last entity ID for next page: {last_entity_id}")

                        # If less than 'limit' count returned, no more pages needed
                        if current_page_count < limit:
                            print("No more pages needed. All results retrieved.")
                            break
                    else:
                        print(f"Collection '{collection_id}': No results in current page")
                        break

                if df_list:
                    final_df = pd.concat(df_list, ignore_index=True)
                    print(f"Successfully retrieved {len(final_df)} total records for collection '{collection_id}'")
                    all_df_list.append(final_df)

            except HttpResponseError as e:
                print(f"Search error for collection '{collection_id}': {e}")
                continue

        if all_df_list:
            combined_df = pd.concat(all_df_list, ignore_index=True)
            print(f"Successfully combined all records into a single dataframe with {len(combined_df)} total records")
            return combined_df
        else:
            print("No results found for any collection or unexpected response format")
            return pd.DataFrame()

def main():
    """Main execution function for the data extraction and JSON export process.
    
    Orchestrates the workflow:
    1. Initializes Purview configuration
    2. Creates necessary client instance
    3. Performs Purview catalog search
    4. Processes search results into a DataFrame
    5. Exports processed data to JSON file
    """

    # Initialize configurations
    purview_config = PurviewConfig()
    
    # Create client
    purview_client = PurviewSearchClient(purview_config)
    collection_ids = purview_client.list_collections()
    
    # Perform search using search_entities method
    search_results = purview_client.search_entities(collection_ids=collection_ids)
    
    if search_results is not None:
        # Process results
        jdf = search_results.copy()
        
        # Count unique values in 'id' column
        if 'id' in jdf.columns:
            unique_id_count = jdf['id'].nunique()
            print(f"Number of unique values in 'id' column: {unique_id_count}")
        else:
            print("Column 'id' not found in the DataFrame.")
        
        # Convert all dictionary/object columns to strings
        for column in jdf.columns:
            if jdf[column].dtype == 'object':
                jdf[column] = jdf[column].apply(lambda x: str(x) if isinstance(x, (dict, list)) else x)

        try:
            print(jdf)
            return jdf
        except Exception as e:
            print(f"Export error: {e}")

if __name__ == "__main__":
    main()