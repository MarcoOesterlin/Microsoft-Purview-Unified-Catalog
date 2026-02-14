from azure.identity import ClientSecretCredential 
from azure.core.exceptions import HttpResponseError
from azure.purview.datamap import DataMapClient
import requests
import os
import dotenv
import asyncio
import aiohttp
import json

# Load environment variables
dotenv.load_dotenv()

tenant_id = os.getenv("TENANTID")
client_id = os.getenv("CLIENTID")
client_secret = os.getenv("CLIENTSECRET")
purview_endpoint = os.getenv("PURVIEWENDPOINT")
purview_account_name = os.getenv("PURVIEWACCOUNTNAME")

# Azure AI Foundry configuration for lineage agent
use_fabric_agent = os.getenv("USE_FABRIC_AGENT", "false").lower() == "true"
azure_foundry_endpoint = os.getenv("AZURE_EXISTING_AIPROJECT_ENDPOINT", "")
azure_foundry_agent_name = os.getenv("AZURE_DATALINEAGE_EXISTING_AGENT_ID", "datalineage-agent")
azure_foundry_env_name = os.getenv("AZURE_DATALINEAGE_ENV_NAME", "")

def get_access_token(tenant_id, client_id, client_secret):
    """Get access token for Purview API using OAuth2 token endpoint (same method as get_data.py)"""
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/token"
    body = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials',
        'resource': 'https://purview.azure.net'
    }
    
    response = requests.post(token_url, data=body)
    
    if response.status_code == 200:
        return response.json().get('access_token')
    else:
        print(f" Error getting access token: {response.status_code}")
        print(f"   Response: {response.text}")
        raise Exception(f"Failed to get access token: {response.text}")

def get_credentials():
    """Get credentials for DataMapClient"""
    return ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret
    )

def parse_fabric_qualified_name(qualified_name):
    """
    Parse Fabric qualified name to extract workspace ID, lakehouse ID, and resource name.
    
    Example paths:
    - https://app.fabric.microsoft.com/groups/{workspace_id}/lakehouses/{lakehouse_id}/tables/{table}
    - https://onelake.dfs.fabric.microsoft.com/{workspace_id}/{lakehouse_id}/Tables/{table}
    
    Returns: (workspace_id, lakehouse_id, resource_name, resource_type)
    """
    try:
        parts = qualified_name.split('/')
        workspace_id = None
        lakehouse_id = None
        resource_name = None
        resource_type = None
        
        # Find workspace ID (first GUID in path)
        for i, part in enumerate(parts):
            if len(part) == 36 and part.count('-') == 4:  # GUID format
                if workspace_id is None:
                    workspace_id = part
                elif lakehouse_id is None:
                    lakehouse_id = part
                    break
        
        # Determine resource type and name
        if 'tables/' in qualified_name.lower():
            resource_type = 'table'
            idx = qualified_name.lower().rfind('tables/')
            resource_name = qualified_name[idx+7:].strip('/')
        elif 'lakehouses/' in qualified_name.lower():
            resource_type = 'lakehouse'
            idx = qualified_name.lower().rfind('lakehouses/')
            resource_name = qualified_name[idx+11:].split('/')[0]
        elif 'notebooks/' in qualified_name.lower():
            resource_type = 'notebook'
            idx = qualified_name.lower().rfind('notebooks/')
            resource_name = qualified_name[idx+10:].strip('/')
        elif 'pipelines/' in qualified_name.lower():
            resource_type = 'pipeline'
            idx = qualified_name.lower().rfind('pipelines/')
            resource_name = qualified_name[idx+10:].strip('/')
        
        return workspace_id, lakehouse_id, resource_name, resource_type
        
    except Exception as e:
        print(f"Error parsing Fabric qualified name: {e}")
        return None, None, None, None

