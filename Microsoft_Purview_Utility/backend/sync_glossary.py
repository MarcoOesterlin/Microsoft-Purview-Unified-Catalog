"""
Business Glossary Sync Tool
This module syncs governance domain terms from Microsoft Purview Unified Catalog 
to the Classic Business Glossary.
"""
import os
import requests
from dotenv import load_dotenv
from azure.identity import ClientSecretCredential
from azure.purview.datamap import DataMapClient
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Load environment variables
load_dotenv()

# Get configuration from environment variables
TENANT_ID = os.getenv("TENANTID")
CLIENT_ID = os.getenv("CLIENTID")
CLIENT_SECRET = os.getenv("CLIENTSECRET")
PURVIEW_ACCOUNT_NAME = os.getenv("PURVIEWACCOUNTNAME")
PURVIEW_ENDPOINT = os.getenv("PURVIEW_ENDPOINT", "https://api.purview-service.microsoft.com")

# Validate required environment variables
required_vars = {
    "TENANT_ID": TENANT_ID,
    "CLIENT_ID": CLIENT_ID,
    "CLIENT_SECRET": CLIENT_SECRET,
    "PURVIEW_ACCOUNT_NAME": PURVIEW_ACCOUNT_NAME,
}

missing_vars = [var for var, value in required_vars.items() if not value]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")


def get_access_token():
    """
    Get an access token using Azure AD authentication with client credentials.
    """
    try:
        credential = ClientSecretCredential(
            tenant_id=TENANT_ID,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET
        )
        
        # Get token for Purview scope
        token = credential.get_token("https://purview.azure.net/.default")
        return token.token
    except Exception as e:
        print(f"Error obtaining access token: {e}")
        raise


def get_datamap_client():
    """
    Initialize the Purview DataMapClient for classic glossary operations.
    """
    try:
        credential = ClientSecretCredential(
            tenant_id=TENANT_ID,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET
        )
        
        endpoint = f"https://{PURVIEW_ACCOUNT_NAME}.purview.azure.com"
        client = DataMapClient(endpoint=endpoint, credential=credential)
        return client
    except Exception as e:
        print(f"Error creating DataMapClient: {e}")
        raise


def get_domain_by_id(domain_id):
    """
    Get domain details by ID from Microsoft Purview Unified Catalog.
    Uses the Business Domain API to get the friendly name.
    
    Args:
        domain_id (str): Domain ID (GUID)
        
    Returns:
        dict: Domain information with friendlyName
    """
    try:
        access_token = get_access_token()
        
        # Construct the URL for business domain API
        api_version = "2025-09-15-preview"
        url = f"{PURVIEW_ENDPOINT}/datagovernance/catalog/businessDomains/{domain_id}"
        
        # Set up query parameters
        params = {
            "api-version": api_version
        }
        
        # Set up headers
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        print(f"[DEBUG] Fetching domain from: {url}")
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            domain_data = response.json()
            print(f"[DEBUG] Domain response: {domain_data}")
            return domain_data
        else:
            print(f"Error fetching domain {domain_id}: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Error getting domain by ID: {e}")
        return None


def list_unified_catalog_terms(skip=0, top=100):
    """
    List terms from Microsoft Purview Unified Catalog.
    
    Args:
        skip (int): Number of results to skip (for pagination)
        top (int): Maximum number of results to return
        
    Returns:
        dict: Response containing terms
    """
    try:
        access_token = get_access_token()
        
        # Construct the URL for terms API
        api_version = "2025-09-15-preview"
        url = f"{PURVIEW_ENDPOINT}/datagovernance/catalog/terms"
        
        # Set up query parameters
        params = {
            "api-version": api_version,
            "top": top,
            "skip": skip
        }
        
        # Set up headers
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        print(f"Requesting unified catalog terms from: {url}")
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            print(f"Response: {response.text}")
            response.raise_for_status()
            
    except Exception as e:
        print(f"Error listing unified catalog terms: {e}")
        raise


