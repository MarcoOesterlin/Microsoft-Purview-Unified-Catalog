# Purview_Delete_Assets_Collection

## delete_Assets.py

### Overview

`delete_Assets.py` is a Python script designed to automate the deletion of assets from an specific collection in a Purview account. It authenticates with Azure using service principal credentials, retrieves all collections and their assets, and deletes assets from a specified collection by their GUIDs. The script is useful for bulk asset management and cleanup in Microsoft Purview Unified Catalog environments.

### Features

- Authenticates with Microsoft Purview using service principal credentials.
- Lists all collections in the Purview account.
- Searches and retrieves all assets within each collection.
- **Deletes assets from a user-specified collection.**
- Deletes assets in bulk by their GUIDs, renewing the access token every 5000 deletions.
- Provides detailed logging and error handling for each operation.

### Selecting Your Collection

Before running the script, you must specify the collection from which you want to delete assets. 

- **How to set your collection:**
  - In the script, locate the line that filters the DataFrame by collection ID:
    ```python
    filtered_jdf = jdf[jdf['collectionId'] == 'snhrnw']
    ```
  - Replace `'ADD COLLECTION HERE'` with the ID of your specific collection, for example:
    ```python
    collection_id = 'your_collection_id_here'
    filtered_jdf = jdf[jdf['collectionId'] == collection_id]
    ```
  - You can set `collection_id` as a variable at the top of the script for easier configuration.

### Prerequisites

- Python 3.7+
- Microsoft Purview account and service principal with appropriate permissions.
- The following Python packages:
  - `azure-identity`
  - `azure-purview-datamap`
  - `pandas`
  - `requests`
  - `python-dotenv`

Install dependencies with:

```bash
pip install azure-identity azure-purview-datamap pandas requests python-dotenv
```

### Environment Variables

Create a `.env` file in the same directory as the script with the following variables:

```
TENANTID=<your-azure-tenant-id>
CLIENTID=<your-service-principal-client-id>
CLIENTSECRET=<your-service-principal-client-secret>
PURVIEWENDPOINT=https://<your-purview-account-name>.purview.azure.com
PURVIEWSCANENDPOINT=https://<your-purview-account-name>.scan.purview.azure.com
PURVIEWACCOUNTNAME=<your-purview-account-name>
```

### Usage

1. **Configure Environment**: Ensure your `.env` file is set up as described above.
2. **Set Your Collection**: Edit the script to set your specific collection ID as described above.
3. **Run the Script**:

   ```
   python delete_Assets.py
   ```

4. **Monitor Output**: The script will print logs for each step, including successful and failed deletions.

### Important Notes

- **Destructive Operation**: This script will permanently delete assets from your Purview account. Use with caution.
- **Permissions**: The service principal must have sufficient permissions to list, search, and delete assets in Purview.
- **Token Renewal**: The script automatically renews the access token every 5000 deletions to avoid authentication issues.

### Customization

- To change which assets are deleted, modify the collection ID filter or add additional filtering logic in the script.
- You can adapt the script to export asset information before deletion if needed.

### License

This project is licensed under the MIT License.