def get_workspace_info_from_purview(guid):
    """
    Get workspace information from Purview entity.
    
    Args:
        guid: Asset GUID
    
    Returns:
        dict: Workspace info including workspace_id, workspace_name, etc.
    """
    try:
        credential = get_credentials()
        client = DataMapClient(endpoint=purview_endpoint, credential=credential)
        
        # Get entity details
        response = client.entity.get_by_ids(guid=[guid])
        
        if not response or 'entities' not in response or not response['entities']:
            return None
        
        entity = response['entities'][0]
        qualified_name = entity.get('attributes', {}).get('qualifiedName', '')
        
        # Parse workspace info from qualified name
        workspace_id, lakehouse_id, resource_name, resource_type = parse_fabric_qualified_name(qualified_name)
        
        # Try to get workspace name from entity attributes
        workspace_name = entity.get('attributes', {}).get('workspaceName', '') or \
                        entity.get('attributes', {}).get('workspace', '')
        
        return {
            'workspace_id': workspace_id,
            'workspace_name': workspace_name,
            'lakehouse_id': lakehouse_id,
            'resource_name': resource_name,
            'resource_type': resource_type,
            'qualified_name': qualified_name,
            'asset_guid': guid,
            'asset_name': entity.get('attributes', {}).get('name', '')
        }
        
    except Exception as e:
        print(f"Error getting workspace info: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_workspace_assets_from_purview(workspace_id):
    """
    Get all assets (lakehouses, tables, columns, notebooks) for a workspace from Purview.
    
    Args:
        workspace_id: Workspace GUID
    
    Returns:
        dict: All workspace assets with details
    """
    try:
        credential = get_credentials()
        client = DataMapClient(endpoint=purview_endpoint, credential=credential)
        
        print(f"\n Fetching all assets for workspace: {workspace_id}")
        
        # Get all entities from get_data (already loaded in memory)
        import get_data
        df = get_data.main()
        
        if df is None or df.empty:
            print(" No data available from Purview")
            return None
        
        assets = {
            'lakehouses': [],
            'tables': [],
            'files': [],  # Add files for raw data sources
            'notebooks': [],
            'dataflows': [],
            'pipelines': [],
            'warehouses': [],
            'other_assets': [],
            'workspace_id': workspace_id
        }
        
        # Filter assets that belong to this workspace
        # Any qualified name containing groups/{workspace_id}/ is part of the workspace
        workspace_pattern = f"groups/{workspace_id}/"
        
        for _, row in df.iterrows():
            qualified_name = row.get('qualifiedName', '')
            
            # Check if this asset belongs to the workspace
            if workspace_pattern not in qualified_name:
                continue
            
            # Use objectType field and qualifiedName patterns for categorization
            object_type = str(row.get('objectType', '')).strip().lower()
            asset_name = row.get('name', '')
            asset_guid = row.get('id', '')  # Use 'id' field from get_data.py, not 'guid'
            
            # Skip folders, columns, and metadata entities (but keep files!)
            if object_type in ['folders']:
                continue
            if any(skip in qualified_name.lower() for skip in ['/columns/', '/fields/', '/meta/']):
                continue
            
            asset_info = {
                'name': asset_name,
                'guid': asset_guid,
                'qualified_name': qualified_name,
                'type': object_type
            }
            
            # Categorize assets by qualifiedName patterns and objectType
            # Priority order matters: check specific patterns first
            if 'table' in object_type or 'dataset' in object_type:
                # Get columns for this table
                try:
                    entity_response = client.entity.get_by_ids(guid=[asset_guid])
                    if entity_response.get('entities'):
                        entity = entity_response['entities'][0]
                        columns = []
                        
                        # Get column information
                        relationship_attrs = entity.get('relationshipAttributes', {})
                        schema_columns = relationship_attrs.get('columns', []) or relationship_attrs.get('schema', [])
                        
                        print(f"   DEBUG: Table {asset_name} - found {len(schema_columns)} columns in relationshipAttributes")
                        
                        if schema_columns:
                            for col in schema_columns:
                                col_name = col.get('displayText', col.get('name', 'unknown'))
                                columns.append({
                                    'name': col_name,
                                    'guid': col.get('guid', ''),
                                    'type': col.get('typeName', '')
                                })
                                print(f"      Column: {col_name} (type: {col.get('typeName', 'N/A')})")
                        
                        asset_info['columns'] = columns
                        print(f"   [OK] Table {asset_name}: {len(columns)} columns added to asset_info")
                except Exception as e:
                    print(f"   Warning: Could not fetch columns for {asset_name}: {e}")
                    asset_info['columns'] = []
                
                assets['tables'].append(asset_info)
            elif 'file' in object_type or qualified_name.endswith(('.csv', '.parquet', '.json', '.txt', '.avro')):
                # Files (raw data sources in Landing zone)
                assets['files'].append(asset_info)
            elif '/synapsenotebooks/' in qualified_name or 'notebook' in object_type:
                assets['notebooks'].append(asset_info)
            elif '/lakewarehouses/' in qualified_name or 'warehouse' in object_type:
                assets['warehouses'].append(asset_info)
            elif '/dataflows/' in qualified_name or 'dataflow' in object_type:
                assets['dataflows'].append(asset_info)
            elif '/datapipelines/' in qualified_name or 'pipeline' in object_type:
                assets['pipelines'].append(asset_info)
            elif '/lakehouses/' in qualified_name and '/tables/' not in qualified_name:
                # Only lakehouses themselves, not tables within lakehouses
                assets['lakehouses'].append(asset_info)
            else:
                # Capture any other asset types we might have missed
                assets['other_assets'].append(asset_info)
        
        print(f" Workspace assets summary:")
        print(f"   - {len(assets['lakehouses'])} lakehouses")
        print(f"   - {len(assets['warehouses'])} warehouses")
        print(f"   - {len(assets['tables'])} tables/datasets")
        print(f"   - {len(assets['files'])} files")
        print(f"   - {len(assets['dataflows'])} dataflows")
        print(f"   - {len(assets['pipelines'])} pipelines")
        print(f"   - {len(assets['notebooks'])} notebooks")
        print(f"   - {len(assets['other_assets'])} other assets")
        
        return assets
        
    except Exception as e:
        print(f" Error fetching workspace assets: {e}")
        import traceback
        traceback.print_exc()
        return None

def analyze_lineage_with_fabric_agent(workspace_info):
    """
    Send workspace information to Azure AI Foundry Agent to discover and create lineage.
    Similar pattern to auto_classify's analyze_with_fabric_agent.
    
    Args:
        workspace_info: Dict containing:
            - workspace_id: Fabric workspace GUID
            - workspace_name: Workspace display name
            - asset_guid: Source asset GUID (optional)
            - qualified_name: Asset qualified name (optional)
    
    Returns:
        dict: Discovered lineage relationships
    """
    try:
        from openai import OpenAI
        from azure.identity import ClientSecretCredential, get_bearer_token_provider
        
        if not azure_foundry_endpoint or not use_fabric_agent:
            return None
        
        # Build the full responses endpoint URL
        base_url = f"{azure_foundry_endpoint}/applications/{azure_foundry_agent_name}/protocols/openai/responses?api-version=2025-11-15-preview"
        
        # Use service principal credentials for bearer token
        if tenant_id and client_id and client_secret:
            credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret
            )
            token_provider = get_bearer_token_provider(credential, "https://ai.azure.com/.default")
        else:
            from azure.identity import DefaultAzureCredential
            credential = DefaultAzureCredential()
            token_provider = get_bearer_token_provider(credential, "https://ai.azure.com/.default")
        
        # Create OpenAI client with Foundry endpoint
        openai_client = OpenAI(
            api_key=token_provider,
            base_url=base_url,
            default_query={"api-version": "2025-11-15-preview"}
        )
        
        # Build the prompt for lineage discovery
        prompt_content = f"""You are a Data Lineage Discovery Agent for Microsoft Fabric workspaces in Azure Purview.

WORKSPACE INFORMATION:
- Workspace ID: {workspace_info.get('workspace_id', 'N/A')}
- Workspace Name: {workspace_info.get('workspace_name', 'N/A')}

"""
        
        # Add workspace assets if available
        if any(workspace_info.get(key) for key in ['lakehouses', 'warehouses', 'tables', 'dataflows', 'pipelines', 'notebooks', 'other_assets']):
            prompt_content += """
=== COMPLETE WORKSPACE ASSET INVENTORY ===

Below are ALL assets in this workspace including lakehouses, warehouses, tables with columns, dataflows, pipelines, and notebooks.
Analyze these assets to discover data lineage relationships and column-level mappings.

"""
            
            # Add Lakehouses
            if workspace_info.get('lakehouses'):
                prompt_content += f"\n LAKEHOUSES ({len(workspace_info['lakehouses'])}):\n"
                for lakehouse in workspace_info['lakehouses']:
                    prompt_content += f"  • {lakehouse['name']}\n"
                    prompt_content += f"    GUID: {lakehouse['guid']}\n"
                    prompt_content += f"    Qualified Name: {lakehouse['qualified_name']}\n"
                    prompt_content += f"    Type: {lakehouse.get('type', 'lakehouse')}\n\n"
            
            # Add Warehouses
            if workspace_info.get('warehouses'):
                prompt_content += f"\n WAREHOUSES ({len(workspace_info['warehouses'])}):\n"
                for warehouse in workspace_info['warehouses']:
                    prompt_content += f"  • {warehouse['name']}\n"
                    prompt_content += f"    GUID: {warehouse['guid']}\n"
                    prompt_content += f"    Qualified Name: {warehouse['qualified_name']}\n"
                    prompt_content += f"    Type: {warehouse.get('type', 'warehouse')}\n\n"
            
            # Add Tables with Columns
            if workspace_info.get('tables'):
                prompt_content += f"\n TABLES WITH COLUMNS ({len(workspace_info['tables'])}):\n"
                for table in workspace_info['tables']:
                    prompt_content += f"  • {table['name']}\n"
                    prompt_content += f"    GUID: {table['guid']}\n"
                    prompt_content += f"    Qualified Name: {table['qualified_name']}\n"
                    prompt_content += f"    Type: {table.get('type', 'table')}\n"
                    if table.get('columns'):
                        prompt_content += f"     Columns ({len(table['columns'])}):\n"
                        for col in table['columns']:
                            col_type = col.get('type', 'unknown')
                            prompt_content += f"       - {col['name']} : {col_type}\n"
                    else:
                        prompt_content += f"     Columns: (no column information available)\n"
                    prompt_content += "\n"
            
            # Add Files (raw data sources)
            if workspace_info.get('files'):
                prompt_content += f"\n FILES (Raw Data Sources) ({len(workspace_info['files'])}):\n"
                for file in workspace_info['files']:
                    prompt_content += f"  • {file['name']}\n"
                    prompt_content += f"    GUID: {file['guid']}\n"
                    prompt_content += f"    Qualified Name: {file['qualified_name']}\n"
                    prompt_content += f"    Type: {file.get('type', 'file')}\n\n"
            
            # Add Dataflows
            if workspace_info.get('dataflows'):
                prompt_content += f"\n DATAFLOWS ({len(workspace_info['dataflows'])}):\n"
                for dataflow in workspace_info['dataflows']:
                    prompt_content += f"  • {dataflow['name']}\n"
                    prompt_content += f"    GUID: {dataflow['guid']}\n"
                    prompt_content += f"    Qualified Name: {dataflow['qualified_name']}\n"
                    prompt_content += f"    Type: {dataflow.get('type', 'dataflow')}\n\n"
            
            # Add Pipelines
            if workspace_info.get('pipelines'):
                prompt_content += f"\n PIPELINES ({len(workspace_info['pipelines'])}):\n"
                for pipeline in workspace_info['pipelines']:
                    prompt_content += f"  • {pipeline['name']}\n"
                    prompt_content += f"    GUID: {pipeline['guid']}\n"
                    prompt_content += f"    Qualified Name: {pipeline['qualified_name']}\n"
                    prompt_content += f"    Type: {pipeline.get('type', 'pipeline')}\n\n"
            
            # Add Notebooks
            if workspace_info.get('notebooks'):
                prompt_content += f"\n NOTEBOOKS ({len(workspace_info['notebooks'])}):\n"
                for notebook in workspace_info['notebooks']:
                    prompt_content += f"  • {notebook['name']}\n"
                    prompt_content += f"    GUID: {notebook['guid']}\n"
                    prompt_content += f"    Qualified Name: {notebook['qualified_name']}\n"
                    prompt_content += f"    Type: {notebook.get('type', 'notebook')}\n\n"
            
            # Add Other Assets
            if workspace_info.get('other_assets'):
                prompt_content += f"\n OTHER ASSETS ({len(workspace_info['other_assets'])}):\n"
                for asset in workspace_info['other_assets']:
                    prompt_content += f"  • {asset['name']}\n"
                    prompt_content += f"    GUID: {asset['guid']}\n"
                    prompt_content += f"    Qualified Name: {asset['qualified_name']}\n"
                    prompt_content += f"    Type: {asset.get('type', 'unknown')}\n\n"
            
            prompt_content += "\n" + "="*60 + "\n\n"
        
        # Print summary of assets being sent
        print("\n" + "="*80)
        print(" ASSET SUMMARY BEING SENT TO AGENT:")
        print("="*80)
        if workspace_info.get('lakehouses'):
            print(f"\n LAKEHOUSES ({len(workspace_info['lakehouses'])}):")
            for lh in workspace_info['lakehouses']:
                print(f"   • {lh['name']}")
        
        if workspace_info.get('warehouses'):
            print(f"\n WAREHOUSES ({len(workspace_info['warehouses'])}):")
            for wh in workspace_info['warehouses']:
                print(f"   • {wh['name']}")
        
        if workspace_info.get('tables'):
            print(f"\n TABLES ({len(workspace_info['tables'])}):")
            for table in workspace_info['tables']:
                col_count = len(table.get('columns', []))
                print(f"   • {table['name']} ({col_count} columns)")
        
        if workspace_info.get('files'):
            print(f"\n FILES (Landing Zone) ({len(workspace_info['files'])}):")
            for file in workspace_info['files']:
                print(f"   • {file['name']} [GUID: {file['guid']}]")
        
        if workspace_info.get('dataflows'):
            print(f"\n DATAFLOWS ({len(workspace_info['dataflows'])}):")
            for df in workspace_info['dataflows']:
                print(f"   • {df['name']}")
        
        if workspace_info.get('pipelines'):
            print(f"\n PIPELINES ({len(workspace_info['pipelines'])}):")
            for pl in workspace_info['pipelines']:
                print(f"   • {pl['name']}")
        
        if workspace_info.get('notebooks'):
            print(f"\n NOTEBOOKS ({len(workspace_info['notebooks'])}):")
            for nb in workspace_info['notebooks']:
                print(f"   • {nb['name']}")
        
        if workspace_info.get('other_assets'):
            print(f"\n OTHER ASSETS ({len(workspace_info['other_assets'])}):")
            for asset in workspace_info['other_assets']:
                print(f"   • {asset['name']} ({asset.get('type', 'unknown')})")
        
        print("="*80 + "\n")
        
        prompt_content += """YOUR TASK:
Analyze the workspace assets and discover data lineage relationships between tables.

Look at the table names, columns, and qualified names to identify data flows. 
Consider that tables with similar names and columns likely have lineage relationships.

For each data flow you discover:

1. **Table-to-Table Lineage**: Identify which tables feed data into other tables
   - Both source_table_name and target_table_name MUST be exact matches from the TABLES list above
   - Copy the GUID and qualified_name exactly as shown
   - Match tables based on similar names and column schemas

2. **Column-Level Mappings**: Map ALL source columns to target columns
   - Include ALL columns from the source table in column_mappings
   - If a source column has an obvious match in the target (exact name or semantic match), include the target_column name
   - If a source column has NO obvious match, set target_column to empty string ""
   - This allows users to see all available source columns and manually map unmapped ones

RESPONSE FORMAT (JSON only, no markdown):
{{
  "lineage_mappings": [
    {{
      "source_table_name": "EXACT name from TABLES or FILES list (use source_file_name for files)",
      "source_table_guid": "GUID from the table/file entry above",
      "source_table_qualified_name": "qualified_name from the table/file entry above",
      "target_table_name": "EXACT name from TABLES list above",
      "target_table_guid": "GUID from the table entry above",
      "target_table_qualified_name": "qualified_name from the table entry above",
      "column_mappings": [
        {{"source_column": "exact_column_name", "target_column": "exact_column_name"}},
        {{"source_column": "unmapped_source_column", "target_column": ""}}
      ]
    }}
  ]
}}

NOTE: 
- Include ALL source columns in column_mappings array
- Set target_column to "" (empty string) for source columns without an obvious target match
- This allows users to see all available columns and manually map the unmapped ones
- For file-to-table lineage: Use FILE name as source_table_name (e.g., "Transactions.csv")
- Create DIRECT lineage from file/table to table (no process intermediary)

If no lineage can be discovered using ONLY the exact asset names listed above, return:
{{
  "lineage_mappings": []
}}

Respond with ONLY the JSON object. Do not make up asset names."""
        
        # Print payload being sent to Foundry
        print("\n" + "="*80)
        print(" PAYLOAD SENT TO FOUNDRY AGENT:")
        print("="*80)
        print(f"Endpoint: {base_url}")
        print(f"Agent: {azure_foundry_agent_name}")
        print(f"\nPAYLOAD:")
        print(prompt_content)
        print("="*80 + "\n")
        
        # Call the responses API
        response = openai_client.responses.create(
            input=prompt_content
        )
        
        # Read the response
        ai_response = response.output_text
        print("\n" + "="*80)
        print(" RESPONSE FROM FOUNDRY AGENT:")
        print("="*80)
        print(ai_response)
        print("="*80 + "\n")
        
        # Parse JSON response
        try:
            # Extract JSON from markdown code blocks if present
            response_text = ai_response
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            
            # Fix common JSON errors from AI (trailing commas)
            import re
            # Remove trailing commas before closing brackets/braces
            response_text = re.sub(r',\s*([\]}])', r'\1', response_text)
            
            print(f" PARSED JSON:\n{response_text}\n")
            
            lineage_data = json.loads(response_text)
            
            # Check if we have the new format with lineage_mappings
            if 'lineage_mappings' in lineage_data:
                num_mappings = len(lineage_data.get('lineage_mappings', []))
                print(f" Agent returned {num_mappings} lineage mapping(s)\n")
                
                # If no mappings found, explain why to the user
                if num_mappings == 0:
                    print("  WARNING: No lineage relationships were discovered by the AI agent.")
                    print("   This could mean:")
                    print("   - The workspace doesn't have clear source -> target relationships")
                    print("   - Assets don't follow typical ETL patterns (files/tables -> tables)")
                    print("   - The AI couldn't identify semantic connections between assets")
                    print("   - You may need to manually create lineage relationships\n")
                    return {
                        'lineage_mappings': [],
                        'upstream_assets': [],
                        'downstream_assets': [],
                        'processes': [],
                        'column_mappings': [],
                        'message': 'No lineage relationships discovered. You may need to create them manually.'
                    }
                
                # Validate that asset names exist in workspace by re-checking against get_data.py
                print(" VALIDATING ASSET NAMES AGAINST PURVIEW DATA (get_data.py)...")
                
                # Re-fetch data from get_data.py to ensure accuracy
                import get_data
                df = get_data.main()
                
                if df is None or df.empty:
                    print(" ERROR: Could not fetch data from get_data.py for validation")
                    return None
                
                workspace_id = workspace_info.get('workspace_id')
                workspace_pattern = f"groups/{workspace_id}/"
                
                # Build lookup of actual asset names from Purview (exact case-insensitive match)
                purview_asset_names = {}  # lowercase_name -> original_name mapping
                
                for _, row in df.iterrows():
                    qualified_name = row.get('qualifiedName', '')
                    if workspace_pattern in qualified_name:
                        asset_name = row.get('name', '')
                        if asset_name:
                            purview_asset_names[asset_name.lower()] = asset_name
                
                print(f"   Found {len(purview_asset_names)} assets in Purview for this workspace:")
                for original_name in sorted(set(purview_asset_names.values())):
                    print(f"      - {original_name}")
                print()
                
                # Validate each mapping against Purview data
                valid_mappings = []
                invalid_mappings = []
                
                for mapping in lineage_data.get('lineage_mappings', []):
                    source_name = mapping.get('source_table_name', '')
                    target_name = mapping.get('target_table_name', '')
                    
                    source_name_lower = source_name.lower()
                    target_name_lower = target_name.lower()
                    
                    source_valid = source_name_lower in purview_asset_names
                    target_valid = target_name_lower in purview_asset_names
                    
                    if source_valid and target_valid:
                        # Replace with actual Purview names (correct casing)
                        mapping['source_table_name'] = purview_asset_names[source_name_lower]
                        mapping['target_table_name'] = purview_asset_names[target_name_lower]
                        valid_mappings.append(mapping)
                        print(f"    VALID: {mapping['source_table_name']} → {mapping['target_table_name']}")
                    else:
                        invalid_mappings.append(mapping)
                        reasons = []
                        if not source_valid:
                            reasons.append(f"source '{source_name}' not found in Purview")
                        if not target_valid:
                            reasons.append(f"target '{target_name}' not found in Purview")
                        print(f"    INVALID: {source_name} → {target_name}")
                        print(f"      Reason: {', '.join(reasons)}")
                
                print(f"\n VALIDATION RESULTS:")
                print(f"    Valid mappings: {len(valid_mappings)}")
                print(f"    Invalid mappings: {len(invalid_mappings)}")
                
                if len(valid_mappings) == 0:
                    print(f"\n ERROR: No valid lineage mappings found!")
                    print(f"   Agent returned asset names that don't exist in Purview.")
                    print(f"\n   Available assets in workspace '{workspace_info.get('workspace_name', workspace_id)}':")
                    for original_name in sorted(set(purview_asset_names.values())):
                        print(f"      • {original_name}")
                    print()
                    return None
                
                print(f" Successfully validated {len(valid_mappings)} lineage mapping(s)\n")
                
                # REMOVE DUPLICATES
                print(" REMOVING DUPLICATE MAPPINGS...")
                seen_mappings = set()
                deduplicated_mappings = []
                
                for mapping in valid_mappings:
                    # Create unique key from source and target GUIDs
                    mapping_key = (mapping.get('source_table_guid'), mapping.get('target_table_guid'))
                    
                    if mapping_key not in seen_mappings:
                        seen_mappings.add(mapping_key)
                        deduplicated_mappings.append(mapping)
                        print(f"    Kept: {mapping['source_table_name']} → {mapping['target_table_name']}")
                    else:
                        print(f"    Removed duplicate: {mapping['source_table_name']} → {mapping['target_table_name']}")
                
                removed_count = len(valid_mappings) - len(deduplicated_mappings)
                if removed_count > 0:
                    print(f" Removed {removed_count} duplicate mapping(s)")
                else:
                    print(f" No duplicates found")
                
                valid_mappings = deduplicated_mappings
                print(f" Final count: {len(valid_mappings)} unique mapping(s)\n")
                
                # ENRICH MAPPINGS WITH COLUMN SCHEMAS
                print(" ENRICHING LINEAGE MAPPINGS WITH COLUMN SCHEMAS...")
                
                # Build lookup of table name -> columns from workspace_info
                table_columns_lookup = {}  # table_name -> [column objects]
                for table in workspace_info.get('tables', []):
                    table_name = table.get('name', '').lower()
                    columns = table.get('columns', [])
                    table_columns_lookup[table_name] = columns
                    if columns:
                        print(f"   • {table.get('name')}: {len(columns)} columns")
                
                # Enrich each mapping with column information
                for mapping in valid_mappings:
                    source_name = mapping.get('source_table_name', '').lower()
                    target_name = mapping.get('target_table_name', '').lower()
                    
                    # Add source columns from workspace_info
                    source_columns = table_columns_lookup.get(source_name, [])
                    target_columns = table_columns_lookup.get(target_name, [])
                    
                    mapping['source_columns'] = source_columns
                    mapping['target_columns'] = target_columns
                    
                    print(f"    {mapping['source_table_name']}: {len(source_columns)} source columns")
                    print(f"    {mapping['target_table_name']}: {len(target_columns)} target columns")
                    
                    # BUILD COMPLETE COLUMN MAPPINGS (SOURCE COLUMNS ONLY)
                    # Include ALL source columns in the mappings list
                    # Frontend will show source_columns and target_columns arrays separately
                    
                    # Start with AI-provided mappings
                    ai_mappings = mapping.get('column_mappings', [])
                    
                    # Track which source columns are already mapped
                    mapped_sources = {cm.get('source_column', '').lower() for cm in ai_mappings if cm.get('source_column')}
                    
                    # Create lookup of target column names for auto-matching
                    target_lookup = {col.get('name', '').lower(): col.get('name', '') for col in target_columns}
                    
                    complete_mappings = []
                    
                    # 1. Add all AI-provided mappings first
                    for cm in ai_mappings:
                        if cm.get('source_column'):
                            complete_mappings.append(cm)
                    
                    # 2. Add unmapped SOURCE columns (try to auto-map by name, or leave target empty)
                    mapped_targets = {cm.get('target_column', '').lower() for cm in complete_mappings if cm.get('target_column')}
                    
                    for source_col in source_columns:
                        col_name = source_col.get('name', '')
                        if col_name.lower() not in mapped_sources:
                            # Try to find matching target column by name
                            matched_target = target_lookup.get(col_name.lower(), '')
                            
                            if matched_target and matched_target.lower() not in mapped_targets:
                                # Auto-map to matching target column
                                complete_mappings.append({
                                    'source_column': col_name,
                                    'target_column': matched_target
                                })
                                mapped_targets.add(matched_target.lower())
                                print(f"      Auto-mapped: {col_name} → {matched_target}")
                            else:
                                # No match - add unmapped source column
                                complete_mappings.append({
                                    'source_column': col_name,
                                    'target_column': ''
                                })
                                print(f"      Unmapped source: {col_name}")
                    
                    # 3. Add unmapped TARGET columns (for frontend display)
                    for target_col in target_columns:
                        col_name = target_col.get('name', '')
                        if col_name.lower() not in mapped_targets:
                            # Add unmapped target column with empty source
                            complete_mappings.append({
                                'source_column': '',
                                'target_column': col_name
                            })
                            print(f"      Unmapped target: → {col_name}")
                    
                    mapping['column_mappings'] = complete_mappings
                    
                    mapped_count = sum(1 for cm in complete_mappings if cm.get('source_column') and cm.get('target_column'))
                    unmapped_count = len(complete_mappings) - mapped_count
                    
                    print(f"    [OK] Column mappings: {len(complete_mappings)} source columns ({mapped_count} mapped, {unmapped_count} unmapped)")
                
                print(f"\n Enriched {len(valid_mappings)} mappings with complete column schemas\n")
                
                # Return enriched mappings
                return {
                    'lineage_mappings': valid_mappings,
                    'upstream_assets': [],
                    'downstream_assets': [],
                    'processes': [],
                    'column_mappings': []
                }
            else:
                # Old format - validate upstream_assets, downstream_assets, and processes
                print(f" Agent returned old format: {len(lineage_data.get('upstream_assets', []))} upstream, {len(lineage_data.get('downstream_assets', []))} downstream, {len(lineage_data.get('processes', []))} processes\n")
                
                # Validate against Purview data
                print(" VALIDATING ASSET NAMES AGAINST PURVIEW DATA (get_data.py)...")
                
                # Re-fetch data from get_data.py to ensure accuracy
                import get_data
                df = get_data.main()
                
                if df is None or df.empty:
                    print(" ERROR: Could not fetch data from get_data.py for validation")
                    return None
                
                workspace_id = workspace_info.get('workspace_id')
                workspace_pattern = f"groups/{workspace_id}/"
                
                # Build lookup of actual asset names from Purview (exact case-insensitive match)
                purview_asset_names = {}  # lowercase_name -> original_name mapping
                
                for _, row in df.iterrows():
                    qualified_name = row.get('qualifiedName', '')
                    if workspace_pattern in qualified_name:
                        asset_name = row.get('name', '')
                        if asset_name:
                            purview_asset_names[asset_name.lower()] = asset_name
                
                print(f"   Found {len(purview_asset_names)} assets in Purview for this workspace:")
                for original_name in sorted(set(purview_asset_names.values())):
                    print(f"      - {original_name}")
                print()
                
                # Validate each asset in the response
                valid_upstream = []
                valid_downstream = []
                valid_processes = []
                invalid_assets = []
                
                # Validate upstream assets
                for asset in lineage_data.get('upstream_assets', []):
                    asset_name = asset.get('name', '')
                    if asset_name.lower() in purview_asset_names:
                        asset['name'] = purview_asset_names[asset_name.lower()]  # Correct casing
                        valid_upstream.append(asset)
                        print(f"    VALID upstream: {asset['name']}")
                    else:
                        invalid_assets.append(f"upstream '{asset_name}'")
                        print(f"    INVALID upstream: {asset_name} (not found in Purview)")
                
                # Validate downstream assets
                for asset in lineage_data.get('downstream_assets', []):
                    asset_name = asset.get('name', '')
                    if asset_name.lower() in purview_asset_names:
                        asset['name'] = purview_asset_names[asset_name.lower()]  # Correct casing
                        valid_downstream.append(asset)
                        print(f"    VALID downstream: {asset['name']}")
                    else:
                        invalid_assets.append(f"downstream '{asset_name}'")
                        print(f"    INVALID downstream: {asset_name} (not found in Purview)")
                
                # Validate processes
                for process in lineage_data.get('processes', []):
                    process_name = process.get('name', '')
                    if process_name.lower() in purview_asset_names:
                        process['name'] = purview_asset_names[process_name.lower()]  # Correct casing
                        valid_processes.append(process)
                        print(f"    VALID process: {process['name']}")
                    else:
                        invalid_assets.append(f"process '{process_name}'")
                        print(f"    INVALID process: {process_name} (not found in Purview)")
                
                print(f"\n VALIDATION RESULTS:")
                print(f"    Valid upstream: {len(valid_upstream)}")
                print(f"    Valid downstream: {len(valid_downstream)}")
                print(f"    Valid processes: {len(valid_processes)}")
                print(f"    Invalid assets: {len(invalid_assets)}")
                
                if len(valid_upstream) == 0 and len(valid_downstream) == 0 and len(valid_processes) == 0:
                    print(f"\n ERROR: No valid lineage assets found!")
                    print(f"   Agent returned asset names that don't exist in Purview.")
                    print(f"\n   Available assets in workspace '{workspace_info.get('workspace_name', workspace_id)}':")
                    for original_name in sorted(set(purview_asset_names.values())):
                        print(f"      • {original_name}")
                    print()
                    return None
                
                print(f" Successfully validated {len(valid_upstream) + len(valid_downstream) + len(valid_processes)} asset(s)\n")
                
                # Return only valid assets
                return {
                    'upstream_assets': valid_upstream,
                    'downstream_assets': valid_downstream,
                    'processes': valid_processes,
                    'column_mappings': lineage_data.get('column_mappings', [])
                }
            
        except json.JSONDecodeError as e:
            print(f" JSON Parse Error: {e}")
            print(f"Raw response text: {response_text}\n")
            return None
        
    except Exception as e:
        print(f" FOUNDRY ERROR (LINEAGE): {e}")
        import traceback
        traceback.print_exc()
        return None