def list_all_unified_catalog_terms():
    """
    List all terms from Unified Catalog, handling pagination automatically.
    
    Returns:
        list: All terms from Unified Catalog
    """
    all_terms = []
    skip = 0
    top = 100
    
    while True:
        try:
            result = list_unified_catalog_terms(skip=skip, top=top)
            
            if "value" in result:
                terms = result["value"]
                # Debug: Check first term structure
                if terms and len(terms) > 0:
                    print(f"[DEBUG] First term type: {type(terms[0])}")
                    print(f"[DEBUG] First term sample: {terms[0]}")
                all_terms.extend(terms)
                print(f"Retrieved {len(terms)} terms (total: {len(all_terms)})")
                
                # Check if there's a next page
                if "nextLink" in result and result["nextLink"]:
                    skip += top
                else:
                    break
            else:
                break
        except Exception as e:
            print(f"Error during pagination: {e}")
            break
    
    return all_terms


def list_classic_glossaries():
    """
    List all glossaries from the Classic Business Glossary using REST API.
    
    Returns:
        list: All classic glossaries
    """
    try:
        access_token = get_access_token()
        endpoint = f"https://{PURVIEW_ACCOUNT_NAME}.purview.azure.com"
        url = f"{endpoint}/datamap/api/atlas/v2/glossary"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            glossaries = response.json()
            print(f"[DEBUG] Glossaries response type: {type(glossaries)}")
            print(f"[DEBUG] Glossaries response: {glossaries}")
            
            # The API might return a list or a single glossary object
            if isinstance(glossaries, list):
                return glossaries
            elif isinstance(glossaries, dict):
                # If it's a single glossary, wrap it in a list
                return [glossaries]
            else:
                print(f"[WARNING] Unexpected glossaries response type: {type(glossaries)}")
                return []
        else:
            print(f"Error listing glossaries: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"Error listing classic glossaries: {e}")
        import traceback
        traceback.print_exc()
        return []  # Return empty list instead of raising to prevent API crash


def get_classic_glossary_terms(glossary_guid):
    """
    Get all terms from a specific glossary in the Classic Business Glossary using REST API.
    
    Args:
        glossary_guid (str): GUID of the glossary
        
    Returns:
        list: All terms in the glossary
    """
    try:
        access_token = get_access_token()
        endpoint = f"https://{PURVIEW_ACCOUNT_NAME}.purview.azure.com"
        url = f"{endpoint}/datamap/api/atlas/v2/glossary/{glossary_guid}/terms"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error listing glossary terms: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"Error listing glossary terms: {e}")
        raise


def create_classic_glossary(name, description=None):
    """
    Create a new glossary in the Classic Business Glossary using REST API.
    
    Args:
        name (str): Name of the glossary
        description (str): Description of the glossary
        
    Returns:
        dict: Created glossary
    """
    try:
        access_token = get_access_token()
        endpoint = f"https://{PURVIEW_ACCOUNT_NAME}.purview.azure.com"
        url = f"{endpoint}/datamap/api/atlas/v2/glossary"
        
        glossary_data = {
            "name": name,
            "shortDescription": description or f"Synced from Governance Domain: {name}",
            "longDescription": description or f"This glossary was automatically synced from the Governance Domain '{name}' in the Unified Catalog."
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, headers=headers, json=glossary_data)
        
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"Created glossary: {name}")
            return result
        else:
            print(f"Error creating glossary: {response.status_code} - {response.text}")
            raise Exception(f"Failed to create glossary: {response.text}")
    except Exception as e:
        print(f"Error creating glossary: {e}")
        raise


def create_classic_glossary_term(glossary_guid, term_name, term_data):
    """
    Create a new term in the Classic Business Glossary using REST API.
    
    Args:
        glossary_guid (str): GUID of the glossary
        term_name (str): Name of the term
        term_data (dict): Term data from Unified Catalog
        
    Returns:
        dict: Created term
    """
    try:
        access_token = get_access_token()
        endpoint = f"https://{PURVIEW_ACCOUNT_NAME}.purview.azure.com"
        url = f"{endpoint}/datamap/api/atlas/v2/glossary/term"
        
        # Extract relevant fields from unified catalog term
        description = term_data.get("description", "")
        long_description = term_data.get("longDescription", "")
        
        # Extract owner/expert information
        contacts = []
        if "owner" in term_data and term_data["owner"]:
            owner_id = term_data["owner"].get("id") or term_data["owner"].get("objectId")
            if owner_id:
                contacts.append({
                    "id": owner_id,
                    "contactType": "Owner"
                })
        
        if "experts" in term_data and term_data["experts"]:
            for expert in term_data["experts"]:
                expert_id = expert.get("id") or expert.get("objectId")
                if expert_id:
                    contacts.append({
                        "id": expert_id,
                        "contactType": "Expert"
                    })
        
        # Create term payload
        term_payload = {
            "name": term_name,
            "shortDescription": description[:100] if description else "",
            "longDescription": long_description or description,
            "anchor": {
                "glossaryGuid": glossary_guid
            }
        }
        
        # Add contacts if available
        if contacts:
            term_payload["contacts"] = contacts
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, headers=headers, json=term_payload)
        
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"Created term: {term_name}")
            return result
        else:
            print(f"Error creating term: {response.status_code} - {response.text}")
            raise Exception(f"Failed to create term: {response.text}")
    except Exception as e:
        print(f"Error creating term '{term_name}': {e}")
        raise


