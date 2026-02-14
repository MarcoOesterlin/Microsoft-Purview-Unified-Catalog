#!/usr/bin/env python3
"""
Comprehensive script to find and delete ALL fabric_lineage_process entities from Purview.
Uses multiple methods to ensure all processes are found and deleted.
"""

import os
import sys
import requests

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import from create_lineage to reuse credentials
import create_lineage
import get_data

purview_endpoint = create_lineage.purview_endpoint
tenant_id = create_lineage.tenant_id
client_id = create_lineage.client_id
client_secret = create_lineage.client_secret

def get_access_token(tenant_id, client_id, client_secret):
    """Get OAuth2 access token for Purview."""
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/token"
    token_data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'resource': 'https://purview.azure.net'
    }
    
    response = requests.post(token_url, data=token_data)
    response.raise_for_status()
    return response.json()['access_token']

def find_processes_via_lineage(headers, workspace_id):
    """Find processes by querying lineage of all workspace assets."""
    print("\n" + "="*80)
    print("METHOD 1: Finding processes via lineage queries")
    print("="*80)
    
    # Get all workspace assets
    try:
        df = get_data.main()
        workspace_assets = df[df['id'].str.contains(workspace_id, na=False)]
        all_guids = workspace_assets['guid'].tolist()
        print(f"Found {len(all_guids)} assets in workspace")
    except:
        # Fallback to known GUIDs - replace these with your actual asset GUIDs
        all_guids = [
            # Add your asset GUIDs here if workspace discovery fails
            # Example: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
        ]
        print(f"Using {len(all_guids)} known asset GUIDs")
    
    all_processes = {}
    
    for i, guid in enumerate(all_guids):
        if i % 10 == 0:
            print(f"  Progress: {i}/{len(all_guids)}")
        
        lineage_url = f"{purview_endpoint}/datamap/api/atlas/v2/lineage/{guid}"
        params = {'depth': 20, 'direction': 'BOTH', 'width': 20}
        
        try:
            response = requests.get(lineage_url, headers=headers, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                guidEntityMap = data.get('guidEntityMap', {})
                
                for proc_guid, entity in guidEntityMap.items():
                    if entity.get('typeName') == 'Process':
                        qn = entity.get('attributes', {}).get('qualifiedName', '')
                        if 'fabric_lineage_process://' in qn:
                            all_processes[proc_guid] = qn
        except:
            pass
    
    print(f"\nFound {len(all_processes)} processes via lineage")
    return all_processes

def find_processes_via_collection(headers, collection_id='osterlin'):
    """Find processes by listing all entities in a collection."""
    print("\n" + "="*80)
    print("METHOD 2: Finding processes via collection listing")
    print("="*80)
    
    all_processes = {}
    
    search_url = f"{purview_endpoint}/datamap/api/atlas/v2/search/basic"
    
    # Try to search within collection
    payload = {
        "keywords": "*",
        "filter": {
            "collectionId": collection_id
        },
        "limit": 1000
    }
    
    try:
        response = requests.post(search_url, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            entities = data.get('value', [])
            
            print(f"Found {len(entities)} total entities in collection")
            
            for entity in entities:
                if entity.get('entityType') == 'Process' or entity.get('objectType') == 'Process':
                    qn = entity.get('qualifiedName', '')
                    guid = entity.get('id', '')
                    if 'fabric_lineage_process://' in qn and guid:
                        all_processes[guid] = qn
        else:
            print(f"Collection search failed: {response.status_code}")
    except Exception as e:
        print(f"Collection search error: {e}")
    
    print(f"Found {len(all_processes)} processes via collection")
    return all_processes

def delete_process(headers, guid, qn):
    """Delete a single process by GUID."""
    delete_url = f"{purview_endpoint}/datamap/api/atlas/v2/entity/guid/{guid}"
    
    try:
        response = requests.delete(delete_url, headers=headers)
        
        if response.status_code in [200, 204]:
            return True, "Deleted"
        elif response.status_code == 404:
            return True, "Already deleted"
        else:
            return False, f"Status {response.status_code}"
    except Exception as e:
        return False, str(e)

def main():
    print("=" * 80)
    print("COMPREHENSIVE FABRIC LINEAGE PROCESS CLEANER")
    print("=" * 80)
    print("\nThis script will find and delete ALL processes with")
    print("qualifiedName starting with: fabric_lineage_process://")
    
    # Get access token
    print("\n1. Authenticating with Azure AD...")
    access_token = get_access_token(tenant_id, client_id, client_secret)
    print("    Authenticated")
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Find processes using multiple methods
    # Replace with your actual workspace ID if needed
    workspace_id = None  # Set to your workspace GUID or leave None to skip workspace-based discovery
    
    all_processes = {}
    
    # Method 1: Via lineage
    processes_1 = find_processes_via_lineage(headers, workspace_id)
    all_processes.update(processes_1)
    
    # Method 2: Via collection
    processes_2 = find_processes_via_collection(headers)
    all_processes.update(processes_2)
    
    # Summary
    print("\n" + "="*80)
    print(f"TOTAL UNIQUE PROCESSES FOUND: {len(all_processes)}")
    print("="*80)
    
    if not all_processes:
        print("\n No fabric_lineage_process entities found")
        return
    
    # Display all processes
    print("\nProcesses to delete:")
    for i, (guid, qn) in enumerate(all_processes.items(), 1):
        print(f"\n{i}. {guid}")
        print(f"   {qn[:100]}")
    
    # Confirm deletion
    print("\n" + "="*80)
    response = input(f"\nDelete {len(all_processes)} process(es)? (yes/no): ")
    
    if response.lower() != 'yes':
        print("Deletion cancelled")
        return
    
    # Delete all processes
    print("\n" + "="*80)
    print("DELETING PROCESSES")
    print("="*80)
    
    deleted_count = 0
    failed_count = 0
    
    for i, (guid, qn) in enumerate(all_processes.items(), 1):
        print(f"\n[{i}/{len(all_processes)}] {guid}")
        print(f"  {qn[:70]}...")
        
        success, message = delete_process(headers, guid, qn)
        
        if success:
            deleted_count += 1
            print(f"   {message}")
        else:
            failed_count += 1
            print(f"   Failed: {message}")
    
    # Final summary
    print("\n" + "="*80)
    print("DELETION COMPLETE")
    print("="*80)
    print(f"Successfully deleted: {deleted_count}")
    print(f"Failed: {failed_count}")
    print(f"Total: {len(all_processes)}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
