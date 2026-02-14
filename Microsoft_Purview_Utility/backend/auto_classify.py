from azure.identity import ClientSecretCredential 
from azure.core.exceptions import HttpResponseError
from azure.purview.datamap import DataMapClient
import requests
import os
import dotenv
import asyncio
import aiohttp
from urllib.parse import quote
import json

# Load environment variables
dotenv.load_dotenv()

# Azure AI Foundry configuration
use_fabric_agent = os.getenv("USE_FABRIC_AGENT", "false").lower() == "true"
azure_foundry_endpoint = os.getenv("AZURE_EXISTING_AIPROJECT_ENDPOINT", "")
azure_foundry_agent_name = os.getenv("AZURE_CLASSIFICATION_EXISTING_AGENT_ID", "classification-agent")
azure_foundry_env_name = os.getenv("AZURE_CLASSIFICATION_ENV_NAME", "")

tenant_id = os.getenv("TENANTID")
client_id = os.getenv("CLIENTID")
client_secret = os.getenv("CLIENTSECRET")
purview_endpoint = os.getenv("PURVIEWENDPOINT")
purview_scan_endpoint = os.getenv("PURVIEWSCANENDPOINT")
purview_account_name = os.getenv("PURVIEWACCOUNTNAME")

def get_access_token(tenant_id, client_id, client_secret):
    """Get access token for Purview API"""
    credential = ClientSecretCredential(
        tenant_id=tenant_id, 
        client_id=client_id, 
        client_secret=client_secret
    )
    token = credential.get_token("https://purview.azure.net/.default")
    return token.token

def get_credentials():
    """Get credentials for DataMapClient"""
    return ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret
    )

def get_available_classifications():
    """Get list of all available classifications from Purview"""
    try:
        access_token = get_access_token(tenant_id, client_id, client_secret)
        url = f"{purview_endpoint}/catalog/api/atlas/v2/types/typedefs?type=classification&api-version=2022-03-01-preview"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            classification_defs = data.get('classificationDefs', [])
            return [c.get('name') for c in classification_defs if c.get('name')]
        else:
            return []
    except Exception:
        return []

def get_entity_schema_with_sdk(guid):
    """Get entity schema using DataMapClient SDK (more reliable)"""
    try:
        credential = get_credentials()
        client = DataMapClient(endpoint=purview_endpoint, credential=credential)
        
        # Get entity by ID
        response = client.entity.get_by_ids(guid=[guid])
        
        if not response or 'entities' not in response or not response['entities']:
            return None
        
        entity = response['entities'][0]
        
        # Extract columns from multiple possible locations
        columns = None
        
        # Check relationshipAttributes first (most common for tables)
        if 'relationshipAttributes' in entity and 'columns' in entity['relationshipAttributes']:
            columns = entity['relationshipAttributes']['columns']
        # Check entity root
        elif 'columns' in entity:
            columns = entity['columns']
        # Check attributes
        elif 'attributes' in entity and 'columns' in entity['attributes']:
            columns = entity['attributes']['columns']
        
        return {
            'entity': entity,
            'columns': columns
        }
        
    except HttpResponseError:
        return None
    except Exception:
        return None

async def get_entity_details_async(session, endpoint, guid, access_token):
    """Get entity details to extract column information"""
    url = f"{endpoint}/datamap/api/atlas/v2/entity/guid/{guid}?api-version=2023-09-01"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                return None
    except Exception:
        return None

def get_entity_details(endpoint, guid, access_token):
    """Get entity details synchronously"""
    url = f"{endpoint}/datamap/api/atlas/v2/entity/guid/{guid}?api-version=2023-09-01"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return None

def parse_onelake_path(qualified_name):
    """
    Parse OneLake path to extract workspace, lakehouse, and table information.
    Example path: https://onelake.dfs.fabric.microsoft.com//{workspace_id}/{lakehouse_id}/Tables/{table_name}
    Returns: (workspace_id, lakehouse_id, table_name)
    """
    try:
        # Extract IDs from the path
        parts = qualified_name.split('/')
        workspace_id = None
        lakehouse_id = None
        table_name = None
        
        # Find workspace ID (first GUID in path)
        for part in parts:
            if len(part) == 36 and part.count('-') == 4:  # GUID format
                if workspace_id is None:
                    workspace_id = part
                elif lakehouse_id is None:
                    lakehouse_id = part
                    break
        
        # Extract table name (last part)
        if 'Tables/' in qualified_name:
            table_name = qualified_name.split('Tables/')[-1].strip('/')
        elif 'tables/' in qualified_name.lower():
            table_name = qualified_name.split('tables/')[-1].strip('/')
        
        return workspace_id, lakehouse_id, table_name
    except Exception as e:
        print(f"Error parsing OneLake path: {e}")
        return None, None, None



