from azure.purview.datamap import DataMapClient
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.core.exceptions import HttpResponseError
import pandas as pd
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class PurviewConfig:
    """Configuration class for Azure Purview authentication and endpoints.
    
    Stores the necessary credentials and endpoints for connecting to Azure Purview,
    including tenant ID, client ID, client secret, and Purview endpoints.
    """
    def __init__(self):
        # Try to get values from parameters first, then environment variables
        self.tenant_id = os.getenv("AZURE_TENANT_ID")
        self.client_id = os.getenv("AZURE_CLIENT_ID")
        self.client_secret = os.getenv("AZURE_CLIENT_SECRET")
        self.purview_account_name = os.getenv("PURVIEW_ACCOUNT_NAME")
        self.purview_endpoint = os.getenv("PURVIEW_ENDPOINT")
        
        # If purview_endpoint is not set but purview_account_name is, construct the endpoint URL
        if not self.purview_endpoint and self.purview_account_name:
            self.purview_endpoint = f"https://{self.purview_account_name}.purview.azure.com"
            
        # Print configuration for debugging (excluding secrets)
        print(f"Configuration:")
        print(f"  Tenant ID: {'Configured' if self.tenant_id else 'Not configured'}")
        print(f"  Client ID: {'Configured' if self.client_id else 'Not configured'}")
        print(f"  Client Secret: {'Configured' if self.client_secret else 'Not configured'}")
        print(f"  Purview Account Name: {self.purview_account_name or 'Not configured'}")
        print(f"  Purview Endpoint: {self.purview_endpoint or 'Not configured'}")