def create_process_entity(source_qualified_name, target_qualified_name, process_name, column_mappings=None, source_guid=None, target_guid=None):
    """
    Create a Process entity in Purview to link source and target assets.
    Based on Microsoft documentation: https://learn.microsoft.com/en-us/purview/data-gov-api-create-lineage-relationships
    
    Args:
        source_qualified_name: Qualified name of source asset
        target_qualified_name: Qualified name of target asset
        process_name: Name for the process
        column_mappings: Optional list of column mappings [{"Source":"col1","Sink":"col1"}]
        source_guid: GUID of source asset (preferred to prevent duplicate creation)
        target_guid: GUID of target asset (preferred to prevent duplicate creation)
    
    Returns:
        dict: Created process entity with GUID
    """
    try:
        access_token = get_access_token(tenant_id, client_id, client_secret)
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Create process qualified name
        process_qualified_name = f"fabric_lineage_process://{process_name.replace(' ', '_')}_{source_qualified_name.split('/')[-1]}_to_{target_qualified_name.split('/')[-1]}"
        
        # Use GUID references if available to prevent duplicate entity creation
        # When using uniqueAttributes, Purview may create new entities if qualified names don't match exactly
        if source_guid:
            source_ref = {"typeName": "DataSet", "guid": source_guid}
        else:
            source_ref = {"typeName": "DataSet", "uniqueAttributes": {"qualifiedName": source_qualified_name}}
        
        if target_guid:
            target_ref = {"typeName": "DataSet", "guid": target_guid}
        else:
            target_ref = {"typeName": "DataSet", "uniqueAttributes": {"qualifiedName": target_qualified_name}}
        
        # Build process entity payload
        process_entity = {
            "entities": [
                {
                    "typeName": "Process",
                    "attributes": {
                        "qualifiedName": process_qualified_name,
                        "name": process_name,
                        "inputs": [source_ref],
                        "outputs": [target_ref]
                    },
                    "guid": "-1"
                }
            ]
        }
        
        # Add column mapping if provided
        if column_mappings:
            mapping_json = json.dumps([{
                "DatasetMapping": {
                    "Source": source_qualified_name,
                    "Sink": target_qualified_name
                },
                "ColumnMapping": column_mappings
            }])
            process_entity["entities"][0]["attributes"]["columnMapping"] = mapping_json
        
        # Create process entity
        url = f"{purview_endpoint}/datamap/api/atlas/v2/entity/bulk"
        print(f"\n Creating process entity: {process_name}")
        print(f"   URL: {url}")
        print(f"   Payload: {json.dumps(process_entity, indent=2)}")
        
        response = requests.post(url, json=process_entity, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        process_guid = result.get('guidAssignments', {}).get('-1')
        
        print(f" Process entity created with GUID: {process_guid}")
        
        return {
            'success': True,
            'process_guid': process_guid,
            'process_qualified_name': process_qualified_name
        }
        
    except Exception as e:
        print(f" Error creating process entity: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }

def get_table_columns(table_guid):
    """
    Get all columns for a table entity from Purview.
    
    Args:
        table_guid: GUID of the table entity
    
    Returns:
        list: List of column entities with guid and qualifiedName
    """
    try:
        access_token = get_access_token(tenant_id, client_id, client_secret)
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Get table entity with relationships
        url = f"{purview_endpoint}/datamap/api/atlas/v2/entity/guid/{table_guid}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        entity = response.json().get('entity', {})
        
        print(f"    DEBUG: Table {table_guid}")
        print(f"    DEBUG: typeName = {entity.get('typeName')}")
        print(f"    DEBUG: displayText = {entity.get('displayText')}")
        
        # Extract column references from relationshipAttributes
        columns = []
        rel_attrs = entity.get('relationshipAttributes', {})
        
        print(f"    DEBUG: relationshipAttributes keys = {list(rel_attrs.keys())}")
        
        # Check for 'columns' or 'schema' relationships
        column_refs = rel_attrs.get('columns', []) or rel_attrs.get('schema', [])
        
        print(f"    DEBUG: column_refs type = {type(column_refs)}, length = {len(column_refs) if isinstance(column_refs, list) else 'N/A'}")
        
        if isinstance(column_refs, list) and len(column_refs) > 0:
            print(f"    DEBUG: First column_ref keys = {list(column_refs[0].keys()) if isinstance(column_refs[0], dict) else 'not a dict'}")
        
        for col_ref in column_refs:
            if isinstance(col_ref, dict):
                col_guid = col_ref.get('guid')
                # Column name can be in displayText or need to extract from qualified name
                col_name = col_ref.get('displayText')
                # Note: uniqueAttributes is not present in column references, only guid and displayText
                col_qname = col_ref.get('uniqueAttributes', {}).get('qualifiedName') if 'uniqueAttributes' in col_ref else None
                
                if col_guid and col_name:
                    columns.append({
                        'guid': col_guid,
                        'qualifiedName': col_qname or f"column:{col_guid}",  # Fallback if qname not available
                        'name': col_name
                    })
        
        print(f"    Found {len(columns)} columns for table {table_guid}")
        if len(columns) > 0:
            print(f"    DEBUG: Sample column names: {[c['name'] for c in columns[:5]]}")
        import sys
        sys.stdout.flush()
        return columns
        
    except Exception as e:
        print(f" Error getting table columns: {e}")
        import traceback
        traceback.print_exc()
        return []

def create_dummy_column(table_guid, column_name="Unmapped", side="Target"):
    """
    Create a dummy column entity in Purview for unmapped columns.
    This allows lineage to be created for all columns, even those without mappings.
    
    Args:
        table_guid: GUID of the parent table
        column_name: Name for the dummy column (default: "Unmapped")
        side: "Source" or "Target" for display purposes
    
    Returns:
        dict: Column info with guid, qualifiedName, name, or None if failed
    """
    try:
        access_token = get_access_token(tenant_id, client_id, client_secret)
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Get parent table info
        url = f"{purview_endpoint}/datamap/api/atlas/v2/entity/guid/{table_guid}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        table_entity = response.json().get('entity', {})
        table_qname = table_entity['attributes']['qualifiedName']
        table_name = table_entity['attributes']['name']
        
        # Create column qualified name
        column_qname = f"{table_qname}#{column_name}_{side}"
        
        # Create column entity
        column_entity = {
            "entity": {
                "typeName": "Column",
                "attributes": {
                    "name": f"{column_name} ({side})",
                    "qualifiedName": column_qname,
                    "type": "string"
                },
                "relationshipAttributes": {
                    "table": {
                        "guid": table_guid,
                        "typeName": table_entity.get('typeName', 'DataSet')
                    }
                }
            }
        }
        
        # Create the column entity
        create_url = f"{purview_endpoint}/datamap/api/atlas/v2/entity"
        response = requests.post(create_url, json=column_entity, headers=headers)
        
        if response.status_code in [200, 201]:
            result = response.json()
            created_entities = result.get('guidAssignments', {})
            
            # Extract the created column GUID
            column_guid = None
            if created_entities and '-1' in created_entities:
                column_guid = created_entities['-1']
            elif result.get('entity'):
                column_guid = result['entity'].get('guid')
            
            if column_guid:
                print(f"    [OK] Created dummy column '{column_name} ({side})' in table {table_name}: {column_guid}")
                return {
                    'guid': column_guid,
                    'qualifiedName': column_qname,
                    'name': f"{column_name} ({side})"
                }
        
        print(f"    [ERROR] Failed to create dummy column: {response.status_code}")
        print(f"      Response: {response.text[:200]}")
        return None
        
    except Exception as e:
        print(f"    [ERROR] Error creating dummy column: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_column_lineage(source_table_guid, target_table_guid, column_mappings):
    """
    Create column-level lineage between two tables.
    This creates direct column-to-column relationships bypassing the process.
    
    Args:
        source_table_guid: GUID of source table
        target_table_guid: GUID of target table
        column_mappings: List of column mappings [{"Source":"col1","Sink":"col1"}]
    
    Returns:
        dict: Result with created column lineage count
    """
    try:
        if not column_mappings:
            print("  No column mappings provided for column lineage")
            return {'success': True, 'column_lineage_count': 0}
        
        # Get columns from both tables
        print(f"\n Creating column-level lineage...")
        print(f"   Source table: {source_table_guid}")
        print(f"   Target table: {target_table_guid}")
        import sys
        sys.stdout.flush()
        
        source_columns = get_table_columns(source_table_guid)
        print(f"    Retrieved {len(source_columns)} source columns")
        sys.stdout.flush()
        
        target_columns = get_table_columns(target_table_guid)
        print(f"    Retrieved {len(target_columns)} target columns")
        sys.stdout.flush()
        
        if not source_columns or not target_columns:
            print(f"  Could not retrieve columns from tables (source: {len(source_columns) if source_columns else 0}, target: {len(target_columns) if target_columns else 0})")
            sys.stdout.flush()
            return {'success': False, 'error': 'Could not retrieve table columns'}
        
        # Create lookup dictionaries by column name
        source_col_map = {col['name'].lower(): col for col in source_columns}
        target_col_map = {col['name'].lower(): col for col in target_columns}
        
        print(f"   Source columns available: {list(source_col_map.keys())}")
        import sys
        sys.stdout.flush()
        print(f"   Target columns available: {list(target_col_map.keys())}")
        sys.stdout.flush()
        print(f"   Column mappings to create: {column_mappings}")
        sys.stdout.flush()
        
        access_token = get_access_token(tenant_id, client_id, client_secret)
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        created_count = 0
        skipped_count = 0
        
        # Get or create dummy "unmapped" column entities for each table
        dummy_source_col = None
        dummy_target_col = None
        
        # Create column lineage for each mapping
        for mapping in column_mappings:
            source_col_name = mapping.get('Source', '').lower()
            target_col_name = mapping.get('Sink', '').lower()
            
            # Skip if BOTH are empty
            if not source_col_name and not target_col_name:
                print(f"   ⏭  Skipping completely empty mapping")
                sys.stdout.flush()
                skipped_count += 1
                continue
            
            print(f"\n    Processing mapping: '{source_col_name}' -> '{target_col_name}'")
            sys.stdout.flush()
            
            # Get or create source column
            # If source is empty/unmapped, use a dummy "Unmapped" column entity
            if not source_col_name:
                print(f"     Source not mapped - creating dummy source column")
                sys.stdout.flush()
                
                # Create or reuse dummy source column
                if not dummy_source_col:
                    dummy_source_col = create_dummy_column(source_table_guid, "Unmapped", "Source")
                    if not dummy_source_col:
                        print(f"     Failed to create dummy source column")
                        sys.stdout.flush()
                        skipped_count += 1
                        continue
                
                source_col = dummy_source_col
            else:
                source_col = source_col_map.get(source_col_name)
                if not source_col:
                    print(f"     Source column not found: '{source_col_name}'")
                    sys.stdout.flush()
                    skipped_count += 1
                    continue
            
            # Get or create target column
            # If target is empty/unmapped, use a dummy "Unmapped" column entity
            if not target_col_name:
                print(f"     Target not mapped - creating dummy target column")
                sys.stdout.flush()
                
                # Create or reuse dummy target column
                if not dummy_target_col:
                    dummy_target_col = create_dummy_column(target_table_guid, "Unmapped", "Target")
                    if not dummy_target_col:
                        print(f"     Failed to create dummy target column")
                        sys.stdout.flush()
                        skipped_count += 1
                        continue
                
                target_col = dummy_target_col
            else:
                target_col = target_col_map.get(target_col_name)
                if not target_col:
                    print(f"     Target column not found: '{target_col_name}'")
                    sys.stdout.flush()
                    skipped_count += 1
                    continue
            
            # Create column lineage relationship
            # For Fabric/Purview, the relationship type is "column_lineage" not "process_column_lineage"
            relationship = {
                "typeName": "column_lineage",
                "guid": "-1",
                "attributes": {},
                "end1": {
                    "typeName": "Column",
                    "guid": source_col['guid']
                },
                "end2": {
                    "typeName": "Column",
                    "guid": target_col['guid']
                }
            }
            
            url = f"{purview_endpoint}/datamap/api/atlas/v2/relationship"
            
            try:
                response = requests.post(url, json=relationship, headers=headers)
                
                if response.status_code == 200:
                    created_count += 1
                    print(f"    Created column lineage: {source_col['name']} -> {target_col['name']}")
                    sys.stdout.flush()
                elif response.status_code == 409:
                    print(f"   [INFO] Column lineage already exists: {source_col['name']} -> {target_col['name']}")
                    sys.stdout.flush()
                    created_count += 1  # Count as success since it exists
                else:
                    print(f"    Failed to create column lineage: {response.status_code}")
                    print(f"      {response.text[:200]}")
                    sys.stdout.flush()
                    skipped_count += 1
                    
            except Exception as e:
                print(f"    Error creating column lineage: {e}")
                sys.stdout.flush()
                skipped_count += 1
        
        # After processing all mappings, create lineage for any unmapped TARGET columns
        print(f"\n    Checking for unmapped target columns...")
        sys.stdout.flush()
        
        # Track which target columns were mapped
        mapped_target_names = set()
        for mapping in column_mappings:
            target_col_name = mapping.get('Sink', '').lower()
            if target_col_name:
                mapped_target_names.add(target_col_name)
        
        # Create lineage for unmapped target columns
        for target_col in target_columns:
            target_col_name = target_col['name'].lower()
            if target_col_name not in mapped_target_names:
                print(f"\n    Processing unmapped target column: '{target_col['name']}'")
                sys.stdout.flush()
                
                # Create or reuse dummy source column
                if not dummy_source_col:
                    dummy_source_col = create_dummy_column(source_table_guid, "Unmapped", "Source")
                    if not dummy_source_col:
                        print(f"     Failed to create dummy source column")
                        sys.stdout.flush()
                        skipped_count += 1
                        continue
                
                # Create lineage from dummy source to this target column
                relationship = {
                    "typeName": "column_lineage",
                    "guid": "-1",
                    "attributes": {},
                    "end1": {
                        "typeName": "Column",
                        "guid": dummy_source_col['guid']
                    },
                    "end2": {
                        "typeName": "Column",
                        "guid": target_col['guid']
                    }
                }
                
                url = f"{purview_endpoint}/datamap/api/atlas/v2/relationship"
                
                try:
                    response = requests.post(url, json=relationship, headers=headers)
                    
                    if response.status_code == 200:
                        created_count += 1
                        print(f"    [OK] Created lineage for unmapped target: Unmapped (Source) -> {target_col['name']}")
                        sys.stdout.flush()
                    elif response.status_code == 409:
                        print(f"   [INFO] Lineage already exists for: Unmapped (Source) -> {target_col['name']}")
                        sys.stdout.flush()
                        created_count += 1
                    else:
                        print(f"    [ERROR] Failed: {response.status_code}")
                        sys.stdout.flush()
                        skipped_count += 1
                        
                except Exception as e:
                    print(f"    [ERROR] Error: {e}")
                    sys.stdout.flush()
                    skipped_count += 1
        
        print(f"\n Column Lineage Summary:")
        print(f"    Created: {created_count}")
        print(f"     Skipped: {skipped_count}")
        import sys
        sys.stdout.flush()
        
        return {
            'success': True,
            'column_lineage_count': created_count,
            'skipped_count': skipped_count
        }
        
    except Exception as e:
        print(f" Error creating column lineage: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }

def create_lineage_relationship(entity1_qname, entity2_qname, relationship_type, entity1_type="DataSet", entity2_type="DataSet", column_mappings=None):
    """
    Create a lineage relationship between two entities in Purview.
    
    Args:
        entity1_qname: Qualified name of first entity
        entity2_qname: Qualified name of second entity
        relationship_type: Type of relationship (dataset_process_inputs, process_dataset_outputs, direct_lineage_dataset_dataset)
        entity1_type: Type of first entity (DataSet or Process)
        entity2_type: Type of second entity (DataSet or Process)
        column_mappings: Optional column mappings for direct dataset-to-dataset lineage
    
    Returns:
        dict: Created relationship
    """
    try:
        access_token = get_access_token(tenant_id, client_id, client_secret)
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Build relationship payload
        relationship = {
            "typeName": relationship_type,
            "guid": "-1",
            "end1": {
                "typeName": entity1_type,
                "uniqueAttributes": {
                    "qualifiedName": entity1_qname
                }
            },
            "end2": {
                "typeName": entity2_type,
                "uniqueAttributes": {
                    "qualifiedName": entity2_qname
                }
            }
        }
        
        # Add column mapping for direct dataset-to-dataset lineage
        if column_mappings and relationship_type == "direct_lineage_dataset_dataset":
            relationship["attributes"] = {
                "columnMapping": json.dumps(column_mappings)
            }
        
        # Create relationship
        url = f"{purview_endpoint}/datamap/api/atlas/v2/relationship"
        print(f"\n Creating {relationship_type} relationship")
        print(f"   From: {entity1_qname}")
        print(f"   To: {entity2_qname}")
        
        response = requests.post(url, json=relationship, headers=headers)
        
        # Handle 409 Conflict (relationship already exists)
        if response.status_code == 409:
            print(f" Relationship already exists (409 Conflict)")
            return {
                'success': True,
                'relationship_guid': 'existing',
                'relationship_type': relationship_type,
                'message': 'Relationship already exists'
            }
        
        response.raise_for_status()
        
        result = response.json()
        relationship_guid = result.get('guid')
        
        print(f" Relationship created with GUID: {relationship_guid}")
        
        return {
            'success': True,
            'relationship_guid': relationship_guid,
            'relationship_type': relationship_type
        }
        
    except Exception as e:
        error_msg = str(e)
        # Check if it's a 409 conflict error
        if '409' in error_msg and 'Conflict' in error_msg:
            print(f" Relationship already exists")
            return {
                'success': True,
                'relationship_guid': 'existing',
                'relationship_type': relationship_type,
                'message': 'Relationship already exists'
            }
        
        print(f" Error creating relationship: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }

def create_lineage_for_asset(source_guid, target_guid, process_name=None, column_mappings=None, use_process=False):
    """
    Create lineage between two assets in Microsoft Purview.
    
    Args:
        source_guid: GUID of the source asset
        target_guid: GUID of the target asset
        process_name: Optional name for the lineage process (not used when use_process=False)
        column_mappings: Optional list of column mappings [{"Source":"col1","Sink":"col1"}]
        use_process: If True, create Dataset->Process->Dataset lineage. If False (default), create direct Dataset->Dataset lineage with column mappings.
    
    Returns:
        dict: Result of lineage creation
    """
    try:
        # Get entity details for source and target
        credential = get_credentials()
        client = DataMapClient(endpoint=purview_endpoint, credential=credential)
        
        source_response = client.entity.get_by_ids(guid=[source_guid])
        target_response = client.entity.get_by_ids(guid=[target_guid])
        
        if not source_response.get('entities') or not target_response.get('entities'):
            return {'success': False, 'error': 'Source or target asset not found'}
        
        source_entity = source_response['entities'][0]
        target_entity = target_response['entities'][0]
        
        source_qname = source_entity['attributes']['qualifiedName']
        target_qname = target_entity['attributes']['qualifiedName']
        
        print(f"\n Creating lineage: {source_entity['attributes']['name']} -> {target_entity['attributes']['name']}")
        
        if use_process and process_name:
            # Create Dataset -> Process -> Dataset lineage
            
            # Step 1: Create process entity with GUIDs to prevent duplicate asset creation
            process_result = create_process_entity(
                source_qname, 
                target_qname, 
                process_name, 
                column_mappings,
                source_guid=source_guid,  # Pass GUIDs to prevent duplicates
                target_guid=target_guid
            )
            
            if not process_result['success']:
                return process_result
            
            process_qname = process_result['process_qualified_name']
            
            # Step 2: Create source -> process relationship (dataset_process_inputs)
            input_relationship = create_lineage_relationship(
                source_qname,
                process_qname,
                "dataset_process_inputs",
                entity1_type="DataSet",
                entity2_type="Process"
            )
            
            if not input_relationship['success']:
                return input_relationship
            
            # Step 3: Create process -> target relationship (process_dataset_outputs)
            output_relationship = create_lineage_relationship(
                process_qname,
                target_qname,
                "process_dataset_outputs",
                entity1_type="Process",
                entity2_type="DataSet"
            )
            
            if not output_relationship['success']:
                return output_relationship
            
            # Step 4: Create column-level lineage (direct column-to-column relationships)
            column_lineage_result = {'column_lineage_count': 0, 'skipped_count': 0}
            print(f"\n DEBUG: column_mappings = {column_mappings}")
            print(f" DEBUG: column_mappings type = {type(column_mappings)}")
            print(f" DEBUG: bool(column_mappings) = {bool(column_mappings)}")
            if column_mappings:
                print(f"\n Creating column-level lineage for {len(column_mappings)} column mapping(s)...")
                column_lineage_result = create_column_lineage(
                    source_guid,
                    target_guid,
                    column_mappings
                )
            else:
                print("\n  No column mappings provided, skipping column lineage creation")
            
            return {
                'success': True,
                'message': f'Lineage created with process: {source_guid} -> {process_name} -> {target_guid}',
                'process_guid': process_result['process_guid'],
                'input_relationship_guid': input_relationship['relationship_guid'],
                'output_relationship_guid': output_relationship['relationship_guid'],
                'column_lineage_count': column_lineage_result.get('column_lineage_count', 0),
                'column_lineage_skipped': column_lineage_result.get('skipped_count', 0)
            }
        else:
            # Create direct Dataset -> Dataset lineage
            print(f"\n Creating DIRECT table-to-table lineage (no process)")
            relationship = create_lineage_relationship(
                source_qname,
                target_qname,
                "direct_lineage_dataset_dataset",
                entity1_type="DataSet",
                entity2_type="DataSet",
                column_mappings=column_mappings
            )
            
            if not relationship['success']:
                return relationship
            
            # Create column-level lineage for direct dataset-to-dataset relationships
            column_lineage_result = {'column_lineage_count': 0, 'skipped_count': 0}
            if column_mappings:
                print(f"\n Creating column-level lineage for {len(column_mappings)} column mapping(s)...")
                column_lineage_result = create_column_lineage(
                    source_guid,
                    target_guid,
                    column_mappings
                )
            else:
                print("\n  No column mappings provided, skipping column lineage creation")
            
            return {
                'success': True,
                'message': f'Direct lineage created: {source_guid} -> {target_guid}',
                'relationship_guid': relationship['relationship_guid'],
                'column_lineage_count': column_lineage_result.get('column_lineage_count', 0),
                'column_lineage_skipped': column_lineage_result.get('skipped_count', 0)
            }
        
    except Exception as e:
        print(f" Error creating lineage: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }

async def create_lineage_async(session, endpoint, source_guid, target_guid, process_name, access_token):
    """
    Create lineage asynchronously.
    
    Args:
        session: aiohttp ClientSession
        endpoint: Purview endpoint
        source_guid: Source asset GUID
        target_guid: Target asset GUID
        process_name: Process name
        access_token: Auth token
    
    Returns:
        dict: Result of lineage creation
    """
    try:
        # TODO: Add async lineage creation logic here
        
        print(f"[Async] Creating lineage: {source_guid} -> {target_guid}")
        
        return {
            'success': True,
            'source': source_guid,
            'target': target_guid
        }
        
    except Exception as e:
        print(f"Error in async lineage creation: {e}")
        return {
            'success': False,
            'error': str(e)
        }

async def create_batch_lineage_async(lineage_pairs, access_token, endpoint):
    """
    Create multiple lineage relationships in parallel.
    
    Args:
        lineage_pairs: List of dicts with 'source', 'target', 'process_name'
        access_token: Auth token
        endpoint: Purview endpoint
    
    Returns:
        list: Results for each lineage creation
    """
    import ssl
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for pair in lineage_pairs:
            task = create_lineage_async(
                session,
                endpoint,
                pair['source'],
                pair['target'],
                pair.get('process_name', 'Data Flow'),
                access_token
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return results

def discover_fabric_lineage(guid):
    """
    Automatically discover lineage for a Fabric asset using Foundry agent.
    
    Args:
        guid: Asset GUID to discover lineage for
    
    Returns:
        dict: Discovered lineage information
    """
    try:
        # Get workspace info from Purview
        workspace_info = get_workspace_info_from_purview(guid)
        
        if not workspace_info:
            return {'success': False, 'error': 'Could not extract workspace information'}
        
        print(f" Discovering lineage for asset: {workspace_info.get('asset_name')}")
        print(f"   Workspace: {workspace_info.get('workspace_name')} ({workspace_info.get('workspace_id')})")
        
        # Use Fabric Agent if enabled
        if use_fabric_agent:
            lineage_data = analyze_lineage_with_fabric_agent(workspace_info)
            
            if lineage_data:
                return {
                    'success': True,
                    'mode': 'ai_discovered',
                    'workspace_info': workspace_info,
                    'lineage': lineage_data
                }
        
        # Fallback: manual discovery from Purview relationships
        print(" Fabric Agent not available, using Purview relationships")
        credential = get_credentials()
        client = DataMapClient(endpoint=purview_endpoint, credential=credential)
        
        # Get entity details
        response = client.entity.get_by_ids(guid=[guid])
        
        if not response or 'entities' not in response or not response['entities']:
            return {'success': False, 'error': 'Asset not found'}
        
        entity = response['entities'][0]
        
        # Extract lineage from Purview relationships
        discovered_lineage = {
            'upstream_assets': [],
            'downstream_assets': [],
            'processes': []
        }
        
        # TODO: Parse Purview relationshipAttributes for lineage
        
        return {
            'success': True,
            'mode': 'purview_relationships',
            'workspace_info': workspace_info,
            'lineage': discovered_lineage
        }
        
    except Exception as e:
        print(f"Error discovering lineage: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }

def main(lineage_pairs, auto_discover=False):
    """
    Main entry point for lineage creation.
    
    Args:
        lineage_pairs: List of lineage relationships to create
        auto_discover: If True, automatically discover lineage from Fabric
    
    Returns:
        dict: Results of lineage creation
    """
    try:
        access_token = get_access_token(tenant_id, client_id, client_secret)
        
        if auto_discover:
            # Auto-discover mode: analyze assets and suggest lineage
            results = []
            for pair in lineage_pairs:
                discovered = discover_fabric_lineage(pair.get('source'))
                results.append(discovered)
            return {
                'success': True,
                'mode': 'auto-discover',
                'results': results
            }
        else:
            # Manual mode: create specified lineage
            results = asyncio.run(
                create_batch_lineage_async(lineage_pairs, access_token, purview_endpoint)
            )
            return {
                'success': True,
                'mode': 'manual',
                'results': results
            }
            
    except Exception as e:
        print(f"Error in lineage creation: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == "__main__":
    # Test the lineage creation
    test_pairs = [
        {
            'source': 'source-guid-here',
            'target': 'target-guid-here',
            'process_name': 'Data Transformation'
        }
    ]
    
    result = main(test_pairs)
    print(json.dumps(result, indent=2))

def delete_lineage_by_process_guid(process_guid):
    """
    Delete a process entity and all its relationships from Purview by GUID.
    
    IMPORTANT: This ONLY deletes:
    - The Process entity itself
    - Relationships (dataset_process_inputs, process_dataset_outputs)
    
    It does NOT delete:
    - Source/target DataSet entities (tables, lakehouses, etc.)
    - Any actual data assets
    
    When a Process entity is deleted, Atlas automatically cascades to delete all its 
    relationships, but the referenced DataSet entities remain intact.
    
    Args:
        process_guid: GUID of the process entity to delete
    
    Returns:
        dict: Result of deletion
    """
    try:
        access_token = get_access_token(tenant_id, client_id, client_secret)
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Delete ONLY the Process entity by GUID
        # Atlas will cascade delete relationships but NOT the DataSet entities
        url = f"{purview_endpoint}/datamap/api/atlas/v2/entity/guid/{process_guid}"
        print(f"\n Deleting Process entity (NOT data assets): {process_guid}")
        
        response = requests.delete(url, headers=headers)
        
        if response.status_code == 204 or response.status_code == 200:
            print(f" Process deleted (data assets remain intact)")
            return {
                'success': True,
                'message': f'Process and relationships deleted (data assets safe)'
            }
        elif response.status_code == 404:
            print(f" Process not found (may have been deleted already)")
            return {
                'success': True,
                'message': 'Process already deleted'
            }
        else:
            response.raise_for_status()
            
    except Exception as e:
        error_msg = str(e)
        if '404' in error_msg:
            print(f" Process not found")
            return {
                'success': True,
                'message': 'Process already deleted'
            }
        
        print(f" Error deleting process: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def delete_all_workspace_lineage(workspace_id):
    """
    Delete ALL lineage relationships for assets in a workspace.
    This includes:
    - Column-to-column lineage relationships
    - Table-to-table lineage relationships (direct or through process)
    
    Args:
        workspace_id: Fabric workspace ID
    
    Returns:
        dict: Result of deletion
    """
    try:
        print(f"\n[DELETE] Finding lineage relationships for workspace: {workspace_id}")
        
        # Get all assets in workspace
        import get_data
        df = get_data.main()
        workspace_pattern = f"groups/{workspace_id}/"
        workspace_assets = df[df['qualifiedName'].str.contains(workspace_pattern, na=False)]
        
        print(f"[INFO] Found {len(workspace_assets)} assets in workspace")
        
        # Get access token
        access_token = get_access_token(tenant_id, client_id, client_secret)
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        credential = get_credentials()
        from azure.purview.datamap import DataMapClient
        client = DataMapClient(endpoint=purview_endpoint, credential=credential)
        
        deleted_column_count = 0
        deleted_table_count = 0
        
        # For each asset, find and delete all lineage relationships
        for _, asset_row in workspace_assets.iterrows():
            asset_guid = asset_row.get('guid') or asset_row.get('id')
            asset_name = asset_row.get('name', 'Unknown')
            
            try:
                # Get entity with relationships
                entity_response = client.entity.get_by_ids(guid=[asset_guid])
                if not entity_response or 'entities' not in entity_response:
                    continue
                
                entity = entity_response['entities'][0]
                relationship_attributes = entity.get('relationshipAttributes', {})
                
                # Delete table-level lineage relationships
                for rel_key, rel_value in relationship_attributes.items():
                    if rel_key in ['meanings', 'collection']:
                        # Skip non-lineage relationships
                        continue
                    
                    # Process relationship lists
                    if isinstance(rel_value, list):
                        for rel in rel_value:
                            if isinstance(rel, dict) and 'relationshipGuid' in rel:
                                rel_guid = rel['relationshipGuid']
                                rel_type = rel.get('relationshipType', '')
                                
                                # Delete lineage-related relationships
                                if any(keyword in rel_type.lower() for keyword in ['lineage', 'input', 'output', 'process']):
                                    try:
                                        delete_url = f"{purview_endpoint}/datamap/api/atlas/v2/relationship/guid/{rel_guid}"
                                        response = requests.delete(delete_url, headers=headers)
                                        if response.status_code in [200, 204]:
                                            deleted_table_count += 1
                                            print(f"  [OK] Deleted table lineage from {asset_name}: {rel_type}")
                                    except Exception as e:
                                        print(f"  [ERROR] Failed to delete {rel_guid}: {e}")
                    
                    # Process single relationships
                    elif isinstance(rel_value, dict) and 'relationshipGuid' in rel_value:
                        rel_guid = rel_value['relationshipGuid']
                        rel_type = rel_value.get('relationshipType', '')
                        
                        if any(keyword in rel_type.lower() for keyword in ['lineage', 'input', 'output', 'process']):
                            try:
                                delete_url = f"{purview_endpoint}/datamap/api/atlas/v2/relationship/guid/{rel_guid}"
                                response = requests.delete(delete_url, headers=headers)
                                if response.status_code in [200, 204]:
                                    deleted_table_count += 1
                                    print(f"  [OK] Deleted table lineage from {asset_name}: {rel_type}")
                            except Exception as e:
                                print(f"  [ERROR] Failed to delete {rel_guid}: {e}")
                
                # Delete column-level lineage if entity has columns
                attributes = entity.get('attributes', {})
                if 'columns' in attributes:
                    columns = attributes['columns']
                    
                    for col in columns:
                        col_guid = col.get('guid')
                        if not col_guid:
                            continue
                        
                        # Get column entity with relationships
                        col_entity_response = client.entity.get_by_ids(guid=[col_guid])
                        if not col_entity_response or 'entities' not in col_entity_response:
                            continue
                        
                        col_entity = col_entity_response['entities'][0]
                        col_rel_attributes = col_entity.get('relationshipAttributes', {})
                        
                        # Delete column lineage relationships
                        for rel_key, rel_value in col_rel_attributes.items():
                            if rel_key in ['meanings']:
                                continue
                            
                            if isinstance(rel_value, list):
                                for rel in rel_value:
                                    if isinstance(rel, dict) and 'relationshipGuid' in rel:
                                        rel_guid = rel['relationshipGuid']
                                        rel_type = rel.get('relationshipType', '')
                                        
                                        if 'lineage' in rel_type.lower():
                                            try:
                                                delete_url = f"{purview_endpoint}/datamap/api/atlas/v2/relationship/guid/{rel_guid}"
                                                response = requests.delete(delete_url, headers=headers)
                                                if response.status_code in [200, 204]:
                                                    deleted_column_count += 1
                                            except Exception as e:
                                                print(f"  [ERROR] Failed to delete column lineage {rel_guid}: {e}")
                            
                            elif isinstance(rel_value, dict) and 'relationshipGuid' in rel_value:
                                rel_guid = rel_value['relationshipGuid']
                                rel_type = rel_value.get('relationshipType', '')
                                
                                if 'lineage' in rel_type.lower():
                                    try:
                                        delete_url = f"{purview_endpoint}/datamap/api/atlas/v2/relationship/guid/{rel_guid}"
                                        response = requests.delete(delete_url, headers=headers)
                                        if response.status_code in [200, 204]:
                                            deleted_column_count += 1
                                    except Exception as e:
                                        print(f"  [ERROR] Failed to delete column lineage {rel_guid}: {e}")
            
            except Exception as e:
                print(f"[WARN] Could not process {asset_name}: {e}")
                continue
        
        total_deleted = deleted_column_count + deleted_table_count
        print(f"\n[COMPLETE] Deleted {total_deleted} lineage relationship(s)")
        print(f"  - Column lineage: {deleted_column_count}")
        print(f"  - Table lineage: {deleted_table_count}")
        
        return {
            'success': True,
            'message': f'Deleted {total_deleted} lineage relationships ({deleted_column_count} column, {deleted_table_count} table)',
            'deleted_count': total_deleted,
            'column_count': deleted_column_count,
            'table_count': deleted_table_count
        }
    except Exception as e:
        print(f"[ERROR] Failed to delete workspace lineage: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }
