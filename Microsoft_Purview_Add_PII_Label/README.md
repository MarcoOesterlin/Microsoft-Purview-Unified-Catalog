# Purview PII Label Automation Script

This script automates the process of adding PII (Personally Identifiable Information) labels to assets in Microsoft Purview that have already received automatic classification. It helps streamline the data governance process by ensuring consistent labeling of sensitive data assets.

## Features

- Automatically identifies assets with existing classification data
- Searches through all assets in your Purview catalog
- Filters for assets with valid classification information
- Provides detailed logging of the process
- Handles large datasets with pagination support

## Prerequisites

- Python 3.6 or higher
- Access to a Microsoft Purview account
- Required Python packages (install via `pip install -r requirements.txt`):
  - azure-purview-datamap
  - azure-identity
  - pandas
  - python-dotenv

## Environment Variables

Create a `.env` file in the script directory with the following variables:

```env
AZURE_TENANT_ID=your_tenant_id
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret
PURVIEW_ACCOUNT_NAME=your_purview_account_name
PURVIEW_ENDPOINT=your_purview_endpoint
```

## Usage

1. Set up your environment variables in the `.env` file
2. Run the script:
   ```
   python Add_PII_Label.py
   ```

## How It Works

1. The script first authenticates with your Purview account using the provided credentials
2. It searches for all entities in your Purview catalog
3. Identifies assets that have valid classification data (non-empty classification values)
4. Processes each identified asset to add the PII label
5. Provides detailed logging of the process, including:
   - Total number of assets found
   - Number of assets with valid classification
   - Progress updates during processing

## Output

The script provides detailed console output showing:
- Configuration status
- Search progress
- Number of assets found
- Number of assets with valid classification
- Processing status for each asset

## Error Handling

The script includes robust error handling for:
- Authentication failures
- API rate limits
- Invalid responses
- Missing or malformed data

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is licensed under the MIT License - see the LICENSE file for details.
