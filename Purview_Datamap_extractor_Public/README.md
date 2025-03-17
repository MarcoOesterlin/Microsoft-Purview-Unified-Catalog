# Purview Datamap Extractor

A Python-based tool for extracting metadata from Azure Purview and exporting it to either Azure SQL Database or Microsoft Fabric Lakehouse.

## 🌟 Features

- Azure Purview catalog search with pagination support
- Flexible export options:
  - Export to Azure SQL Database
  - Export to Microsoft Fabric Notebook/Lakehouse as JSON files
- Secure credential management:
  - Environment variables for Azure SQL export
  - Azure Key Vault integration for Fabric Notebook export
- Robust error handling and connection testing
- Detailed logging throughout the extraction process

## 📋 Prerequisites

### Software Requirements
- Python 3.6+
- ODBC Driver 17 for SQL Server (for Azure SQL export only)

### Azure Resources
- Azure Purview account
- Service Principal with appropriate permissions
- One of the following:
  - Azure SQL Database
  - Microsoft Fabric Workspace with Lakehouse

### Python Dependencies
```
# For both export methods
pip install azure-purview-catalog azure-identity azure-core pandas

# For Azure SQL export
pip install pyodbc sqlalchemy python-dotenv urllib3

# For Fabric Notebook export
# Note: notebookutils is provided by the Fabric Notebook environment
```

## 🚀 Installation

1. Clone the repository
```
git clone https://github.com/YourUsername/Purview_Datamap_extractor_Public.git
cd Purview_Datamap_extractor_Public
```

2. Install the required dependencies based on your export method

## ⚙️ Configuration

### Azure SQL Database Export

Create a `.env` file with the following variables:

```
# Azure Purview Configuration
TENANT_ID=your-tenant-id
CLIENT_ID=your-client-id
CLIENT_SECRET=your-client-secret
PURVIEW_ENDPOINT=your-purview-endpoint
PURVIEW_SCAN_ENDPOINT=your-scan-endpoint

# Azure SQL Database Configuration
DB_SERVER=your-server.database.windows.net
DB_NAME=your-database
DB_USERNAME=your-username
DB_PASSWORD=your-password
DB_TABLE_NAME=your-table
```

### Microsoft Fabric Notebook Export

Store the following secrets in your Azure Key Vault:

```
TENANTID=your-tenant-id
CLIENTID=your-client-id
CLIENTSECRET=your-client-secret
PURVIEWENDPOINT=your-purview-endpoint
PURVIEWSCANENDPOINT=your-scan-endpoint
```

Update the `KEYVAULT_URL` in the script with your Key Vault URL.

## 💻 Usage

### Azure SQL Database Export

Run the script:
```
python datamap_extract_azure_sql.py
```

This will:
1. Connect to Azure Purview using the provided credentials
2. Search for all entities in the catalog
3. Test the database connection with retries
4. Export the results to the specified Azure SQL Database table

### Microsoft Fabric Notebook Export

1. Upload the `datamap_extract_fabric_notebook.py` to your Fabric Notebook
2. Run the notebook

This will:
1. Connect to Azure Purview using credentials from Key Vault
2. Search for all entities in the catalog
3. Export the results as JSON files to your Lakehouse with a date-based folder structure

## 🔧 Code Structure

### Common Components

#### PurviewConfig
- Manages Azure Purview authentication
- Stores endpoints and credentials
- Handles secure configuration (env vars or Key Vault)

#### PurviewSearchClient
- Performs Purview catalog searches
- Handles authentication
- Manages paginated results
- Processes search data

### Azure SQL Export Components

#### DatabaseConfig
- Manages database connection settings
- Stores SQL Database credentials
- Configures target table information

#### DataExporter
- Manages database connections
- Handles data export operations
- Provides error handling and connection testing

### Fabric Notebook Components

- Uses notebookutils for Key Vault integration
- Implements date-based folder structure for data organization
- Exports data as JSON files with UUID-based filenames

## 🔄 Version History

- 1.0.0
  - Initial Release
  - Support for both Azure SQL and Fabric Notebook export methods
