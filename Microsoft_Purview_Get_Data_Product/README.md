# Microsoft Purview Unified Catalog - List Data Products

This Python script retrieves and displays data products from Microsoft Purview Unified Catalog using the REST API.

## Prerequisites

- Python 3.7 or higher
- Microsoft Purview account with Unified Catalog enabled
- Azure AD App Registration (Service Principal) with appropriate permissions
- Access to Microsoft Purview portal

## Dependencies

The script requires the following Python packages:

```
requests>=2.31.0
python-dotenv>=1.0.0
azure-identity>=1.15.0
```

## Installation

1. **Clone or download this repository**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Grant Purview Permissions

**CRITICAL:** Your Service Principal must be added to the **Global Data Reader** role in Unified Catalog permissions.


### 3. Create Environment Variables

Create a `.env` file in the project directory with the following content:

```env
# Azure AD Tenant ID
TENANT_ID=your-tenant-id-here

# Azure AD Application (Client) ID
CLIENTID=your-client-id-here

# Azure AD Application Client Secret
CLIENTSECRET=your-client-secret-here

# For CLASSIC Purview governance portal:
# PURVIEW_ENDPOINT=https://your-account-name.purview.azure.com
```

## Usage

Run the script:

```bash
python get_data_product.py
```

### Output

The script will:
1. Authenticate using your Service Principal credentials
2. Retrieve all data products from Purview Unified Catalog
3. Display a summary of each data product
4. Print the full JSON response in a formatted view

## API Information

This script uses the Microsoft Purview Data Governance API:

- **API Version:** `2025-09-15-preview`
- **Endpoint:** `{endpoint}/datagovernance/catalog/dataProducts`
- **Authentication:** OAuth2 with Azure AD (Client Credentials flow)
- **Scope:** `https://purview.azure.net/.default`

## Troubleshooting

### 403 Forbidden Error

If you receive a 403 error:
- Ensure your Service Principal is added to **Global Data Reader** role in Purview
- Check that you're using the correct endpoint URL
- Confirm your Purview account has Data Products enabled

### Authentication Errors

- Verify your `TENANT_ID`, `CLIENTID`, and `CLIENTSECRET` are correct
- Ensure the Service Principal (App Registration) is active
- Check that the client secret hasn't expired

## API Reference

For more information about the Microsoft Purview Data Products API:
- [List Data Products API Documentation](https://learn.microsoft.com/en-us/rest/api/purview/purviewdatagovernance/list-data-products/list-data-products?view=rest-purview-purviewdatagovernance-2025-09-15-preview)
- [Microsoft Purview REST API](https://learn.microsoft.com/en-us/rest/api/purview/)