def analyze_with_fabric_agent(asset_info):
    """
    Send asset information to Azure AI Foundry Agent and read the response.
    Agent will read the data by itself.
    
    Args:
        asset_info: Dict containing:
            - name: Asset name
            - qualified_name: Asset qualified name
            - available_classifications: List of available Purview classifications
    
    Returns:
        dict mapping column names to suggested classification lists
    """
    try:
        from openai import OpenAI
        from azure.identity import ClientSecretCredential, get_bearer_token_provider
        
        if not azure_foundry_endpoint:
            return None
        
        # Build the full responses endpoint URL
        # Format: https://{resource}.services.ai.azure.com/api/projects/{project}/applications/{app}/protocols/openai/responses
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
        
        # Build the prompt - include column names and types to help the agent
        columns_info = ""
        if 'columns' in asset_info and asset_info['columns']:
            columns_list = [f"  - {col['name']} ({col.get('type', 'unknown')})" for col in asset_info['columns']]
            columns_info = f"\n\nTable Columns:\n{chr(10).join(columns_list)}"
        
        prompt_content = f"""DELEGATE TO FABRIC DATA AGENT: Use the Fabric Data Agent to read ACTUAL DATA from this table and analyze the content.

Table Qualified Name (PASS THIS TO FABRIC DATA AGENT):
{asset_info['qualified_name']}

Table Name: {asset_info.get('name', 'Unknown')}{columns_info}

INSTRUCTIONS FOR FABRIC DATA AGENT:
1. Read at least 10-20 sample rows from the Fabric table using the qualified name above
2. Analyze the ACTUAL DATA CONTENT in each column (look at real values, not just column names)
3. Identify sensitive patterns: emails, names, phone numbers, SSNs, credit cards, IDs, addresses, etc.
4. Match patterns ONLY to classifications from the EXACT list below

========================================
AVAILABLE MICROSOFT PURVIEW CLASSIFICATIONS ({len(asset_info['available_classifications'])} total)
[STRICT REQUIREMENT] ONLY USE THESE EXACT CLASSIFICATION NAMES
DO NOT modify, abbreviate, or create variations of these names
========================================
{chr(10).join([f'- {c}' for c in asset_info['available_classifications']])}
========================================

[CLASSIFICATION GUIDELINES] USE ONLY EXACT NAMES FROM THE LIST ABOVE

CORRECT CLASSIFICATIONS FOR COMMON DATA:
[OK] FirstName, LastName, FullName, Name → MICROSOFT.PERSONAL.NAME
[OK] Email, EmailAddress → MICROSOFT.PERSONAL.EMAIL
[OK] Address, Street, City → MICROSOFT.PERSONAL.PHYSICALADDRESS
[OK] CreditCard, CCNumber → MICROSOFT.FINANCIAL.CREDIT_CARD_NUMBER
[OK] SSN, SocialSecurity → MICROSOFT.GOVERNMENT.US.SOCIAL_SECURITY_NUMBER
[OK] Phone, PhoneNumber → MICROSOFT.PERSONAL.US.PHONE_NUMBER
[OK] DOB, BirthDate → MICROSOFT.PERSONAL.DATE_OF_BIRTH
[DO NOT] DO NOT classify technical IDs (CustomerId, OrderId, RowId, etc.)

[CRITICAL VALIDATION RULES]
1. EVERY classification MUST be copied EXACTLY from the list above
2. DO NOT use "MICROSOFT.IDENTIFIER" - it's NOT in the list
3. DO NOT use "MICROSOFT.PERSONAL.FIRST_NAME" - use "MICROSOFT.PERSONAL.NAME" instead
4. DO NOT use "MICROSOFT.PERSONAL.LAST_NAME" - use "MICROSOFT.PERSONAL.NAME" instead
5. If a classification is NOT in the list, return empty [] for that column
6. Check EVERY suggestion against the list before returning

CORRECT Response Format:
{{"Email": ["MICROSOFT.PERSONAL.EMAIL"], "FirstName": ["MICROSOFT.PERSONAL.NAME"], "LastName": ["MICROSOFT.PERSONAL.NAME"]}}

WRONG Examples (DO NOT DO THIS):
[ERROR] {{"Email": ["MICROSOFT.PERSONAL.EMAIL_ADDRESS"]}} - Not in list!
[ERROR] {{"Name": ["PERSONAL.NAME"]}} - Missing MICROSOFT prefix!
[ERROR] {{"Phone": ["MICROSOFT.PERSONAL.PHONE"]}} - Not exact match!

Return ONLY a JSON object mapping column names to classification arrays.
Format: {{"ColumnName": ["EXACT.CLASSIFICATION.FROM.LIST"]}}

Invoke the Fabric Data Agent now. Return empty {{}} if no sensitive data patterns are found."""
        
        # Print payload being sent to Foundry
        print("\n" + "="*80)
        print("SENDING TO MICROSOFT FOUNDRY:")
        print("="*80)
        print(f"Base URL: {base_url}")
        print(f"Agent: {azure_foundry_agent_name}")
        print(f"\nPrompt:\n{prompt_content}")
        print("="*80 + "\n")
        
        # Call the responses API
        response = openai_client.responses.create(
            input=prompt_content
        )
        
        # Read the response
        ai_response = response.output_text
        print("\n" + "="*80)
        print("RESPONSE FROM MICROSOFT FOUNDRY:")
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
            
            print(f"PARSED JSON:\n{response_text}\n")
            
            suggestions = json.loads(response_text)
            print(f"Successfully parsed {len(suggestions)} column suggestions\n")
            
            # VALIDATE: Filter out any classifications not in the approved list
            if suggestions and isinstance(suggestions, dict):
                approved_set = set(asset_info['available_classifications'])
                validated_suggestions = {}
                invalid_found = []
                
                for col_name, classifications in suggestions.items():
                    if isinstance(classifications, list):
                        valid_classifications = []
                        for classification in classifications:
                            if classification in approved_set:
                                valid_classifications.append(classification)
                            else:
                                invalid_found.append(f"{col_name}: {classification}")
                        
                        if valid_classifications:
                            validated_suggestions[col_name] = valid_classifications
                
                if invalid_found:
                    print(f"[WARNING] Removed {len(invalid_found)} invalid classification(s):")
                    for invalid in invalid_found:
                        print(f"   - {invalid}")
                    print()
                
                return validated_suggestions  # Return validated dict
            
            return suggestions  # Return even if empty dict
            
        except json.JSONDecodeError as e:
            print(f"JSON Parse Error: {e}")
            print(f"Raw response text: {response_text}\n")
            return None
        
    except Exception as e:
        print(f"FOUNDRY ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

async def auto_classify_entity_async(session, endpoint, guid, access_token):
    """Automatically classify an entity based on its columns using Azure AI Foundry Agent"""
    
    # Use SDK method for more reliable schema fetching
    entity_response = get_entity_schema_with_sdk(guid)
    if not entity_response:
        return {'has_schema': False, 'classifications': {}, 'schema': []}
    
    entity = entity_response['entity']
    columns = entity_response['columns']
    asset_name = entity.get('attributes', {}).get('name', '')
    qualified_name = entity.get('attributes', {}).get('qualifiedName', '')
    
    # Dictionary to store column GUID -> classifications mapping
    column_classifications = {}
    schema_info = []
    has_schema = False
    
    # Check if we got columns
    if columns and len(columns) > 0:
        has_schema = True
        
        # Get available classifications from Purview
        available_classifications = get_available_classifications()
        
        # Prepare columns info
        columns_list = []
        for column_ref in columns:
            if isinstance(column_ref, dict):
                column_guid = column_ref.get('guid')
                column_name = column_ref.get('displayText', '') or column_ref.get('name', '')
                column_type = column_ref.get('typeName', '')
                
                if column_name and column_guid:
                    columns_list.append({
                        'name': column_name,
                        'guid': column_guid,
                        'type': column_type
                    })
        
        # Send asset info to Azure AI Foundry Agent
        ai_suggestions = None
        if use_fabric_agent and asset_name and qualified_name:
            try:
                asset_info = {
                    'name': asset_name,
                    'qualified_name': qualified_name,
                    'available_classifications': available_classifications,
                    'columns': columns_list  # Include column info for the agent
                }
                ai_suggestions = analyze_with_fabric_agent(asset_info)
            except Exception:
                ai_suggestions = None
        
        # Process columns with AI suggestions
        for col_info in columns_list:
            schema_info.append({
                'guid': col_info['guid'],
                'name': col_info['name'],
                'type': col_info['type']
            })
            
            # Check if AI provided suggestions for this column
            classifications = []
            if ai_suggestions and col_info['name'] in ai_suggestions:
                classifications = ai_suggestions[col_info['name']]
            
            if classifications:
                column_classifications[col_info['guid']] = {
                    'name': col_info['name'],
                    'classifications': classifications
                }
    
    return {
        'has_schema': has_schema,
        'classifications': column_classifications,
        'schema': schema_info
    }

def auto_classify_entity(endpoint, guid, access_token):
    """Synchronous wrapper for auto-classification with Azure AI Foundry Agent"""
    
    print(f"\n[SYNC] auto_classify_entity called for GUID: {guid}", flush=True)
    print(f"[SYNC] use_fabric_agent={use_fabric_agent}", flush=True)
    
    # Use SDK method for more reliable schema fetching
    entity_response = get_entity_schema_with_sdk(guid)
    if not entity_response:
        return {'has_schema': False, 'classifications': {}, 'schema': []}
    
    entity = entity_response['entity']
    columns = entity_response['columns']
    asset_name = entity.get('attributes', {}).get('name', '')
    qualified_name = entity.get('attributes', {}).get('qualifiedName', '')
    
    column_classifications = {}
    schema_info = []
    has_schema = False
    
    if columns and len(columns) > 0:
        has_schema = True
        
        # Get available classifications from Purview
        available_classifications = get_available_classifications()
        
        # Prepare columns info
        columns_list = []
        for column_ref in columns:
            if isinstance(column_ref, dict):
                column_guid = column_ref.get('guid')
                column_name = column_ref.get('displayText', '') or column_ref.get('name', '')
                column_type = column_ref.get('typeName', '')
                
                if column_name and column_guid:
                    columns_list.append({
                        'name': column_name,
                        'guid': column_guid,
                        'type': column_type
                    })
        
        # Send asset info to Azure AI Foundry Agent
        print(f"SYNC: use_fabric_agent={use_fabric_agent}, asset='{asset_name}', qn='{qualified_name}'", flush=True)
        ai_suggestions = None
        if use_fabric_agent and asset_name and qualified_name:
            try:
                asset_info = {
                    'name': asset_name,
                    'qualified_name': qualified_name,
                    'available_classifications': available_classifications,
                    'columns': columns_list  # Include column info for the agent
                }
                print(f"SYNC: Calling analyze_with_fabric_agent...", flush=True)
                ai_suggestions = analyze_with_fabric_agent(asset_info)
                print(f"SYNC: Agent returned: {ai_suggestions}", flush=True)
            except Exception as e:
                print(f"SYNC: Error calling agent: {e}", flush=True)
                ai_suggestions = None
        
        # Process columns with AI suggestions
        for col_info in columns_list:
            schema_info.append({
                'guid': col_info['guid'],
                'name': col_info['name'],
                'type': col_info['type']
            })
            
            # Only use AI agent suggestions
            classifications = []
            if ai_suggestions and col_info['name'] in ai_suggestions:
                classifications = ai_suggestions[col_info['name']]
                print(f"SYNC: Column '{col_info['name']}' has {len(classifications)} classifications: {classifications}", flush=True)
            
            if classifications:
                column_classifications[col_info['guid']] = {
                    'name': col_info['name'],
                    'classifications': classifications
                }
        
        print(f"SYNC: Returning {len(column_classifications)} columns with classifications", flush=True)
    
    return {
        'has_schema': has_schema,
        'classifications': column_classifications,
        'schema': schema_info
    }

async def apply_column_classifications_async(session, endpoint, column_guid, classifications, access_token):
    """Apply classifications to a specific column"""
    url = f"{endpoint}/datamap/api/atlas/v2/entity/guid/{column_guid}/classifications?api-version=2023-09-01"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Format classifications for API
    classification_payload = [{"typeName": classification} for classification in classifications]
    
    try:
        async with session.post(url, headers=headers, json=classification_payload) as response:
            return response.status == 204
    except Exception:
        return False

async def process_auto_classification_async(guid_list, access_token, endpoint):
    """Process auto-classification for multiple GUIDs in parallel"""
    # Create SSL context that doesn't verify certificates (for self-signed certs)
    import ssl
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for guid in guid_list:
            task = auto_classify_entity_async(session, endpoint, guid, access_token)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Combine all suggested column classifications
        all_column_classifications = {}
        for guid, column_data in zip(guid_list, results):
            if column_data:
                all_column_classifications[guid] = column_data
        
        return all_column_classifications

async def apply_auto_classifications_async(guid_list, access_token, endpoint):
    """Analyze and immediately apply classifications to columns"""
    # Create SSL context that doesn't verify certificates (for self-signed certs)
    import ssl
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Step 1: Analyze all entities to get column classifications
        analyze_tasks = []
        for guid in guid_list:
            task = auto_classify_entity_async(session, endpoint, guid, access_token)
            analyze_tasks.append(task)
        
        analysis_results = await asyncio.gather(*analyze_tasks)
        
        # Step 2: Apply classifications to columns
        apply_tasks = []
        all_suggestions = {}
        
        for guid, column_data in zip(guid_list, analysis_results):
            if column_data:
                all_suggestions[guid] = column_data
                
                # Apply classifications to each column
                for column_guid, column_info in column_data.items():
                    classifications = column_info['classifications']
                    task = apply_column_classifications_async(session, endpoint, column_guid, classifications, access_token)
                    apply_tasks.append(task)
        
        # Wait for all applications to complete
        if apply_tasks:
            await asyncio.gather(*apply_tasks)
        
        return all_suggestions

def main(guid_list, parallel=True, apply=False):
    """
    Main function to auto-classify assets
    
    Args:
        guid_list: List of entity GUIDs to analyze
        parallel: Whether to use parallel processing
        apply: If True, immediately apply classifications. If False, just return suggestions
    
    Returns:
        Dictionary mapping entity GUID -> entity data with suggestions
        Format: {"entity_guid": {"has_schema": bool, "classifications": {...}, "schema": [...]}}
    """
    access_token = get_access_token(tenant_id, client_id, client_secret)
    
    if apply:
        if parallel and len(guid_list) > 1:
            results = asyncio.run(apply_auto_classifications_async(guid_list, access_token, purview_endpoint))
        else:
            results = {}
            for guid in guid_list:
                entity_data = auto_classify_entity(purview_endpoint, guid, access_token)
                if entity_data:
                    results[guid] = entity_data
                    # Apply classifications synchronously if has_schema
                    if entity_data.get('has_schema') and entity_data.get('classifications'):
                        for column_guid, column_info in entity_data['classifications'].items():
                            if column_info.get('classifications'):
                                apply_column_classifications_sync(purview_endpoint, column_guid, column_info['classifications'], access_token)
    else:
        if parallel and len(guid_list) > 1:
            results = asyncio.run(process_auto_classification_async(guid_list, access_token, purview_endpoint))
        else:
            results = {}
            for guid in guid_list:
                entity_data = auto_classify_entity(purview_endpoint, guid, access_token)
                if entity_data:
                    results[guid] = entity_data
    
    return results

def apply_column_classifications_sync(endpoint, column_guid, classifications, access_token):
    """Apply classifications to a column synchronously"""
    url = f"{endpoint}/datamap/api/atlas/v2/entity/guid/{column_guid}/classifications?api-version=2023-09-01"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    classification_payload = [{"typeName": classification} for classification in classifications]
    
    response = requests.post(url, headers=headers, json=classification_payload)
    return response.status_code == 204

if __name__ == "__main__":
    # Example usage:
    # Suggest only:
    # results = main(["your-entity-guid"], apply=False)
    # Returns: {"entity_guid": {"column_guid": {"name": "email", "classifications": ["MICROSOFT.PERSONAL.EMAIL"]}}}
    # 
    # Apply immediately:
    # results = main(["your-entity-guid"], apply=True)
    pass
