from azure.purview.datamap import DataMapClient
from azure.identity import ClientSecretCredential 
from azure.core.exceptions import HttpResponseError
import pandas as pd
from datetime import datetime
import uuid
import os
import notebookutils

class PurviewConfig:
    """Configuration class for Azure Purview authentication and endpoints.
    
    Stores the necessary credentials and endpoints for connecting to Azure Purview,
    including tenant ID, client ID, client secret, and Purview endpoints.
    """
    def __init__(self, keyvault_url: str):
        self.tenant_id = notebookutils.credentials.getSecret(keyvault_url, "TENANTID")
        self.client_id = notebookutils.credentials.getSecret(keyvault_url, "CLIENTID")
        self.client_secret = notebookutils.credentials.getSecret(keyvault_url, "CLIENTSECRET")
        self.purview_endpoint = notebookutils.credentials.getSecret(keyvault_url, "PURVIEWENDPOINT")
        self.purview_scan_endpoint = notebookutils.credentials.getSecret(keyvault_url, "PURVIEWSCANENDPOINT")
        self.purview_account_name = notebookutils.credentials.getSecret(keyvault_url, "PURVIEWACCOUNTNAME")

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
    
    def search_entities(self, keywords: str = "*", limit: int = 1000) -> pd.DataFrame:
        """Search for entities in Purview.

        Args:
            keywords: Search keywords (default: "*" to match all)
            limit: Maximum number of records per page (max 1000 per API limitations)

        Returns:
            DataFrame containing search results
        """
        df_list = []
        total_retrieved = 0
        page_count = 0

        try:
            # Prepare initial search request
            search_request = {
                "keywords": keywords,
                "limit": limit
            }

            print(f"Executing search with keywords: '{keywords}'")

            # Execute the initial query
            response = self.data_map_client.discovery.query(body=search_request)

            # Process results and handle pagination with continuation token
            while response and "value" in response:
                page_count += 1

                # Get count from first response
                if "@search.count" in response and page_count == 1:
                    total_count = response.get("@search.count", 0)
                    print(f"Found {total_count} total entities matching search criteria")
                    if total_count > 1000:
                        print(f"This will require multiple API calls to retrieve all {total_count} records")

                # Process current page of results
                if response["value"]:
                    current_page_count = len(response["value"])
                    total_retrieved += current_page_count
                    print(f"Page {page_count}: Retrieved {current_page_count} records (Total: {total_retrieved})")
                    
                    # Normalize the nested JSON data
                    df = pd.json_normalize(
                        response["value"],
                        sep='_',
                        max_level=2  # Limit nesting level to prevent overly complex column names
                    )
                    
                    # Add search score if present
                    if "@search.score" in response:
                        df["@search.score"] = response["@search.score"]
                    
                    df_list.append(df)
                else:
                    print(f"Page {page_count}: No results in current page")

                # Check if there's a continuation token for the next page
                continuation_token = None
                for key in response.keys():
                    if "continuation" in key.lower():
                        continuation_token = response[key]
                        print(f"Found continuation token with key: {key}")
                        # Display a portion of the actual token value
                        token_preview = str(continuation_token)
                        if len(token_preview) > 50:
                            token_preview = f"{token_preview[:50]}..."
                        print(f"Continuation token value: {token_preview}")
                        break

                if continuation_token:
                    # Update search request with continuation token
                    search_request = {
                        "keywords": keywords,
                        "limit": limit,
                        "continuationToken": continuation_token
                    }
                    # Get next page
                    print(f"Retrieving next page...")
                    response = self.data_map_client.discovery.query(body=search_request)
                else:
                    print("No continuation token found. Available response keys:")
                    for key in response.keys():
                        print(f"  - {key}")
                    print("No more pages available")
                    break

            # Combine all dataframes
            if df_list:
                final_df = pd.concat(df_list, ignore_index=True)
                print(f"Successfully retrieved {len(final_df)} total records across {page_count} pages")
                print("\nColumns in the final DataFrame:")
                for col in final_df.columns:
                    print(f"- {col}")
                return final_df
            else:
                print("No results found or unexpected response format")
                return pd.DataFrame()

        except HttpResponseError as e:
            print(f"Search error: {e}")
            return None

def main():
    """Main execution function for the data extraction and JSON export process.
    
    Orchestrates the workflow:
    1. Initializes Purview configuration
    2. Creates necessary client instance
    3. Performs Purview catalog search
    4. Processes search results into a DataFrame
    5. Exports processed data to JSON file
    """
    # Key Vault URL should be provided as a variable in the notebook
    keyvault_url = "https://your-keyvault-name.vault.azure.net"  # Replace this with your actual Key Vault URL
    
    now = datetime.utcnow()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    day = now.strftime("%d")
    run_id = int(now.strftime("%H%M%S%f"))

    # Initialize configurations with Key Vault URL
    purview_config = PurviewConfig(keyvault_url)
    
    # Create client
    purview_client = PurviewSearchClient(purview_config)
    
    # Perform search using search_entities method
    search_results = purview_client.search_entities()
    
    if search_results is not None:
        # Process results
        jdf = search_results.copy()
        
        # Convert all dictionary/object columns to strings
        for column in jdf.columns:
            if jdf[column].dtype == 'object':
                jdf[column] = jdf[column].apply(lambda x: str(x) if isinstance(x, (dict, list)) else x)

        # Create directory path
        path = f"/lakehouse/default/Files/data/load_type=full/year={year}/month={month}/day={day}/run_id={run_id}"
        os.makedirs(path, exist_ok=True)

        # Generate unique filename with .json extension
        output_filename = f"{str(uuid.uuid4())}.json"
        output_filepath = os.path.join(path, output_filename)

        try:
            # Convert DataFrame directly to JSON using to_json
            jdf.to_json(output_filepath, orient='records', indent=2, date_format='iso')
            print(f"Data successfully exported to {output_filepath}")
        except Exception as e:
            print(f"Export error: {e}")

if __name__ == "__main__":
    main()