def sync_glossary_from_unified_catalog(dry_run=False):
    """
    Main function to sync terms from Unified Catalog to Classic Business Glossary.
    
    Args:
        dry_run (bool): If True, only shows what would be created without creating anything
        
    Returns:
        dict: Summary of sync operation
    """
    summary = {
        "success": False,
        "message": "",
        "unified_terms_count": 0,
        "domains_processed": 0,
        "glossaries_created": 0,
        "glossaries_skipped": 0,
        "terms_created": 0,
        "terms_skipped": 0,
        "errors": []
    }
    
    try:
        # Step 1: Fetch all terms from Unified Catalog
        print("Fetching terms from Unified Catalog...")
        unified_terms = list_all_unified_catalog_terms()
        summary["unified_terms_count"] = len(unified_terms)
        print(f"Found {len(unified_terms)} terms in Unified Catalog")
        
        # Step 2: Get existing classic glossaries
        print("\nFetching existing classic glossaries...")
        classic_glossaries = list_classic_glossaries()
        # Create glossaries map, ensuring each glossary is a dict
        classic_glossaries_map = {}
        for g in classic_glossaries:
            if isinstance(g, dict):
                glossary_name = g.get("name", "")
                if glossary_name:
                    classic_glossaries_map[glossary_name] = g
        print(f"Found {len(classic_glossaries)} existing glossaries")
        
        # Step 3: Group terms by domain
        terms_by_domain = {}
        domain_cache = {}  # Cache domain lookups to avoid repeated API calls
        
        for term in unified_terms:
            # Skip if term is not a dictionary
            if not isinstance(term, dict):
                print(f"[WARNING] Skipping non-dict term: {type(term)}")
                continue
                
            # Get domain information
            domain_name = None
            if "domain" in term and term["domain"]:
                # Handle both string (domain ID) and dict domain values
                if isinstance(term["domain"], str):
                    # It's a domain ID, fetch the domain details (with caching)
                    domain_id = term["domain"]
                    
                    if domain_id in domain_cache:
                        domain_name = domain_cache[domain_id]
                    else:
                        domain_info = get_domain_by_id(domain_id)
                        if domain_info:
                            domain_name = domain_info.get("friendlyName") or domain_info.get("name")
                            print(f"Resolved domain ID {domain_id} to name: {domain_name}")
                        
                        if not domain_name:
                            print(f"[WARNING] Could not get name for domain ID: {domain_id}, using 'Unknown Domain'")
                            domain_name = f"Unknown Domain ({domain_id[:8]}...)"
                        
                        domain_cache[domain_id] = domain_name
                elif isinstance(term["domain"], dict):
                    domain_name = term["domain"].get("friendlyName") or term["domain"].get("displayName") or term["domain"].get("name")
            
            if not domain_name:
                domain_name = "Unassigned Domain"
            
            if domain_name not in terms_by_domain:
                terms_by_domain[domain_name] = []
            
            terms_by_domain[domain_name].append(term)
        
        summary["domains_processed"] = len(terms_by_domain)
        print(f"\nGrouped terms into {len(terms_by_domain)} domains")
        
        # Step 4: Process each domain
        for domain_name, domain_terms in terms_by_domain.items():
            print(f"\n{'='*80}")
            print(f"Processing domain: {domain_name} ({len(domain_terms)} terms)")
            print(f"{'='*80}")
            
            # Check if glossary already exists
            glossary_guid = None
            if domain_name in classic_glossaries_map:
                glossary = classic_glossaries_map[domain_name]
                glossary_guid = glossary.get("guid")
                print(f"[OK] Glossary '{domain_name}' already exists (GUID: {glossary_guid})")
                summary["glossaries_skipped"] += 1
            else:
                if dry_run:
                    print(f"[DRY RUN] Would create glossary: {domain_name}")
                    summary["glossaries_created"] += 1
                    continue
                else:
                    # Create new glossary
                    print(f"Creating new glossary: {domain_name}")
                    try:
                        new_glossary = create_classic_glossary(domain_name)
                        glossary_guid = new_glossary.get("guid")
                        summary["glossaries_created"] += 1
                    except Exception as e:
                        error_msg = f"Failed to create glossary '{domain_name}': {e}"
                        print(f"[ERROR] {error_msg}")
                        summary["errors"].append(error_msg)
                        continue
            
            # Get existing terms in this glossary
            existing_terms = []
            existing_terms_map = {}
            if glossary_guid:
                try:
                    existing_terms = get_classic_glossary_terms(glossary_guid)
                    existing_terms_map = {t.get("name", ""): t for t in existing_terms}
                    print(f"Found {len(existing_terms)} existing terms in this glossary")
                except Exception as e:
                    print(f"Warning: Could not fetch existing terms: {e}")
            
            # Create terms from this domain
            # Separate terms to create and terms to skip
            terms_to_create = []
            for term in domain_terms:
                term_name = term.get("name") or term.get("displayName", "Unnamed Term")
                
                # Check if term already exists
                if term_name in existing_terms_map:
                    print(f"  [OK] Term '{term_name}' already exists, skipping")
                    summary["terms_skipped"] += 1
                else:
                    if dry_run:
                        print(f"  [DRY RUN] Would create term: {term_name}")
                        summary["terms_created"] += 1
                    else:
                        terms_to_create.append((term_name, term))
            
            # Create terms in parallel if not dry run
            if not dry_run and terms_to_create:
                print(f"  Creating {len(terms_to_create)} terms in parallel...")
                
                # Thread-safe counter
                lock = threading.Lock()
                
                def create_term_wrapper(term_info):
                    term_name, term = term_info
                    try:
                        create_classic_glossary_term(glossary_guid, term_name, term)
                        return {"success": True, "term_name": term_name}
                    except Exception as e:
                        return {"success": False, "term_name": term_name, "error": str(e)}
                
                # Use ThreadPoolExecutor for parallel execution
                # Limit to 5 concurrent requests to avoid overwhelming the API
                with ThreadPoolExecutor(max_workers=5) as executor:
                    future_to_term = {executor.submit(create_term_wrapper, term_info): term_info for term_info in terms_to_create}
                    
                    for future in as_completed(future_to_term):
                        result = future.result()
                        with lock:
                            if result["success"]:
                                print(f"  [OK] Created term: {result['term_name']}")
                                summary["terms_created"] += 1
                            else:
                                error_msg = f"Failed to create term '{result['term_name']}': {result['error']}"
                                print(f"  [ERROR] {error_msg}")
                                summary["errors"].append(error_msg)
        
        # Set success
        summary["success"] = True
        if dry_run:
            summary["message"] = f"Dry run completed. Would create {summary['glossaries_created']} glossaries and {summary['terms_created']} terms."
        else:
            summary["message"] = f"Sync completed. Created {summary['glossaries_created']} glossaries and {summary['terms_created']} terms."
        
    except Exception as e:
        summary["success"] = False
        summary["message"] = f"Sync failed: {str(e)}"
        summary["errors"].append(str(e))
    
    return summary


if __name__ == "__main__":
    print("Business Glossary Sync Tool")
    print("="*80)
    
    # Run a dry run first to see what would be created
    print("\n--- DRY RUN MODE ---\n")
    dry_run_result = sync_glossary_from_unified_catalog(dry_run=True)
    
    print("\n" + "="*80)
    print("DRY RUN SUMMARY")
    print("="*80)
    print(json.dumps(dry_run_result, indent=2))
    
    # Ask user if they want to proceed
    print("\n" + "="*80)
    response = input("\nDo you want to proceed with the actual sync? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        print("\n--- LIVE SYNC MODE ---\n")
        result = sync_glossary_from_unified_catalog(dry_run=False)
        
        print("\n" + "="*80)
        print("SYNC SUMMARY")
        print("="*80)
        print(json.dumps(result, indent=2))
    else:
        print("\nSync cancelled by user.")
