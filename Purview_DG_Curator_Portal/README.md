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
- Python 3.8+
- Access to Microsoft Purview Unified Catalog
- Service Principal with Microsoft Purview & Graph API permissions (see below)

## Setup & Usage

1. **Install Python 3.8+**
   - Make sure Python is installed and available in your PATH.

2. **Set up your environment variables:**
   - Create a `.env` file in this directory with your Azure credentials and Purview/Graph API details (see below for required variables).

3. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

4. **Run the Streamlit app:**
   ```
   streamlit run app.py
   ```

**Note:**
- You do NOT need to create or activate a virtual environment; simply install the requirements and run the app as above.
- Ensure your `.env` file is properly configured for both Purview and Microsoft Graph API access.

## Microsoft Graph API Requirements
To fetch Entra ID (Azure AD) user data, you must have a service principal with access to the Microsoft Graph API and the `User.Read.All` permission. You can use your existing Purview service principal for this purpose, as long as it has the required Graph API permissions.

**How to set up:**
1. Register an Azure AD application (service principal) in the Azure portal (or use your existing Purview service principal).
2. Grant the application the `User.Read.All` permission for Microsoft Graph API (Application permissions).
3. Grant admin consent for the permission.
4. Use the client ID, tenant ID, and client secret of this service principal in your environment variables or `.env` file as required by the app.

## Purview API Requirements
To access and manage assets in Microsoft Purview via this portal, you must use a service principal (Azure AD application) with the appropriate permissions assigned in your Purview account's Data Map.

**How to set up:**
1. Register an Azure AD application (service principal) in the Azure portal (or use your existing one).
2. Assign the service principal to your Purview account with one of the following roles:
   - **Data Curator** (recommended for full curation capabilities)
   - **Data Source Admin** (if you need to manage sources)
3. Grant the service principal access in the Purview Data Map 'Collections' permissions.
4. Use the client ID, tenant ID, and client secret of this service principal in your environment variables or `.env` file as required by the app.

> **Note:** The same service principal can be used for both Purview API and Microsoft Graph API access, as long as it has the required permissions for both.

## Setup & Usage
1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Navigate to the folder containing app.py:
   ```
   cd Purview_DG_Curator_Portal
   ```
3. Start the Streamlit app:
   ```
   streamlit run app.py
   ```

**Note:**
- There is no need to create or activate a virtual environment; simply install the requirements and run the app as above.
- Ensure your environment variables or `.env` file are configured for Purview and Graph API access.

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