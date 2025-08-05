# Microsoft Purview Unified Catalog Tools & Scripts

A comprehensive collection of tools, scripts, and applications for managing and working with Microsoft Purview Unified Catalog. This repository provides solutions for data governance, asset management, schema extraction, and automation tasks.

## 📁 Repository Structure

### 🔍 [Purview_Get_Asset_Schema](./Purview_Get_Asset_Schema/)
**Asset Schema Retrieval Tool**
- **Purpose**: Retrieve and extract schema information for specific assets from Azure Purview
- **Main Script**: `Get_Data_Asset_Schema.py`
- **Features**:
  - Extract detailed schema information from Purview assets
  - Support for various asset types (tables, views, etc.)
  - Service principal and default Azure credential authentication
  - Comprehensive error handling and logging
- **Use Case**: Data discovery, schema documentation

### 📊 [Purview_Datamap_extractor_Public](./Purview_Datamap_extractor_Public/)
**Metadata Extraction & Export Tool**
- **Purpose**: Extract metadata from Azure Purview and export to Azure SQL Database or Microsoft Fabric Lakehouse
- **Main Scripts**:
  - `datamap_extract_azure_sql.py` - Export to Azure SQL Database
  - `datamap_extract_fabric_notebook.py` - Export to Microsoft Fabric Lakehouse
- **Features**:
  - Flexible export options (SQL Database or Fabric Lakehouse)
  - Pagination support for large datasets
  - Azure Key Vault integration for secure credential management
  - Comprehensive logging and error handling
- **Use Case**: metadata analysis

### 🌐 [Purview_DG_Curator_Portal](./Purview_DG_Curator_Portal/)
**Web-Based Curation Portal**
- **Purpose**: Streamlit-based web application for managing and curating data assets
- **Main Application**: `app.py`
- **Features**:
  - Modern web interface for data asset management
  - Add/delete tags for assets
  - Assign data owners and experts
  - Search and filter functionality
  - Bulk operations support
  - Integration with Microsoft Graph API for user management
- **Use Case**: Data governance workflows, asset curation.

### 🏷️ [Purview_Add_PII_Label](./Purview_Add_PII_Label/)
**PII Label Automation Tool**
- **Purpose**: Automate the process of adding PII (Personally Identifiable Information) labels to classified assets
- **Main Script**: `Add_PII_Label.py`
- **Features**:
  - Automatic identification of classified assets
  - Bulk PII labeling operations
  - Detailed logging and progress tracking
  - Support for large datasets with pagination
- **Use Case**: Data privacy compliance, automated data classification, and governance automation

### 🗑️ [Purview_Delete_Assets_Collection](./Purview_Delete_Assets_Collection/)
**Asset Deletion Management Tool**
- **Purpose**: Bulk deletion of assets from specific Purview collections
- **Main Script**: `delete_assets.py`
- **Features**:
  - Targeted deletion from specific collections
  - Bulk operations with token renewal
  - Comprehensive logging and error handling
  - Safe collection-based filtering
- **Use Case**: Data cleanup, collection management, and asset lifecycle management

### 👥 [Purview_Get_Inactive_Experts_Owners](./Purview_Get_Inactive_Experts_Owners/)
**Inactive Contact Detection Tool**
- **Purpose**: Identify assets with inactive owners or experts by comparing against Azure Entra ID
- **Main Script**: `get_inactive_owner_experts.py`
- **Features**:
  - Automated detection across all Purview collections
  - Integration with Microsoft Graph API
  - Comprehensive reporting of inactive contacts
  - Pagination support for large datasets
- **Use Case**: Data governance maintenance, contact cleanup, and compliance auditing

## 📚 Documentation

Each project contains detailed documentation:
- **Individual README files** with specific setup and usage instructions
- **Code comments** for customization guidance
- **Example configurations** and use cases

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

## 🔗 Related Resources

- [Microsoft Purview Documentation](https://docs.microsoft.com/en-us/azure/purview/)
- [Azure Purview REST API Reference](https://docs.microsoft.com/en-us/rest/api/purview/)
- [Microsoft Graph API Documentation](https://docs.microsoft.com/en-us/graph/)
- [Azure Identity Python SDK](https://docs.microsoft.com/en-us/python/api/overview/azure/identity-readme/)

---

**Note**: Always test tools in a non-production environment first and ensure you have appropriate backups before performing destructive operations.