class PurviewClient:
    """Client for performing operations in Azure Purview.
    
    Handles authentication and operations against the Azure Purview datamap,
    with support for searching and adding PII labels.
    
    Args:
        config (PurviewConfig): Configuration object containing Purview credentials and endpoints.
    """
    def __init__(self, config: PurviewConfig):
        self.config = config
        self.credential = self._get_credential()
        self.datamap_client = self._get_datamap_client()
        
    def _get_credential(self):
        """Create Azure credential object.
        
        Returns:
            Azure credential object for authentication.
        """
        if all([self.config.tenant_id, self.config.client_id, self.config.client_secret]):
            print("Using ClientSecretCredential for authentication")
            return ClientSecretCredential(
                tenant_id=self.config.tenant_id,
                client_id=self.config.client_id,
                client_secret=self.config.client_secret
            )
        else:
            print("Using DefaultAzureCredential for authentication")
            # Fall back to DefaultAzureCredential if service principal credentials not provided
            return DefaultAzureCredential()
    
    def _get_datamap_client(self):
        """Initialize the Purview datamap client.
        
        Returns:
            DataMapClient: Authenticated client for Purview datamap operations.
        """
        if not self.config.purview_endpoint:
            raise ValueError("Purview endpoint is not configured. Please provide either a purview_account_name or purview_endpoint.")
            
        print(f"Initializing DataMapClient with endpoint: {self.config.purview_endpoint}")
        return DataMapClient(
            endpoint=self.config.purview_endpoint,
            credential=self.credential
        )
    
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
            response = self.datamap_client.discovery.query(body=search_request)
            
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
                    df = pd.DataFrame(response["value"])
                    df_list.append(df)
                else:
                    print(f"Page {page_count}: No results in current page")
                
                # Debug: Print all keys in the response to see what's available
                print(f"Response keys: {list(response.keys())}")
                
                # Check if there's a continuation token for the next page
                # The key might be different than what we expect
                continuation_token = None
                for key in response.keys():
                    if "continuation" in key.lower():
                        continuation_token = response[key]
                        print(f"Found continuation token with key: {key}")
                        break
                
                if continuation_token:
                    # Update search request with continuation token
                    print(f"Using continuation token: {continuation_token[:30]}..." if len(str(continuation_token)) > 30 else continuation_token)
                    search_request = {
                        "keywords": keywords,
                        "limit": limit,
                        "continuationToken": continuation_token
                    }
                    # Get next page
                    print(f"Retrieving next page with continuation token...")
                    response = self.datamap_client.discovery.query(body=search_request)
                else:
                    # No continuation token found
                    print("No continuation token found in response. Available keys:")
                    for key in response.keys():
                        print(f"  - {key}")
                    print("No more pages available")
                    break
            
            # Combine all dataframes
            if df_list:
                result_df = pd.concat(df_list, ignore_index=True)
                print(f"Successfully retrieved {len(result_df)} total records across {page_count} pages")
                print(result_df)
                return result_df
            else:
                print("No results found or unexpected response format")
                return pd.DataFrame()
            
        except HttpResponseError as e:
            print(f"Search error: {e}")
            return pd.DataFrame()
    
    def identify_classified_assets(self, result_df: pd.DataFrame) -> list[dict]:
        """Identify assets with valid classification data.
        
        This function filters the search results to find assets that have 
        non-empty classification values with a minimum length.
        
        Args:
            result_df: DataFrame containing search results from search_entities
            
        Returns:
            List of dictionaries with 'id', 'name', and 'classification' of classified assets
        """
        if result_df.empty:
            print("No data to process")
            return []
            
        # Check if 'classification' column exists
        if 'classification' not in result_df.columns:
            print("Classification column not found in the data")
            return []
            
        # Filter for non-null, non-empty classifications with length > 10
        filtered_df = result_df.copy()
        
        # Convert any non-string values to strings or empty strings
        # Handle all types safely to avoid errors
        def safe_str_conversion(x):
            try:
                # First check if it's None
                if x is None:
                    return ''
                
                # Check for NaN/NA values using pandas functions
                # This is safer than using isinstance with pd.NA
                if pd.isna(x) or (hasattr(x, 'isna') and x.isna().any()):
                    return ''
                
                # Handle arrays, lists, dicts, etc.
                if isinstance(x, (list, dict, tuple, set)):
                    return str(x)
                
                # Try to convert to string
                return str(x)
            except Exception as e:
                print(f"Warning: Error converting value to string: {str(e)}")
                return ''
                
        # Apply the conversion function with error handling
        try:
            filtered_df['classification'] = filtered_df['classification'].apply(safe_str_conversion)
        except Exception as e:
            print(f"Error processing classification column: {str(e)}")
            # Fallback: use a more direct approach
            filtered_df['classification'] = filtered_df['classification'].astype(str)
        
        # Apply the filter criteria
        filtered_df = filtered_df[filtered_df['classification'].str.len() > 10]
        
        # Get the count of filtered records
        filtered_count = len(filtered_df)
        total_count = len(result_df)
        
        print(f"Found {filtered_count} out of {total_count} assets with valid classification data")
        
        # Create array of dictionaries with id, name, and classification
        classified_assets_array = []
        
        # Check if required columns exist
        required_columns = ['id', 'name', 'classification']
        missing_columns = [col for col in required_columns if col not in filtered_df.columns]
        
        if missing_columns:
            print(f"Warning: Missing required columns: {missing_columns}")
            return []
        
        # Convert to list of dictionaries with id, name, and classification
        classified_assets_array = filtered_df[required_columns].to_dict(orient='records')
        print(f"\nCreated array with {len(classified_assets_array)} classified assets")
        
        # Display sample of the array
        if classified_assets_array:
            print("\nSample of classified assets array:")
            print(classified_assets_array[:5])
            
        return classified_assets_array


def main():
    """Main function to demonstrate Purview operations.
    
    Returns:
        List of dictionaries with 'id', 'name', and 'classification' of classified assets
    """
    
    # Initialize configuration
    purview_config = PurviewConfig()
    
    # Create client
    purview_client = PurviewClient(purview_config)
    
    # Search for all entities
    print("\n=== Searching for entities ===")
    search_results = purview_client.search_entities(keywords="*")
    
    # Identify assets with valid classification data
    print("\n=== Identifying assets with valid classification data ===")
    classified_assets_array = purview_client.identify_classified_assets(search_results)
    
    # Print all classified assets
    if classified_assets_array:
        print(f"\n=== Printing all {len(classified_assets_array)} classified assets ===")
        for i, asset in enumerate(classified_assets_array):
            print(f"{i+1}. ID: {asset['id']}")
            print(f"   Name: {asset['name']}")
            print(f"   Classification: {asset['classification']}")
            print("---")
    else:
        print("\nNo classified assets found")

if __name__ == "__main__":
    main()