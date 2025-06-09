# Microsoft Purview Unified Catalog Scripts

This repository contains a collection of scripts and tools for working with Microsoft Purview Unified Catalog. Each folder contains specific functionality and has its own detailed README file.

## Repository Structure

### Get_Asset_Schema
Contains scripts for retrieving and working with asset schemas in Microsoft Purview. This folder includes:
- `Get_Data_Asset_Schema.py`: A Python script for extracting asset schema information

### Purview_Datamap_extractor_Public
Contains scripts for extracting datamaps from various Microsoft data sources. This folder includes:
- `datamap_extract_azure_sql.py`: Script for extracting datamaps from Azure SQL databases
- `datamap_extract_fabric_notebook.py`: Script for extracting datamaps from Fabric notebooks

### Purview_DG_Curator_Portal
A Streamlit-based web application for managing and curating data assets in Microsoft Purview. Features include:
- Viewing and searching data assets
- Adding and deleting tags
- Assigning data owners
- Bulk operations support
- Modern and user-friendly interface

### Purview_Add_PII_Label
A script that automates the process of adding PII (Personally Identifiable Information) labels to assets in Microsoft Purview that have already received automatic classification. Features include:
- Automatic identification of classified assets
- Bulk PII labeling
- Detailed logging and progress tracking
- Support for large datasets

## Getting Started
Each folder contains its own README.md file with specific instructions for:
- Prerequisites
- Installation steps
- Usage examples
- Configuration details

Please refer to the README.md in each folder for detailed information about the specific tools and scripts.


## Contributing
Feel free to submit issues and enhancement requests for any of the tools in this repository.

## License
This project is licensed under the MIT License - see the LICENSE file for details.

