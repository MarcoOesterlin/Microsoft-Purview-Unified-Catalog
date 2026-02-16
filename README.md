# Microsoft Purview Unified Catalog Tools & Scripts

A comprehensive collection of tools, scripts, and applications for managing and working with Microsoft Purview Unified Catalog. This repository provides solutions for data governance, asset management, schema extraction, automation tasks, and a modern web-based utility application.

## 📁 Repository Structure

### 🚀 [Microsoft_Purview_Utility](./Microsoft_Purview_Utility/)
**Modern Web Application for Purview Management**
- **Purpose**: Full-stack web application for comprehensive Purview data catalog management and curation
- **Tech Stack**: 
  - **Frontend**: React + TypeScript + Vite + TailwindCSS + shadcn/ui
  - **Backend**: Python Flask REST API
- **Features**:
  - Interactive dashboard with asset statistics and metrics
  - Browse and search assets by type, collection, and classification
  - Data products catalog with governance domain tracking
  - Advanced curation portal with bulk operations:
    - Add/delete tags with auto-suggestions
    - Add/delete classifications with ML-powered recommendations
    - Manage owners and experts with Entra ID integration
    - Add descriptions and metadata
    - Create and manage lineage relationships
  - Business glossary synchronization
  - Orphaned assets detection and cleanup
  - Real-time search with filtering and sorting
  - Modern, responsive UI
- **Use Case**: Primary interface for data governance teams, centralized asset management, and comprehensive data catalog operations

### 🔍 [Microsoft_Purview_Get_Asset_Schema](./Microsoft_Purview_Get_Asset_Schema/)
**Asset Schema Retrieval Tool**
- **Purpose**: Retrieve and extract schema information for specific assets from Microsoft Purview
- **Main Script**: `Get_Data_Asset_Schema.py`
- **Features**:
  - Extract detailed schema information from Purview assets
  - Support for various asset types (tables, views, etc.)
  - Service principal and default Azure credential authentication
  - Comprehensive error handling and logging
- **Use Case**: Data discovery, schema documentation, metadata extraction

### 📊 [Microsoft_Purview_Datamap_extractor_Public](./Microsoft_Purview_Datamap_extractor_Public/)
**Metadata Extraction & Export Tool**
- **Purpose**: Extract metadata from Microsoft Purview and export to Azure SQL Database or Microsoft Fabric Lakehouse
- **Main Scripts**:
  - `datamap_extract_azure_sql.py` - Export to Azure SQL Database
  - `datamap_extract_fabric_notebook.py` - Export to Microsoft Fabric Lakehouse
- **Features**:
  - Flexible export options (SQL Database or Fabric Lakehouse)
  - Pagination support for large datasets
  - Azure Key Vault integration for secure credential management
  - Comprehensive logging and error handling
- **Use Case**: Metadata analysis, reporting, and data warehousing

### 🌐 [Microsoft_Purview_Purview_DG_Curator_Portal](./Microsoft_Purview_Purview_DG_Curator_Portal/)
**Streamlit-Based Curation Portal**
- **Purpose**: Streamlit web application for managing and curating data assets
- **Main Application**: `app.py`
- **Features**:
  - Simple web interface for data asset management
  - Add/delete tags for assets
  - Assign data owners and experts
  - Search and filter functionality
  - Bulk operations support
  - Integration with Microsoft Graph API for user management
- **Use Case**: Lightweight data governance workflows, quick asset curation

### 📦 [Microsoft_Purview_Get_Data_Product](./Microsoft_Purview_Get_Data_Product/)
**Data Product Retrieval Tool**
- **Purpose**: Extract and analyze data products from Microsoft Purview Unified Catalog
- **Main Script**: `get_data_product.py`
- **Features**:
  - Retrieve data product information
  - Export data product metadata
  - Pagination and filtering support
- **Use Case**: Data product catalog management, governance reporting

### 🏷️ [Microsoft_Purview_Add_PII_Label](./Microsoft_Purview_Add_PII_Label/)
**PII Label Automation Tool**
- **Purpose**: Automate the process of adding PII (Personally Identifiable Information) labels to classified assets
- **Main Script**: `Add_PII_Label.py`
- **Features**:
  - Automatic identification of classified assets
  - Bulk PII labeling operations
  - Detailed logging and progress tracking
  - Support for large datasets with pagination
- **Use Case**: Data privacy compliance, automated data classification, governance automation

### 🗑️ [Microsoft_Purview_Delete_Assets_Collection](./Microsoft_Purview_Delete_Assets_Collection/)
**Asset Deletion Management Tool**
- **Purpose**: Bulk deletion of assets from specific Purview collections
- **Main Script**: `delete_assets.py`
- **Features**:
  - Targeted deletion from specific collections
  - Bulk operations with token renewal
  - Comprehensive logging and error handling
  - Safe collection-based filtering
- **Use Case**: Data cleanup, collection management, asset lifecycle management

### 👥 [Microsoft_Purview_Get_Inactive_Experts_Owners](./Microsoft_Purview_Get_Inactive_Experts_Owners/)
**Inactive Contact Detection Tool**
- **Purpose**: Identify assets with inactive owners or experts by comparing against Azure Entra ID
- **Main Script**: `get_inactive_owner_experts.py`
- **Features**:
  - Automated detection across all Purview collections
  - Integration with Microsoft Graph API
  - Comprehensive reporting of inactive contacts
  - Pagination support for large datasets
- **Use Case**: Data governance maintenance, contact cleanup, compliance auditing

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

