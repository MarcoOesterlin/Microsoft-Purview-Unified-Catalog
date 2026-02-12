from azure.purview.datamap import DataMapClient
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.core.exceptions import HttpResponseError
import pandas as pd
from datetime import datetime
import pyodbc
from sqlalchemy import create_engine, String, DateTime, Float, BigInteger, Boolean, NVARCHAR, Numeric
import urllib
import os
from dotenv import load_dotenv
import time



load_dotenv()

class PurviewConfig:
    """Configuration class for Azure Purview authentication and endpoints.
    
    Stores the necessary credentials and endpoints for connecting to Azure Purview,
    including tenant ID, client ID, client secret, and Purview endpoints.
    """
    def __init__(self):
        self.tenant_id = os.getenv("TENANT_ID")
        self.client_id = os.getenv("CLIENT_ID")
        self.client_secret = os.getenv("CLIENT_SECRET")
        self.purview_account_name = os.getenv("PURVIEW_ACCOUNT_NAME")

class DatabaseConfig:
    """Configuration class for Azure SQL Database connection settings."""
    def __init__(self):
        self.server = os.getenv("DB_SERVER")
        self.database = os.getenv("DB_NAME")
        self.username = os.getenv("DB_USERNAME")
        self.password = os.getenv("DB_PASSWORD")
        self.driver = 'ODBC Driver 17 for SQL Server'
        self.table_name = os.getenv("DB_TABLE_NAME")


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
        """Initialize the Purview DataMapClient with the updated SDK.
        
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
                    df = pd.DataFrame(response["value"])
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
                return final_df
            else:
                print("No results found or unexpected response format")
                return pd.DataFrame()

        except HttpResponseError as e:
            print(f"Search error: {e}")
            return None

class DataExporter:
    """Handles data export operations to Azure SQL Database.
    
    Manages the connection and data export operations to Azure SQL Database using SQLAlchemy.
    
    Args:
        db_config (DatabaseConfig): Configuration object containing database connection details.
    """
    def __init__(self, db_config: DatabaseConfig):
        self.db_config = db_config
        self.engine = self._create_engine()

   
    def _create_engine(self):
        """Create SQLAlchemy engine for database operations.
        
        Returns:
            Engine: SQLAlchemy engine instance for database connections.
        """
        connection_string = (
            f"mssql+pyodbc://{self.db_config.username}:{urllib.parse.quote_plus(self.db_config.password)}"
            f"@{self.db_config.server}:1433/{self.db_config.database}"
            f"?driver={self.db_config.driver.replace(' ', '+')}"
        )
        return create_engine(connection_string)


    def ping_database(self, max_retries=3, retry_delay=30):
        """Test database connection with retry mechanism.
        
        Args:
            max_retries (int): Maximum number of connection attempts
            retry_delay (int): Delay in seconds between retries
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        for attempt in range(max_retries):
            try:
                conn_str = (
                    f'DRIVER={{{self.db_config.driver}}};'
                    f'SERVER={self.db_config.server};'
                    f'DATABASE={self.db_config.database};'
                    f'UID={self.db_config.username};'
                    f'PWD={self.db_config.password}'
                )
                conn = pyodbc.connect(conn_str)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                conn.close()
                print("Database connection test successful")
                return True
                
            except Exception as e:
                print(f"Database connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:  # Don't sleep after last attempt
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                
        print(f"Database connection failed after {max_retries} attempts")
        return False


    def export_to_sql(self, df, table_name=None):
        """Export DataFrame to Azure SQL Database.
        
        Args:
            df (pandas.DataFrame): DataFrame to export.
            table_name (str, optional): Target table name. Defaults to configured table name.
        """
        if table_name is None:
            table_name = self.db_config.table_name
            
        try:
            df.to_sql(
                table_name,
                con=self.engine,
                if_exists='append',
                index=False
            )
            print(f"DataFrame successfully appended to the '{table_name}' table in Azure SQL Database.")
        except Exception as e:
            print(f"Export error: {e}")


def main():
    """Main execution function for the data extraction and export process.
    
    Orchestrates the entire workflow:
    1. Initializes Purview and database configurations
    2. Creates necessary client instances
    3. Performs Purview catalog search
    4. Processes search results into a DataFrame
    5. Exports processed data to Azure SQL Database
    """
    # Initialize configurations
    purview_config = PurviewConfig()
    db_config = DatabaseConfig()
    
    # Create clients
    purview_client = PurviewSearchClient(purview_config)
    data_exporter = DataExporter(db_config)
    
    # Perform search using search_entities method
    search_results = purview_client.search_entities()
    
    if search_results is not None and not search_results.empty:
        # Process results
        search_results['date'] = datetime.now().date()
        
        # Convert all dictionary/object columns to strings
        for column in search_results.columns:
            if search_results[column].dtype == 'object':
                search_results[column] = search_results[column].apply(lambda x: str(x) if isinstance(x, (dict, list)) else x)

        # Try to connect to database with retries
        if data_exporter.ping_database(max_retries=3, retry_delay=30):
            print("Waiting 120 seconds before export...")
            #time.sleep(120)  # Wait 120 seconds
            # Export to SQL
            data_exporter.export_to_sql(search_results)
        else:
            print("Export aborted due to persistent database connection issues")

if __name__ == "__main__":
    main()