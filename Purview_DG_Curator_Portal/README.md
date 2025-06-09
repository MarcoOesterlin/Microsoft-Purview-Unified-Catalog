# Purview DG Curator Portal

A Streamlit-based web application for managing and curating data assets in Microsoft Purview. This portal provides a user-friendly interface for adding tags, managing data owners, and viewing asset information.

## Features

- View and search data assets from Microsoft Purview
- Add and delete tags for selected assets
- Assign data owners and experts to assets
- Search functionality across all columns
- Bulk operations support
- Modern and responsive UI

## Prerequisites

- Python 3.7 or higher
- Microsoft Purview account with appropriate permissions
- Azure AD application with access to Purview (for authentication)

## Required Environment Variables

Create a `.env` file in the project root with the following variables:

```env
TENANTID=your_tenant_id
CLIENTID=your_client_id
CLIENTSECRET=your_client_secret
PURVIEWENDPOINT=your_purview_endpoint
PURVIEWSCANENDPOINT=your_purview_scan_endpoint
PURVIEWACCOUNTNAME=your_purview_account_name
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/Microsoft-Purview-Unified-Catalog.git
cd Microsoft-Purview-Unified-Catalog/Purview_DG_Curator_Portal
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On Unix or MacOS
source venv/bin/activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
pip install streamlit pandas azure-identity azure-purview-datamap python-dotenv
```

## Running the Portal

1. Ensure your `.env` file is properly configured with the required environment variables.

2. Start the Streamlit application:
```bash
streamlit run app.py
```

3. The portal will open in your default web browser at `http://localhost:8501`

## Usage

### Data Assets Tab
- View all data assets in a table format
- Use the search bar to filter assets
- Select assets using checkboxes for bulk operations
- View asset details including ID, name, contact, tags, classification, and description

### Add Tags Tab
- Select assets from the Data Assets tab
- Enter new tags to add to selected assets
- View existing tags for selected assets

### Delete Tags Tab
- Select assets from the Data Assets tab
- Remove all tags from selected assets

### Add Data Owner / Expert Tab
- Select assets from the Data Assets tab
- Search and select users to assign as owners or experts
- Add comments for the assignment
- Choose between Owner or Expert role

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the GitHub repository or contact the maintainers. 