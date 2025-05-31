# Azure Purview Asset Schema Retriever

This script provides functionality to retrieve the schema information for a specific asset from Azure Purview using the Data Map API.

## Prerequisites

- Python 3.6 or higher
- Azure Purview account
- Required Python packages:
  - azure-purview-datamap
  - azure-identity
  - python-dotenv

## Installation

1. Install the required packages:
```bash
pip install azure-purview-datamap azure-identity python-dotenv
```

2. Create a `.env` file in the same directory with the following variables:
```env
AZURE_TENANT_ID=your_tenant_id
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret
PURVIEW_ACCOUNT_NAME=your_purview_account_name
PURVIEW_ENDPOINT=your_purview_endpoint  # Optional if PURVIEW_ACCOUNT_NAME is provided
```

## Usage

1. Open `Get_Data_Asset_Schema.py` and replace the `asset_id` variable in the `main()` function with your target asset's GUID:
```python
asset_id = "your-asset-guid-here"
```

2. Run the script:
```bash
python Get_Data_Asset_Schema.py
```

## Authentication

The script supports two authentication methods:
1. Service Principal Authentication (using Client Secret)
   - Requires AZURE_TENANT_ID, AZURE_CLIENT_ID, and AZURE_CLIENT_SECRET in the .env file
2. Default Azure Credential
   - Used as fallback if service principal credentials are not provided
   - Supports various authentication methods including managed identity and Azure CLI

## Function Details

### get_asset_schema(asset_id)

Retrieves the schema information for a specific asset from Azure Purview.

**Parameters:**
- `asset_id` (str): The GUID of the asset to retrieve schema for

**Returns:**
- Dictionary containing the asset's schema information if found
- None if the asset is not found or if an error occurs

The function searches for schema information in the following locations:
1. relationshipAttributes.columns
2. columns
3. attributes.columns

## Error Handling

The script includes error handling for HTTP response errors and will print error messages if the retrieval fails.

## Example Output

The script will output the schema information in JSON format if found:

```json
{
  "columns": [
    {
      "name": "column1",
      "type": "string",
      ...
    },
    ...
  ]
}
```

## Notes

- Make sure you have the necessary permissions in Azure Purview to access the asset information
- The script requires network connectivity to your Azure Purview instance
- For security best practices, never commit the .env file to version control
