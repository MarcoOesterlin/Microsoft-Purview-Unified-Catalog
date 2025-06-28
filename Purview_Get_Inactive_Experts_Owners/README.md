# Microsoft Purview Unified Catalog Inactive Experts & Owners Detection

This Python script identifies assets in Microsoft Purview Unified Catalog that have inactive owners or experts by comparing contact information against the current list of active users in Azure Entra ID (formerly Azure AD).

## Overview

The script performs the following operations:

1. **Connects to Microsoft Purview Unified Catalog** using service principal authentication
2. **Retrieves all collections** from the Purview catalog
3. **Searches all entities** across all collections with pagination support
4. **Extracts contact information** (owners and experts) from each asset
5. **Fetches active users** from Azure Entra ID via Microsoft Graph API
6. **Compares contact IDs** with active user IDs to identify inactive users
7. **Generates a report** of assets with inactive owners or experts

## Prerequisites

- Python 3.8 or higher
- Microsoft Purview Unified Catalog account with appropriate permissions
- Azure Entra ID (Azure AD) tenant
- Service principal with permissions to:
  - Read Microsoft Purview Unified Catalog data
  - Read Azure Entra ID user information

## Installation

1. **Clone or download** this repository
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Create a `.env` file** in the project directory with the following variables:
   ```env
   TENANTID=your_tenant_id
   CLIENTID=your_service_principal_client_id
   CLIENTSECRET=your_service_principal_client_secret
   PURVIEWENDPOINT=https://your-purview-account.purview.azure.com
   PURVIEWSCANENDPOINT=https://your-purview-account.scan.purview.azure.com
   PURVIEWACCOUNTNAME=your-purview-account-name
   ```

## Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TENANTID` | Azure AD tenant ID | `12345678-1234-1234-1234-123456789012` |
| `CLIENTID` | Service principal client ID | `87654321-4321-4321-4321-210987654321` |
| `CLIENTSECRET` | Service principal client secret | `your-secret-value` |
| `PURVIEWENDPOINT` | Purview catalog endpoint | `https://myaccount.purview.azure.com` |
| `PURVIEWSCANENDPOINT` | Purview scan endpoint | `https://myaccount.scan.purview.azure.com` |
| `PURVIEWACCOUNTNAME` | Purview account name | `myaccount` |

### Required Permissions

The service principal needs the following permissions:

**Microsoft Purview Unified Catalog:**
- `PurviewDataReader` role or equivalent permissions to read catalog data

**Microsoft Graph:**
- `User.Read.All` permission to read user information

## Usage

Run the script from the command line:

```bash
python get_inactive_owner_experts.py
```

## Output

The script generates several outputs:

### 1. Search Results Summary
- Total number of unique entities found
- Progress information during search operations

### 2. Extracted Contacts DataFrame
A DataFrame containing:
- `name`: Asset name
- `id`: Asset ID
- `owner_ids`: Comma-separated list of owner IDs
- `expert_ids`: Comma-separated list of expert IDs

### 3. Active Users DataFrame
A DataFrame containing:
- `id`: User ID
- `displayName`: User display name

### 4. Inactive Assets Report
A DataFrame containing assets with inactive contacts:
- `name`: Asset name
- `id`: Asset ID
- `owner_ids`: All owner IDs (active and inactive)
- `expert_ids`: All expert IDs (active and inactive)

## Dependencies

- `azure-identity`: Azure authentication
- `azure-purview-datamap`: Purview data map operations
- `pandas`: Data manipulation and analysis
- `requests`: HTTP requests
- `python-dotenv`: Environment variable management
- `asyncio`: Asynchronous operations

## License

This project is licensed under the MIT License - see the LICENSE file for details.

