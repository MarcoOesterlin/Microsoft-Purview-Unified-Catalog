"""
Flask API Server for Purview Data Catalog
Serves data from get_data.py to the React frontend
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import get_data
import get_data_product
import get_entra_id_users
import sync_glossary
import pandas as pd
import json
import os
import asyncio
import requests

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for React dev server

# Cache the data
cached_data = None
cached_data_products = None
cached_user_mapping = None

# Load Entra ID user mapping
def load_user_mapping():
    """Load user ID to display name mapping from Entra ID"""
    global cached_user_mapping
    if cached_user_mapping is None:
        try:
            print("Loading Entra ID users...")
            credential = get_entra_id_users.get_graph_client()
            # Run async function in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            users_df = loop.run_until_complete(get_entra_id_users.get_entraid_users(credential))
            loop.close()
            
            # Create dictionary mapping id to displayName
            cached_user_mapping = dict(zip(users_df['id'], users_df['displayName']))
            print(f"Loaded {len(cached_user_mapping)} Entra ID users")
        except Exception as e:
            print(f"Warning: Could not load Entra ID users: {e}")
            cached_user_mapping = {}
    return cached_user_mapping

# Load collection mapping
def load_collection_mapping():
    """Load collection ID to name mapping from Purview API"""
    try:
        print("Fetching collection mappings from Purview API...")
        purview_config = get_data.PurviewConfig()
        purview_client = get_data.PurviewSearchClient(purview_config)
        mapping = purview_client.get_collections_with_names()
        print(f"Loaded {len(mapping)} collection mappings from API")
        return mapping
    except Exception as e:
        print(f"Warning: Could not load collection mapping from API: {e}")
        return {}

collection_mapping = load_collection_mapping()
user_mapping = load_user_mapping()

@app.route('/', methods=['GET'])
def index():
    """Root endpoint with API information"""
    return jsonify({
        'message': 'Purview Data Catalog API',
        'version': '1.0',
        'endpoints': {
            'health': '/api/health',
            'assets': '/api/assets',
            'stats': '/api/stats',
            'collections': '/api/collections',
            'data-products': '/api/data-products',
            'refresh': '/api/refresh (POST)'
        },
        'status': 'running'
    })

def get_purview_data():
    """Fetch and cache Purview data"""
    global cached_data
    if cached_data is None:
        print("Fetching data from Purview...")
        df = get_data.main()
        if df is not None and not df.empty:
            cached_data = df
        else:
            print("Warning: No data returned from Purview")
            cached_data = pd.DataFrame()
    return cached_data

def get_purview_data_products():
    """Fetch and cache Purview data products"""
    global cached_data_products
    if cached_data_products is None:
        print("Fetching data products from Purview...")
        try:
            products = get_data_product.list_all_data_products()
            cached_data_products = products if products else []
        except Exception as e:
            print(f"Warning: Error fetching data products: {e}")
            cached_data_products = []
    return cached_data_products

def dataframe_to_json_records(df):
    """Convert DataFrame to JSON-serializable records"""
    if df is None or df.empty:
        return []
    
    # Convert DataFrame to dict records
    records = df.to_dict('records')
    
    # Clean up records
    for record in records:
        for key, value in record.items():
            if pd.isna(value):
                record[key] = None
            # Handle assetType - extract first element from list or parse string representation
            elif key == 'assetType':
                if isinstance(value, list) and len(value) > 0:
                    record[key] = value[0]
                elif isinstance(value, str):
                    # Parse string representation like "['Azure SQL Database']"
                    if value.startswith('[') and value.endswith(']'):
                        try:
                            import ast
                            parsed = ast.literal_eval(value)
                            if isinstance(parsed, list) and len(parsed) > 0:
                                record[key] = parsed[0]
                        except:
                            record[key] = value
            # Handle tags and classifications - parse string representations to arrays
            elif key in ['tag', 'classification', 'contact']:
                if isinstance(value, str) and value.startswith('[') and value.endswith(']'):
                    try:
                        import ast
                        parsed = ast.literal_eval(value)
                        if isinstance(parsed, list):
                            record[key] = parsed
                    except:
                        pass  # Keep original value if parsing fails
        
        # Refine Azure Blob Storage to be more specific based on qualifiedName URL
        if record.get('assetType') == 'Azure Blob Storage' and record.get('qualifiedName'):
            qname_val = record['qualifiedName']
            if pd.notna(qname_val):
                qualified_name = str(qname_val).lower()
                # Check URL patterns to determine specific type
                if '.blob.core.windows.net/' in qualified_name:
                    # Count path segments after the domain
                    path_part = qualified_name.split('.blob.core.windows.net/')[-1]
                    path_segments = [seg for seg in path_part.split('/') if seg]
                    
                    if len(path_segments) > 1:
                        # Multiple segments = Asset/File inside container - detect file type
                        file_name = path_segments[-1]
                        if '.' in file_name:
                            extension = file_name.split('.')[-1].upper()
                            record['assetType'] = f'{extension} File'
                        else:
                            record['assetType'] = 'Azure Blob'
                    elif len(path_segments) == 1:
                        # Single segment = Container
                        record['assetType'] = 'Azure Blob Container'
                elif '.core.windows.net' in qualified_name and '.blob.' not in qualified_name:
                    # Core endpoint without blob subdomain = Storage Account
                    record['assetType'] = 'Azure Storage Account'
        
        # Map collection ID to collection name if available
        if 'collectionId' in record and record['collectionId'] in collection_mapping:
            record['collectionName'] = collection_mapping[record['collectionId']]
        
        # Extract owner and expert from contact field and replace IDs with display names
        if 'contact' in record and record['contact']:
            contacts = record['contact']
            if isinstance(contacts, list):
                for contact in contacts:
                    if isinstance(contact, dict):
                        contact_type_val = contact.get('contactType', '')
                        contact_type = str(contact_type_val).lower() if pd.notna(contact_type_val) else ''
                        contact_id = contact.get('id')
                        
                        if contact_id:
                            # Resolve ID to display name
                            display_name = user_mapping.get(contact_id, contact_id)
                            print(f"DEBUG: Resolving contact {contact_type}: {contact_id} -> {display_name}")
                            
                            # Set owner or expert field
                            if contact_type == 'owner':
                                record['owner'] = display_name
                            elif contact_type == 'expert':
                                record['expert'] = display_name
        
        # Also handle standalone owner/expert fields (in case they exist)
        for field in ['owner', 'expert']:
            if field in record and record[field] and isinstance(record[field], str):
                # Skip special values like $superuser
                if not record[field].startswith('$'):
                    # Check if it's a GUID (Entra ID object ID)
                    if record[field] in user_mapping:
                        record[field] = user_mapping[record[field]]
    
    return records

@app.route('/api/assets', methods=['GET'])
def get_assets():
    """Get all Purview assets"""
    try:
        df = get_purview_data()
        assets = dataframe_to_json_records(df)
        
        return jsonify({
            'success': True,
            'data': assets,
            'count': len(assets)
        })
    except Exception as e:
        print(f"Error in /api/assets: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        }), 500

@app.route('/api/collections', methods=['GET'])
def get_collections():
    """Get all available collections from mapping"""
    try:
        collections = [{'id': cid, 'name': name} for cid, name in collection_mapping.items()]
        return jsonify({
            'success': True,
            'data': collections,
            'count': len(collections)
        })
    except Exception as e:
        print(f"Error in /api/collections: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        }), 500

@app.route('/api/data-products', methods=['GET'])
def get_data_products():
    """Get all Purview data products"""
    try:
        products = get_purview_data_products()
        return jsonify({
            'success': True,
            'data': products,
            'count': len(products)
        })
    except Exception as e:
        print(f"Error in /api/data-products: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        }), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get statistics about the catalog"""
    try:
        df = get_purview_data()
        
        if df is None or df.empty:
            return jsonify({
                'success': True,
                'data': {
                    'totalAssets': 0,
                    'assetTypes': {},
                    'entityTypes': {},
                    'withTags': 0,
                    'withClassification': 0
                }
            })
        
        stats = {
            'totalAssets': len(df),
            'assetTypes': df['assetType'].value_counts().to_dict() if 'assetType' in df.columns else {},
            'entityTypes': df['entityType'].value_counts().to_dict() if 'entityType' in df.columns else {},
            'withTags': int(df['tag'].notna().sum()) if 'tag' in df.columns else 0,
            'withClassification': int(df['classification'].notna().sum()) if 'classification' in df.columns else 0
        }
        
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        print(f"Error in /api/stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    """Force refresh of Purview data and data products"""
    global cached_data, cached_data_products, collection_mapping
    try:
        # Clear caches
        cached_data = None
        cached_data_products = None
        
        # Refresh collection mappings from API
        print("Refreshing collection mappings from API...")
        collection_mapping = load_collection_mapping()
        
        # Refresh data
        df = get_purview_data()
        products = get_purview_data_products()
        
        return jsonify({
            'success': True,
            'message': 'Data refreshed successfully',
            'assetsCount': len(df) if df is not None else 0,
            'productsCount': len(products)
        })
    except Exception as e:
        print(f"Error in /api/refresh: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'success': True,
        'status': 'healthy',
        'message': 'API server is running'
    })

@app.route('/api/curate/add-tags', methods=['POST'])
def add_tags_to_assets():
    """Add tags to multiple assets"""
    from flask import request
    import add_tag
    
    try:
        data = request.get_json()
        guids = data.get('guids', [])
        tag = data.get('tag', '')
        
        if not guids or not tag:
            return jsonify({
                'success': False,
                'error': 'Missing guids or tag'
            }), 400
        
        # Call add_tag.main with the guids and tag
        add_tag.main(guids, tag)
        
        return jsonify({
            'success': True,
            'message': f'Tag "{tag}" added to {len(guids)} asset(s)',
            'guids': guids,
            'tag': tag
        })
    except Exception as e:
        print(f"Error adding tags: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/curate/remove-tags', methods=['POST'])
def remove_tags_from_assets():
    """Remove tags from multiple assets"""
    from flask import request
    import delete_tag
    
    try:
        data = request.get_json()
        guids = data.get('guids', [])
        tag = data.get('tag', '')
        
        if not guids or not tag:
            return jsonify({
                'success': False,
                'error': 'Missing guids or tag'
            }), 400
        
        # Call delete_tag.main with the guids and tag
        delete_tag.main(guids, tag)
        
        return jsonify({
            'success': True,
            'message': f'Tag "{tag}" removed from {len(guids)} asset(s)',
            'guids': guids,
            'tag': tag
        })
    except Exception as e:
        print(f"Error removing tags: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/curate/get-tags', methods=['POST'])
def get_tags_from_assets():
    """Get all tags from selected assets"""
    from flask import request
    import requests as req
    
    try:
        data = request.get_json()
        guids = data.get('guids', [])
        
        if not guids:
            return jsonify({
                'success': False,
                'error': 'Missing guids'
            }), 400
        
        # Get access token
        from add_tag import get_access_token, tenant_id, client_id, client_secret, purview_endpoint
        access_token = get_access_token(tenant_id, client_id, client_secret)
        
        all_tags = set()
        
        # Fetch labels for each GUID
        for guid in guids:
            url = f"{purview_endpoint}/datamap/api/atlas/v2/entity/guid/{guid}"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = req.get(url, headers=headers)
            
            if response.status_code == 200:
                entity_data = response.json()
                # Extract labels (tags) from the entity
                labels = entity_data.get('entity', {}).get('labels', [])
                if labels:
                    all_tags.update(labels)
        
        return jsonify({
            'success': True,
            'tags': sorted(list(all_tags))
        })
    except Exception as e:
        print(f"Error getting tags: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/curate/add-owner', methods=['POST'])
def add_owner_to_assets():
    """Add owner or expert to selected assets"""
    from flask import request
    import add_owner
    import delete_owner
    
    try:
        data = request.get_json()
        guids = data.get('guids', [])
        contact_type = data.get('contactType')  # "Owner" or "Expert"
        user_id = data.get('userId')
        notes = data.get('notes', '')
        remove_existing = data.get('removeExisting', False)
        
        if not guids or not contact_type or not user_id:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: guids, contactType, or userId'
            }), 400
        
        # If removeExisting is True, first remove any existing owner/expert
        if remove_existing:
            print(f"[INFO] Removing existing {contact_type} from {len(guids)} asset(s) before adding new one...")
            delete_owner.main(guids, contact_type)
        
        # Add owner/expert to each asset
        for guid in guids:
            add_owner.main(
                contact=contact_type,
                guid=guid,
                id=user_id,
                notes=notes,
                type_name=None
            )
        
        return jsonify({
            'success': True,
            'message': f'{contact_type} added to {len(guids)} asset(s)'
        })
    except Exception as e:
        print(f"Error adding {contact_type}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/curate/remove-owner', methods=['POST'])
def remove_owner_from_assets():
    """Remove owner or expert from selected assets"""
    from flask import request
    import delete_owner
    
    try:
        data = request.get_json()
        guids = data.get('guids', [])
        contact_type = data.get('contactType')  # "Owner" or "Expert"
        
        if not guids or not contact_type:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: guids or contactType'
            }), 400
        
        # Remove owner/expert from assets
        success = delete_owner.main(guids, contact_type)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'{contact_type} removed from {len(guids)} asset(s)'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Failed to remove {contact_type}'
            }), 500
    except Exception as e:
        print(f"Error removing {contact_type}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/curate/get-contacts', methods=['POST'])
def get_contacts_from_assets():
    """Get all owners and experts from selected assets"""
    from flask import request
    import requests as req
    
    try:
        data = request.get_json()
        guids = data.get('guids', [])
        
        if not guids:
            return jsonify({
                'success': False,
                'error': 'Missing guids'
            }), 400
        
        # Get access token
        from add_tag import get_access_token, tenant_id, client_id, client_secret, purview_endpoint
        access_token = get_access_token(tenant_id, client_id, client_secret)
        
        owners = {}
        experts = {}
        user_mapping = load_user_mapping()
        
        # Fetch contacts for each GUID
        for guid in guids:
            url = f"{purview_endpoint}/datamap/api/atlas/v2/entity/guid/{guid}"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = req.get(url, headers=headers)
            
            if response.status_code == 200:
                entity_data = response.json()
                print(f"DEBUG: Entity data for {guid}:")
                print(f"  Keys: {entity_data.keys()}")
                contacts = entity_data.get('entity', {}).get('contacts', {})
                print(f"  Contacts: {contacts}")
                
                # Extract owner
                if 'Owner' in contacts and len(contacts['Owner']) > 0:
                    owner_id = contacts['Owner'][0].get('id')
                    if owner_id:
                        display_name = user_mapping.get(owner_id, owner_id)
                        owners[owner_id] = display_name
                        print(f"  Found owner: {owner_id} -> {display_name}")
                
                # Extract expert
                if 'Expert' in contacts and len(contacts['Expert']) > 0:
                    expert_id = contacts['Expert'][0].get('id')
                    if expert_id:
                        display_name = user_mapping.get(expert_id, expert_id)
                        experts[expert_id] = display_name
                        print(f"  Found expert: {expert_id} -> {display_name}")
            else:
                print(f"ERROR: Failed to get entity {guid}, status: {response.status_code}")
                print(f"  Response: {response.text}")
        
        return jsonify({
            'success': True,
            'owners': [{'id': uid, 'displayName': name} for uid, name in owners.items()],
            'experts': [{'id': uid, 'displayName': name} for uid, name in experts.items()]
        })
    except Exception as e:
        print(f"Error getting contacts: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/users', methods=['GET'])
def get_users():
    """Get Entra ID users for owner/expert selection"""
    try:
        user_mapping = load_user_mapping()
        
        # Convert to list format for frontend
        users = [
            {'id': user_id, 'displayName': display_name}
            for user_id, display_name in user_mapping.items()
        ]
        
        return jsonify({
            'success': True,
            'users': users
        })
    except Exception as e:
        print(f"Error getting users: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/classifications', methods=['GET'])
def get_classifications():
    """Get all available classifications from Purview"""
    try:
        import add_classificiation
        
        # Get access token
        access_token = add_classificiation.get_access_token(
            add_classificiation.tenant_id,
            add_classificiation.client_id,
            add_classificiation.client_secret
        )
        
        # Fetch classifications from Purview
        url = f"{add_classificiation.purview_endpoint}/catalog/api/atlas/v2/types/typedefs?type=classification&api-version=2022-03-01-preview"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            classification_defs = data.get('classificationDefs', [])
            
            # Extract classification names
            classifications = [
                {
                    'name': c.get('name'),
                    'description': c.get('description', ''),
                    'category': c.get('category', '')
                }
                for c in classification_defs
            ]
            
            # Sort by name
            classifications.sort(key=lambda x: x['name'])
            
            return jsonify({
                'success': True,
                'classifications': classifications
            })
        else:
            raise Exception(f"Failed to fetch classifications: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Error fetching classifications: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/curate/add-classifications', methods=['POST'])
def add_classifications():
    """Add classifications to multiple assets"""
    try:
        data = request.get_json()
        guids = data.get('guids', [])
        classification_names = data.get('classifications', [])
        
        if not guids:
            return jsonify({
                'success': False,
                'error': 'No GUIDs provided'
            }), 400
            
        if not classification_names:
            return jsonify({
                'success': False,
                'error': 'No classifications provided'
            }), 400
        
        print(f"Adding classifications {classification_names} to {len(guids)} assets")
        
        import add_classificiation
        
        # Call the add_classification function
        add_classificiation.main(guids, classification_names)
        
        return jsonify({
            'success': True,
            'message': f'Successfully added {len(classification_names)} classification(s) to {len(guids)} asset(s)'
        })
        
    except Exception as e:
        print(f"Error adding classifications: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/curate/remove-classifications', methods=['POST'])
def remove_classifications():
    """Remove classifications from multiple assets"""
    try:
        data = request.get_json()
        guids = data.get('guids', [])
        classification_names = data.get('classifications', [])
        
        if not guids:
            return jsonify({
                'success': False,
                'error': 'No GUIDs provided'
            }), 400
            
        if not classification_names:
            return jsonify({
                'success': False,
                'error': 'No classifications provided'
            }), 400
        
        print(f"Removing classifications {classification_names} from {len(guids)} assets")
        
        import delete_classification
        
        # Call the remove_classification function
        delete_classification.main(guids, classification_names)
        
        return jsonify({
            'success': True,
            'message': f'Successfully removed {len(classification_names)} classification(s) from {len(guids)} asset(s)'
        })
        
    except Exception as e:
        print(f"Error removing classifications: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/curate/get-classifications', methods=['POST'])
def get_asset_classifications():
    """Get all classifications on selected assets (both asset-level and schema/column-level)"""
    try:
        data = request.get_json()
        guids = data.get('guids', [])
        
        if not guids:
            return jsonify({
                'success': False,
                'error': 'No GUIDs provided'
            }), 400
        
        print(f"Fetching classifications for {len(guids)} assets (including schema)")
        
        import add_classificiation
        import auto_classify
        
        # Get access token
        access_token = add_classificiation.get_access_token(
            add_classificiation.tenant_id,
            add_classificiation.client_id,
            add_classificiation.client_secret
        )
        
        # Map each GUID to its classifications
        asset_classifications = {}
        
        for guid in guids:
            all_classifications = set()
            
            try:
                # Get schema using SDK (more efficient)
                entity_response = auto_classify.get_entity_schema_with_sdk(guid)
                
                if entity_response and entity_response.get('entity'):
                    entity = entity_response['entity']
                    
                    # Get asset-level classifications
                    classifications = entity.get('classifications', [])
                    for classification in classifications:
                        classification_name = classification.get('typeName')
                        if classification_name:
                            all_classifications.add(classification_name)
                    
                    # Get schema/column-level classifications
                    if entity_response.get('columns'):
                        columns = entity_response['columns']
                        print(f"  Checking {len(columns)} columns for classifications on asset {guid}")
                        
                        # For each column, fetch its classifications
                        headers = {
                            'Authorization': f'Bearer {access_token}',
                            'Content-Type': 'application/json'
                        }
                        
                        for col_ref in columns:
                            if isinstance(col_ref, dict):
                                column_guid = col_ref.get('guid')
                                if column_guid:
                                    try:
                                        # Get column entity details
                                        col_url = f"{add_classificiation.purview_endpoint}/datamap/api/atlas/v2/entity/guid/{column_guid}?api-version=2023-09-01"
                                        col_response = requests.get(col_url, headers=headers, timeout=5)
                                        
                                        if col_response.status_code == 200:
                                            col_entity_data = col_response.json()
                                            col_entity = col_entity_data.get('entity', {})
                                            col_classifications = col_entity.get('classifications', [])
                                            
                                            for col_classification in col_classifications:
                                                col_classification_name = col_classification.get('typeName')
                                                if col_classification_name:
                                                    all_classifications.add(col_classification_name)
                                    except Exception as col_error:
                                        print(f"  Warning: Could not fetch classifications for column {column_guid}: {col_error}")
                                        continue
                    
                    asset_classifications[guid] = sorted(list(all_classifications))
                    print(f"  Asset {guid}: Found {len(all_classifications)} total classifications")
                else:
                    asset_classifications[guid] = []
            except Exception as asset_error:
                print(f"  Error processing asset {guid}: {asset_error}")
                asset_classifications[guid] = []
        
        print(f"Fetched classifications for {len(asset_classifications)} assets")
        
        return jsonify({
            'success': True,
            'classifications': asset_classifications
        })
        
    except Exception as e:
        print(f"Error fetching asset classifications: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/curate/auto-classify', methods=['POST'])
def auto_classify_assets():
    """Automatically suggest and apply classifications based on column names and patterns"""
    try:
        data = request.get_json()
        guids = data.get('guids', [])
        apply_suggestions = data.get('apply', False)  # Whether to automatically apply suggestions
        
        if not guids:
            return jsonify({
                'success': False,
                'error': 'No GUIDs provided'
            }), 400
        
        import auto_classify
        
        # Get classification suggestions (now returns column-level or asset-level data)
        # Format: {"entity_guid": {"has_schema": bool, "classifications": {...}, "schema": [...], "asset_classifications": [...]}}
        suggestions = auto_classify.main(guids, apply=apply_suggestions)
        
        # Count total columns, assets, and classifications
        total_columns = 0
        total_classifications = 0
        total_assets_with_suggestions = 0
        
        for entity_guid, entity_data in suggestions.items():
            if entity_data.get('has_schema'):
                # Has columns
                column_data = entity_data.get('classifications', {})
                total_columns += len(column_data)
                for column_info in column_data.values():
                    total_classifications += len(column_info.get('classifications', []))
            else:
                # No schema, asset-level classifications
                asset_classifications = entity_data.get('asset_classifications', [])
                if asset_classifications:
                    total_assets_with_suggestions += 1
                    total_classifications += len(asset_classifications)
        
        # Format response
        result = {
            'success': True,
            'suggestions': suggestions,
            'applied': apply_suggestions,
            'total_columns': total_columns,
            'total_assets': total_assets_with_suggestions,
            'total_classifications': total_classifications
        }
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in auto-classification: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/curate/get-schema', methods=['POST'])
def get_asset_schema():
    """Get the schema (columns) for selected assets with existing classifications"""
    try:
        data = request.get_json()
        guids = data.get('guids', [])
        
        if not guids:
            return jsonify({
                'success': False,
                'error': 'No GUIDs provided'
            }), 400
        
        print(f"Fetching schema for {len(guids)} assets")
        
        import auto_classify
        
        # Get access token
        access_token = auto_classify.get_access_token(
            auto_classify.tenant_id, auto_classify.client_id, auto_classify.client_secret
        )
        
        # Get schema info for each asset
        schema_data = {}
        for guid in guids:
            # Get base schema info
            entity_info = auto_classify.auto_classify_entity(
                auto_classify.purview_endpoint, guid, access_token
            )
            
            # Add existing classifications for each column
            if entity_info.get('has_schema') and entity_info.get('schema'):
                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                }
                
                print(f"Fetching existing classifications for {len(entity_info['schema'])} columns")
                
                for column in entity_info['schema']:
                    column_guid = column.get('guid')
                    column_name = column.get('name', 'unknown')
                    if column_guid:
                        try:
                            # Fetch existing classifications for this column
                            col_url = f"{auto_classify.purview_endpoint}/datamap/api/atlas/v2/entity/guid/{column_guid}?api-version=2023-09-01"
                            col_response = requests.get(col_url, headers=headers, timeout=5)
                            
                            if col_response.status_code == 200:
                                col_entity_data = col_response.json()
                                col_entity = col_entity_data.get('entity', {})
                                col_classifications = col_entity.get('classifications', [])
                                
                                # Add existing classifications to column info
                                existing_classifications = [c.get('typeName') for c in col_classifications if c.get('typeName')]
                                column['existing_classifications'] = existing_classifications
                                
                                if existing_classifications:
                                    print(f"  [OK] Column '{column_name}' ({column_guid}): {existing_classifications}")
                                else:
                                    print(f"  - Column '{column_name}' ({column_guid}): No classifications")
                            else:
                                print(f"   Column '{column_name}': API returned {col_response.status_code}")
                                column['existing_classifications'] = []
                        except Exception as col_error:
                            print(f"  Warning: Could not fetch classifications for column {column_name} ({column_guid}): {col_error}")
                            column['existing_classifications'] = []
                    else:
                        print(f"  Warning: Column '{column_name}' has no GUID")
            else:
                print(f"Entity {guid}: No schema or has_schema=False")
            
            schema_data[guid] = entity_info
        
        return jsonify({
            'success': True,
            'schema_data': schema_data
        })
        
    except Exception as e:
        print(f"Error fetching schema: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/curate/classify-columns', methods=['POST'])
def classify_columns():
    """Apply classifications to specific columns"""
    try:
        data = request.get_json()
        column_classifications = data.get('column_classifications', {})
        # Format: {"column_guid": ["CLASSIFICATION1", "CLASSIFICATION2"]}
        
        if not column_classifications:
            return jsonify({
                'success': False,
                'error': 'No column classifications provided'
            }), 400
        
        print(f"Applying classifications to {len(column_classifications)} columns")
        
        import auto_classify
        access_token = auto_classify.get_access_token(
            auto_classify.tenant_id, auto_classify.client_id, auto_classify.client_secret
        )
        
        # Apply classifications to each column
        for column_guid, classifications in column_classifications.items():
            auto_classify.apply_column_classifications_sync(
                auto_classify.purview_endpoint, column_guid, classifications, access_token
            )
        
        return jsonify({
            'success': True,
            'message': f'Applied classifications to {len(column_classifications)} column(s)'
        })
        
    except Exception as e:
        print(f"Error classifying columns: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/lineage/workspaces', methods=['GET'])
def get_workspaces():
    """Get list of unique Fabric workspaces from Purview assets"""
    try:
        df = get_purview_data()
        
        if df is None or df.empty:
            return jsonify({
                'success': True,
                'workspaces': []
            })
        
        print(f"\n[DEBUG] Searching for Fabric workspaces in {len(df)} assets...")
        
        # Extract workspace info from Fabric assets
        # Only include assets with URLs that don't go deeper than groups/{workspace_id}/
        # Example: https://app.powerbi.com/groups/{workspace_id}
        workspaces = {}
        
        for idx, row in df.iterrows():
            qname_val = row.get('qualifiedName', '')
            # Handle NaN values which come as floats from pandas
            qualified_name = str(qname_val) if pd.notna(qname_val) else ''
            
            # Check if this is a workspace-level asset (URL ends at groups/{workspace_id})
            if 'groups/' in qualified_name:
                # Split on 'groups/' and get workspace ID
                parts = qualified_name.split('groups/')
                if len(parts) >= 2:
                    after_groups = parts[1].rstrip('/')  # Remove trailing slash
                    
                    # Check if it's just the workspace ID (no additional path segments)
                    if '/' not in after_groups:
                        workspace_id = after_groups
                        
                        # Validate it's a GUID format
                        if len(workspace_id) == 36 and workspace_id.count('-') == 4:
                            if workspace_id not in workspaces:
                                workspace_name = row.get('name', '') or row.get('displayName', '') or f"Workspace {workspace_id[:8]}"
                                print(f"  [OK] Found workspace: {workspace_name} ({workspace_id})")
                                print(f"    Qualified Name: {qualified_name}")
                                workspaces[workspace_id] = {
                                    'workspace_id': workspace_id,
                                    'workspace_name': workspace_name,
                                    'asset_count': 0
                                }
        
        print(f"\n[STATS] Found {len(workspaces)} workspace(s)")
        
        # Count all lineage-relevant assets per workspace
        # Include tables, lakehouses, notebooks, datasets, warehouses, dataflows, pipelines, etc.
        # Exclude columns, fields, folders, files, and metadata entities
        for _, row in df.iterrows():
            qname_val = row.get('qualifiedName', '')
            # Handle NaN values which come as floats from pandas
            qualified_name = str(qname_val) if pd.notna(qname_val) else ''
            entity_type_val = row.get('entityType', '')
            asset_type = str(entity_type_val).lower() if pd.notna(entity_type_val) else ''
            
            # Skip non-data entities
            skip_types = ['column', 'field', 'folder', 'file', 'meta', 'function']
            if any(skip_type in asset_type for skip_type in skip_types):
                continue
            
            if 'groups/' in qualified_name:
                parts = qualified_name.split('groups/')
                if len(parts) >= 2:
                    workspace_parts = parts[1].split('/')
                    if len(workspace_parts) > 0:
                        workspace_id = workspace_parts[0]
                        if workspace_id in workspaces:
                            workspaces[workspace_id]['asset_count'] += 1
        
        result_list = list(workspaces.values())
        print(f"[OK] Returning {len(result_list)} workspace(s) with asset counts")
        for ws in result_list:
            print(f"   - {ws['workspace_name']}: {ws['asset_count']} assets")
        
        return jsonify({
            'success': True,
            'workspaces': result_list
        })
        
    except Exception as e:
        print(f"[ERROR] Error getting workspaces: {e}")
        import traceback
        error_trace = traceback.format_exc()
        print(error_trace)
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': error_trace  
        }), 500

@app.route('/api/lineage/discover', methods=['POST'])
def discover_lineage():
    """Discover lineage for a Fabric workspace using Foundry agent"""
    try:
        data = request.get_json()
        workspace_id = data.get('workspace_id')
        workspace_name = data.get('workspace_name', '')
        asset_guid = data.get('asset_guid')  # Optional: specific asset to analyze
        
        if not workspace_id:
            return jsonify({
                'success': False,
                'error': 'workspace_id is required'
            }), 400
        
        print(f"Discovering lineage for workspace: {workspace_name} ({workspace_id})")
        
        import create_lineage
        
        # If specific asset provided, discover from that asset
        if asset_guid:
            result = create_lineage.discover_fabric_lineage(asset_guid)
        else:
            # Discover from workspace level - fetch all workspace assets first
            workspace_assets = create_lineage.get_workspace_assets_from_purview(workspace_id)
            
            if not workspace_assets:
                return jsonify({
                    'success': False,
                    'error': 'Could not fetch workspace assets from Purview'
                }), 500
            
            # Build comprehensive workspace info with all assets
            workspace_info = {
                'workspace_id': workspace_id,
                'workspace_name': workspace_name,
                'lakehouses': workspace_assets.get('lakehouses', []),
                'tables': workspace_assets.get('tables', []),
                'notebooks': workspace_assets.get('notebooks', [])
            }
            
            if create_lineage.use_fabric_agent:
                lineage_data = create_lineage.analyze_lineage_with_fabric_agent(workspace_info)
                
                # Debug: print what was returned
                print(f"\n[DEBUG] Lineage data returned from agent:")
                print(f"  Type: {type(lineage_data)}")
                print(f"  Keys: {lineage_data.keys() if lineage_data else 'None'}")
                if lineage_data:
                    print(f"  lineage_mappings: {len(lineage_data.get('lineage_mappings', []))} mappings")
                
                # Check if lineage was found
                if lineage_data and lineage_data.get('lineage_mappings'):
                    result = {
                        'success': True,
                        'mode': 'ai_discovered',
                        'workspace_info': workspace_info,
                        'lineage': lineage_data
                    }
                    print(f"[DEBUG] Returning success=True with {len(lineage_data['lineage_mappings'])} mappings")
                else:
                    # No lineage found
                    message = lineage_data.get('message') if lineage_data else 'No lineage relationships could be discovered'
                    result = {
                        'success': False,
                        'mode': 'ai_discovered',
                        'workspace_info': workspace_info,
                        'lineage': lineage_data or {'lineage_mappings': []},
                        'message': message,
                        'hint': 'The AI agent could not identify clear data flow relationships. You may need to create lineage manually or ensure your workspace has typical ETL patterns (source files/tables -> target tables).'
                    }
                    print(f"[DEBUG] Returning success=False - no mappings found")
            else:
                result = {
                    'success': False,
                    'error': 'Fabric Agent not enabled'
                }
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error discovering lineage: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/lineage/workspace-assets', methods=['POST'])
def get_workspace_assets():
    """Get workspace assets without lineage discovery (for description tab)"""
    try:
        data = request.get_json()
        workspace_id = data.get('workspace_id')
        workspace_name = data.get('workspace_name', '')
        
        if not workspace_id:
            return jsonify({
                'success': False,
                'error': 'workspace_id is required'
            }), 400
        
        print(f"Loading workspace assets for: {workspace_name} ({workspace_id})")
        
        import create_lineage
        
        # Fetch all workspace assets from Purview
        workspace_assets = create_lineage.get_workspace_assets_from_purview(workspace_id)
        
        if not workspace_assets:
            return jsonify({
                'success': False,
                'error': 'Could not fetch workspace assets from Purview'
            }), 500
        
        # Build comprehensive workspace info with all assets
        workspace_info = {
            'workspace_id': workspace_id,
            'workspace_name': workspace_name,
            'lakehouses': workspace_assets.get('lakehouses', []),
            'warehouses': workspace_assets.get('warehouses', []),
            'tables': workspace_assets.get('tables', []),
            'files': workspace_assets.get('files', []),
            'dataflows': workspace_assets.get('dataflows', []),
            'pipelines': workspace_assets.get('pipelines', []),
            'notebooks': workspace_assets.get('notebooks', []),
            'other_assets': workspace_assets.get('other_assets', []),
            'total_assets': (
                len(workspace_assets.get('lakehouses', [])) +
                len(workspace_assets.get('warehouses', [])) +
                len(workspace_assets.get('tables', [])) +
                len(workspace_assets.get('files', [])) +
                len(workspace_assets.get('dataflows', [])) +
                len(workspace_assets.get('pipelines', [])) +
                len(workspace_assets.get('notebooks', [])) +
                len(workspace_assets.get('other_assets', []))
            )
        }
        
        return jsonify({
            'success': True,
            'workspace_info': workspace_info
        })
        
    except Exception as e:
        print(f"Error loading workspace assets: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/lineage/create', methods=['POST'])
def create_lineage_endpoint():
    """Create lineage relationships in Purview"""
    try:
        data = request.get_json()
        lineage_mappings = data.get('lineage_mappings', [])
        # Format: [{"source_guid": "...", "target_guid": "...", "process_name": "...", "column_mappings": [...]}]
        
        if not lineage_mappings:
            return jsonify({
                'success': False,
                'error': 'No lineage mappings provided'
            }), 400
        
        print(f"Creating {len(lineage_mappings)} lineage relationship(s)")
        
        import create_lineage
        
        results = []
        for mapping in lineage_mappings:
            # Support both field name formats: source_guid or source_table_guid
            source_guid = mapping.get('source_table_guid') if 'source_table_guid' in mapping else mapping.get('source_guid')
            target_guid = mapping.get('target_table_guid') if 'target_table_guid' in mapping else mapping.get('target_guid')
            process_name = mapping.get('process_name', 'Data Flow')
            
            # Transform column mappings from AI agent format to Purview format
            # From: [{"source_column":"col1","target_column":"col1"}]
            # To: [{"Source":"col1","Sink":"col1"}]
            column_mappings = mapping.get('column_mappings')
            print(f"\n[DEBUG] DEBUG - Raw column_mappings from request: {column_mappings}")
            print(f"[DEBUG] DEBUG - Type: {type(column_mappings)}")
            
            if column_mappings:
                # Transform column mappings - INCLUDE empty source/target for dummy column creation
                column_mappings = [
                    {"Source": cm.get("source_column", ""), "Sink": cm.get("target_column", "")}
                    for cm in column_mappings
                ]
                print(f"[DEBUG] DEBUG - Transformed column_mappings: {column_mappings}")
            
            # Default to direct table-to-table lineage (no process intermediary)
            use_process = mapping.get('use_process', False)
            
            print(f"\n Mapping: {process_name}")
            print(f"    Source: {source_guid}")
            print(f"    Target: {target_guid}")
            print(f"    Columns: {len(column_mappings) if column_mappings else 0} mappings")
            if column_mappings:
                print(f"    Column details: {column_mappings}")
            
            if not source_guid or not target_guid:
                results.append({
                    'success': False,
                    'error': f'source_guid/source_table_guid and target_guid/target_table_guid are required. Got: {list(mapping.keys())}'
                })
                continue
            
            result = create_lineage.create_lineage_for_asset(
                source_guid, 
                target_guid, 
                process_name=process_name,
                column_mappings=column_mappings,
                use_process=use_process
            )
            results.append(result)
        
        success_count = sum(1 for r in results if r.get('success'))
        
        return jsonify({
            'success': success_count > 0,
            'message': f'Created {success_count} of {len(lineage_mappings)} lineage relationship(s)',
            'results': results
        })
        
    except Exception as e:
        print(f"Error creating lineage: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/lineage/delete', methods=['POST'])
def delete_lineage_endpoint():
    """Delete lineage relationships from Purview"""
    try:
        data = request.get_json()
        workspace_id = data.get('workspace_id')
        lineage_mappings = data.get('lineage_mappings', [])
        
        import create_lineage
        
        # If workspace_id is provided, delete ALL processes for that workspace
        if workspace_id:
            print(f"Deleting ALL lineage for workspace: {workspace_id}")
            result = create_lineage.delete_all_workspace_lineage(workspace_id)
            return jsonify(result)
        
        # Otherwise delete specific process GUIDs
        if not lineage_mappings:
            return jsonify({
                'success': False,
                'error': 'No lineage mappings or workspace_id provided'
            }), 400
        
        print(f"Deleting {len(lineage_mappings)} specific lineage relationship(s)")
        
        results = []
        for mapping in lineage_mappings:
            process_guid = mapping.get('process_guid')
            
            if not process_guid:
                results.append({
                    'success': False,
                    'error': 'process_guid is required'
                })
                continue
            
            result = create_lineage.delete_lineage_by_process_guid(process_guid)
            results.append(result)
        
        success_count = sum(1 for r in results if r.get('success'))
        
        return jsonify({
            'success': success_count > 0,
            'message': f'Deleted {success_count} of {len(lineage_mappings)} lineage relationship(s)',
            'results': results
        })
        
    except Exception as e:
        print(f"Error deleting lineage: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/lineage/delete-all-processes', methods=['POST'])
def delete_all_lineage_processes():
    """
    Delete all fabric_lineage_process entities from Purview using Atlas search API.
    
    IMPORTANT: This ONLY deletes Process entities and their relationships.
    It does NOT delete any data assets (tables, lakehouses, notebooks, etc.).
    """
    global cached_data
    
    try:
        import create_lineage
        import sys
        from azure.purview.datamap import DataMapClient
        
        print("[DELETE] Deleting ALL fabric_lineage_process entities (data assets safe)...", flush=True)
        sys.stdout.flush()
        
        # Use Atlas search API to find all process entities directly
        credential = create_lineage.get_credentials()
        client = DataMapClient(endpoint=create_lineage.purview_endpoint, credential=credential)
        
        print("[DEBUG] Searching for all entities with qualifiedName starting with 'fabric_lineage_process://'", flush=True)
        sys.stdout.flush()
        
        # Search for process entities using query
        search_request = {
            "keywords": "*",
            "filter": {
                "and": [
                    {
                        "attributeName": "qualifiedName",
                        "operator": "startswith",
                        "attributeValue": "fabric_lineage_process://"
                    }
                ]
            },
            "limit": 1000
        }
        
        process_guids = []
        process_info = []
        
        try:
            search_result = client.discovery.query(search_request=search_request)
            
            if search_result and 'value' in search_result:
                for entity in search_result['value']:
                    guid = entity.get('id')
                    name = entity.get('name', 'Unknown')
                    qname = entity.get('qualifiedName', '')
                    
                    if guid and qname.startswith('fabric_lineage_process://'):
                        process_guids.append(guid)
                        process_info.append({'guid': guid, 'name': name, 'qualifiedName': qname})
                        
        except Exception as search_error:
            print(f"[WARN] Search API error, trying alternative method: {search_error}", flush=True)
            sys.stdout.flush()
            
            # Fallback: Get all entities and filter
            print("[INFO] Fetching all entities from Purview...", flush=True)
            import get_data
            df = get_data.main()
            process_df = df[df['qualifiedName'].str.startswith('fabric_lineage_process://', na=False)]
            
            for _, row in process_df.iterrows():
                guid = row.get('id')
                name = row.get('name', 'Unknown')
                qname = row.get('qualifiedName', '')
                if guid:
                    process_guids.append(guid)
                    process_info.append({'guid': guid, 'name': name, 'qualifiedName': qname})
        
        print(f"[DEBUG] Found {len(process_guids)} fabric_lineage_process entities to delete", flush=True)
        print("[WARN] Only Process entities will be deleted - data assets remain intact", flush=True)
        sys.stdout.flush()
        
        if len(process_guids) == 0:
            return jsonify({
                'success': True,
                'message': 'No fabric_lineage_process entities found',
                'deleted_count': 0
            })
        
        # Show what will be deleted
        print("\n Process entities to delete:", flush=True)
        for info in process_info:
            print(f"  • {info['name']}", flush=True)
            print(f"    GUID: {info['guid']}", flush=True)
            print(f"    QName: {info['qualifiedName']}", flush=True)
        sys.stdout.flush()
        
        # Delete each process
        deleted_count = 0
        failed_count = 0
        
        for info in process_info:
            guid = info['guid']
            name = info['name']
            
            print(f"\n  [DELETE] Deleting: {name}", flush=True)
            print(f"     GUID: {guid}", flush=True)
            sys.stdout.flush()
            
            result = create_lineage.delete_lineage_by_process_guid(guid)
            
            if result.get('success'):
                deleted_count += 1
                print(f"     [OK] Deleted successfully", flush=True)
            else:
                failed_count += 1
                print(f"     [ERROR] Failed: {result.get('error', 'Unknown error')}", flush=True)
            sys.stdout.flush()
        
        print(f"\n[OK] Deletion complete: {deleted_count} deleted, {failed_count} failed", flush=True)
        sys.stdout.flush()
        
        # Clear cache to reflect deletions
        cached_data = None
        print("[INFO] Cache cleared", flush=True)
        sys.stdout.flush()
        
        return jsonify({
            'success': True,
            'message': f'Deleted {deleted_count} fabric_lineage_process entities (data assets safe)',
            'deleted_count': deleted_count,
            'failed_count': failed_count
        })
        
    except Exception as e:
        print(f"[ERROR] Error deleting all processes: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/lineage/test-column-lineage', methods=['POST'])
def test_column_lineage():
    """Test endpoint to create column lineage between two tables"""
    try:
        data = request.get_json()
        source_guid = data.get('source_guid')
        target_guid = data.get('target_guid')
        column_mappings = data.get('column_mappings', [])
        # Format: [{"Source": "col1", "Sink": "col1"}]
        
        if not source_guid or not target_guid:
            return jsonify({
                'success': False,
                'error': 'source_guid and target_guid are required'
            }), 400
        
        print(f"\n TEST: Creating column lineage")
        print(f"   Source: {source_guid}")
        print(f"   Target: {target_guid}")
        print(f"   Column mappings: {column_mappings}")
        
        import create_lineage
        
        result = create_lineage.create_column_lineage(
            source_guid,
            target_guid,
            column_mappings
        )
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error testing column lineage: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/description/generate', methods=['POST'])
def generate_description():
    """Generate AI description for an asset using Azure AI Foundry"""
    try:
        data = request.get_json()
        
        # Extract payload
        asset_name = data.get('asset_name')
        asset_type = data.get('asset_type')
        qualified_name = data.get('qualified_name', '')
        guid = data.get('guid', '')
        lakehouse_tier = data.get('lakehouse_tier', 'Unknown')
        columns = data.get('columns', [])
        
        if not asset_name or not asset_type:
            return jsonify({
                'success': False,
                'error': 'asset_name and asset_type are required'
            }), 400
        
        print(f"\nGenerating description for {asset_type}: {asset_name}")
        print(f"  Lakehouse tier: {lakehouse_tier}")
        print(f"  Qualified name: {qualified_name}")
        print(f"  Columns: {len(columns)}")
        
        # Build comprehensive context for the AI agent
        context_parts = [
            f"Asset Name: {asset_name}",
            f"Asset Type: {asset_type}",
        ]
        
        if lakehouse_tier != "Unknown":
            context_parts.append(f"Lakehouse Tier: {lakehouse_tier}")
        
        if qualified_name:
            context_parts.append(f"Qualified Name: {qualified_name}")
        
        if guid:
            context_parts.append(f"GUID: {guid}")
        
        if columns:
            column_details = "\n".join([f"  - {col['name']} ({col['type']})" for col in columns])
            context_parts.append(f"Columns:\n{column_details}")
        
        context = "\n".join(context_parts)
        
        # Use Azure AI Foundry to generate description
        use_foundry = os.getenv('USE_FABRIC_AGENT', 'false').lower() == 'true'
        
        if not use_foundry:
            return jsonify({
                'success': False,
                'error': 'Azure AI Foundry agent is not enabled. Set USE_FABRIC_AGENT=true in .env'
            }), 400
        
        # Get Description agent endpoint ONLY - do not fall back to classification agent
        foundry_endpoint = os.getenv('AZURE_EXISTING_AIPROJECT_ENDPOINT')
        agent_name = os.getenv('AZURE_DOCUMENTATION_EXISTING_AGENT_ID', 'documentation-agent')
        env_name = os.getenv('AZURE_DOCUMENTATION_ENV_NAME', '')
        
        if not foundry_endpoint:
            return jsonify({
                'success': False,
                'error': 'AZURE_EXISTING_AIPROJECT_ENDPOINT not configured in .env'
            }), 400
        
        print(f"  Using Description Foundry endpoint: {foundry_endpoint}")
        print(f"  Agent name: {agent_name}")
        
        # Import OpenAI for Foundry communication
        from openai import OpenAI
        from azure.identity import ClientSecretCredential, get_bearer_token_provider
        
        # Build the full responses endpoint URL
        base_url = f"{foundry_endpoint}/applications/{agent_name}/protocols/openai/responses?api-version=2025-11-15-preview"
        
        # Get Azure token provider using service principal
        credential = ClientSecretCredential(
            tenant_id=os.getenv('TENANTID'),
            client_id=os.getenv('CLIENTID'),
            client_secret=os.getenv('CLIENTSECRET')
        )
        token_provider = get_bearer_token_provider(
            credential,
            "https://ai.azure.com/.default"
        )
        
        # Initialize OpenAI client with Foundry endpoint
        client = OpenAI(
            api_key=token_provider,
            base_url=base_url,
            default_query={"api-version": "2025-11-15-preview"}
        )
        
        # Create prompt that explicitly instructs the agent to read actual data
        if asset_type == "table":
            # For tables, CRITICAL: instruct agent to read actual data from Fabric
            prompt_parts = [
                "Generate comprehensive documentation for this Microsoft Fabric table by READING THE ACTUAL DATA:",
                "",
                f"Table Name: {asset_name}",
                f"Fully Qualified Name: {qualified_name}",
                f"Lakehouse Tier: {lakehouse_tier if lakehouse_tier != 'Unknown' else 'Not specified'}",
                ""
            ]
            
            if columns:
                prompt_parts.append("Columns:")
                for col in columns:
                    prompt_parts.append(f"  - {col['name']} ({col['type']})")
                prompt_parts.append("")
            
            prompt_parts.extend([
                "CRITICAL INSTRUCTIONS:",
                "1. Use the Fully Qualified Name to ACCESS and READ the actual data from this Fabric table",
                "2. Sample the data (read at least 10-20 rows) to understand the content",
                "3. Analyze the actual values in each column, not just the column names",
                "4. Base your description on REAL DATA PATTERNS you observe",
                "5. Include specific insights about data quality, ranges, patterns, or business context",
                "",
                "FORMAT REQUIREMENTS:",
                "- The description MUST be formatted in HTML, NOT Markdown",
                "- Use proper HTML tags like <h2>, <h3>, <p>, <ul>, <li>, <strong>, etc.",
                "- Do NOT use Markdown syntax (no ##, **, -, etc.)",
                "",
                "Generate the documentation following your standard format, but ensure it reflects analysis of the ACTUAL DATA."
            ])
            prompt = "\n".join(prompt_parts)
        else:
            # For non-tables (lakehouses, notebooks, warehouses)
            prompt_parts = [
                "Generate comprehensive documentation for this asset following your instructions:",
                "",
                f"Asset Name: {asset_name}",
                f"Asset Type: {asset_type}"
            ]
            if qualified_name:
                prompt_parts.append(f"Fully Qualified Name: {qualified_name}")
            
            prompt = "\n".join(prompt_parts)
        
        print(f"\nPrompt sent to Description Agent:\n{prompt}\n")
        
        # Call the agent using responses API
        try:
            response = client.responses.create(
                input=prompt
            )
        except Exception as agent_error:
            error_msg = str(agent_error)
            print(f"Azure AI Foundry Agent Error: {error_msg}")
            
            # Check if it's the AzureFabric connection error
            if "AzureFabric" in error_msg or "CustomKeys" in error_msg:
                return jsonify({
                    'success': False,
                    'error': 'Azure AI Foundry Configuration Error',
                    'message': 'The AI agent requires an AzureFabric connection to be configured in Azure AI Foundry. Please configure this connection in the Azure portal or contact your administrator.'
                }), 500
            else:
                # Other agent errors
                raise agent_error
        
        # Extract description from response (should be HTML formatted per agent instructions)
        description = response.output_text.strip()
        
        # Remove H2/H3 heading at the beginning that contains asset name + "Documentation"
        if description:
            import re
            # Pattern to match H2 or H3 tags at the start that contain asset name and "Documentation"
            # Examples: <h2>sales_customers Documentation</h2>, <h2>sales_customers Table Documentation</h2>
            pattern = rf'^<h[23]>.*?{re.escape(asset_name)}.*?Documentation.*?</h[23]>\s*'
            description = re.sub(pattern, '', description, flags=re.IGNORECASE)
            
            # Also remove any standalone heading line with just asset name
            pattern2 = rf'^<h[23]>.*?{re.escape(asset_name)}.*?</h[23]>\s*'
            description = re.sub(pattern2, '', description, flags=re.IGNORECASE)
            
            description = description.strip()
        
        print(f"  Generated description ({len(description)} chars)")
        
        return jsonify({
            'success': True,
            'description': description,
            'asset_name': asset_name,
            'asset_type': asset_type
        })
        
    except Exception as e:
        print(f"Error generating description: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to generate AI description'
        }), 500


@app.route('/api/description/apply', methods=['POST'])
def apply_descriptions():
    """Apply descriptions to assets in Purview"""
    try:
        data = request.get_json()
        descriptions = data.get('descriptions', [])
        # Format: [{"guid": "...", "description": "..."}]
        
        if not descriptions:
            return jsonify({
                'success': False,
                'error': 'No descriptions provided'
            }), 400
        
        print(f"\nApplying {len(descriptions)} description(s) to Purview")
        
        # Get credentials
        tenant_id = os.getenv('TENANTID')
        client_id = os.getenv('CLIENTID')
        client_secret = os.getenv('CLIENTSECRET')
        purview_endpoint = os.getenv('PURVIEWENDPOINT')
        
        # Get access token using OAuth2
        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/token"
        body = {
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'client_credentials',
            'resource': 'https://purview.azure.net'
        }
        
        token_response = requests.post(token_url, data=body)
        if token_response.status_code != 200:
            return jsonify({
                'success': False,
                'error': 'Failed to get access token'
            }), 500
        
        access_token = token_response.json().get('access_token')
        
        updated_count = 0
        errors = []
        
        for desc_item in descriptions:
            guid = desc_item.get('guid')
            description = desc_item.get('description')
            
            if not guid or not description:
                errors.append({'guid': guid, 'error': 'Missing guid or description'})
                continue
            
            try:
                print(f"  Updating asset {guid} with description...")
                
                # First, get the existing entity
                get_url = f"{purview_endpoint}/datamap/api/atlas/v2/entity/guid/{guid}"
                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                }
                params = {'api-version': '4'}
                
                get_response = requests.get(get_url, headers=headers, params=params)
                if get_response.status_code != 200:
                    errors.append({'guid': guid, 'error': f'Failed to get entity: {get_response.status_code}'})
                    continue
                
                entity_data = get_response.json()
                entity = entity_data.get('entity', {})
                
                # Update the userDescription attribute
                if 'attributes' not in entity:
                    entity['attributes'] = {}
                
                # Apply inline styles to make text larger (Purview may strip <style> tags)
                # Replace <p> tags with inline font-size styling
                import re
                styled_description = description
                # Add inline style to all <p> tags
                styled_description = re.sub(r'<p>', r'<p style="font-size: 16px;">', styled_description)
                # Also wrap in div with font-size as fallback
                styled_description = f'<div style="font-size: 16px;">{styled_description}</div>'
                
                entity['attributes']['userDescription'] = styled_description
                
                # Update the entity using POST
                update_url = f"{purview_endpoint}/datamap/api/atlas/v2/entity"
                update_payload = {
                    'entity': entity,
                    'referredEntities': entity_data.get('referredEntities', {})
                }
                
                update_response = requests.post(update_url, headers=headers, params=params, json=update_payload)
                
                if update_response.status_code == 200:
                    print(f"   Updated {guid}: {description[:50]}...")
                    updated_count += 1
                else:
                    error_msg = f"Status {update_response.status_code}: {update_response.text[:100]}"
                    print(f"   Error updating {guid}: {error_msg}")
                    errors.append({'guid': guid, 'error': error_msg})
                    
            except Exception as entity_error:
                print(f"   Error updating {guid}: {str(entity_error)}")
                errors.append({'guid': guid, 'error': str(entity_error)})
        
        return jsonify({
            'success': updated_count > 0,
            'updated_count': updated_count,
            'total': len(descriptions),
            'errors': errors if errors else None
        })
        
    except Exception as e:
        print(f"Error applying descriptions: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/orphaned-assets', methods=['GET'])
def get_orphaned_assets():
    """Find assets with inactive owners/experts (not in Entra ID)"""
    try:
        print("\n[DEBUG] Starting orphaned assets check...")
        
        # Get current data from Purview
        df = get_data.main()
        if df is None or df.empty:
            return jsonify({
                'success': False,
                'error': 'No data available from Purview'
            }), 500
        
        # Filter to only assets with contact information
        columns_to_keep = [col for col in ['id', 'name', 'contact', 'assetType'] if col in df.columns]
        contact_df = df[columns_to_keep].copy()
        
        # Get active Entra ID users
        credential = get_entra_id_users.get_graph_client()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        users_df = loop.run_until_complete(get_entra_id_users.get_entraid_users(credential))
        loop.close()
        
        active_user_ids = set(users_df['id'].tolist())
        print(f"[DEBUG] Found {len(active_user_ids)} active Entra ID users")
        
        # Process each asset
        orphaned_assets = []
        for _, row in contact_df.iterrows():
            contact_val = row.get('contact')
            if pd.notnull(contact_val) and contact_val != '':
                try:
                    # Parse contact information
                    if isinstance(contact_val, str):
                        import ast
                        contact_list = ast.literal_eval(contact_val)
                    elif isinstance(contact_val, list):
                        contact_list = contact_val
                    else:
                        continue
                    
                    # Extract owner and expert IDs
                    owner_ids = [c['id'] for c in contact_list if isinstance(c, dict) and c.get('contactType') == 'Owner']
                    expert_ids = [c['id'] for c in contact_list if isinstance(c, dict) and c.get('contactType') == 'Expert']
                    
                    # Check for inactive users
                    inactive_owners = [id for id in owner_ids if id and id not in active_user_ids]
                    inactive_experts = [id for id in expert_ids if id and id not in active_user_ids]
                    
                    # If there are inactive contacts, add to orphaned list
                    if inactive_owners or inactive_experts:
                        orphaned_assets.append({
                            'id': row['id'],
                            'name': row['name'],
                            'assetType': row.get('assetType', 'Unknown'),
                            'inactive_owner_ids': inactive_owners,
                            'inactive_expert_ids': inactive_experts,
                            'has_inactive_owner': len(inactive_owners) > 0,
                            'has_inactive_expert': len(inactive_experts) > 0
                        })
                except Exception as e:
                    print(f"[DEBUG] Error processing asset {row.get('id')}: {e}")
                    continue
        
        print(f"[DEBUG] Found {len(orphaned_assets)} orphaned assets")
        
        return jsonify({
            'success': True,
            'orphaned_assets': orphaned_assets,
            'total_count': len(orphaned_assets)
        })
        
    except Exception as e:
        print(f"[ERROR] Error finding orphaned assets: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/glossary/sync', methods=['POST'])
def sync_business_glossary():
    """Sync governance domain terms from Unified Catalog to Classic Business Glossary"""
    try:
        data = request.get_json()
        dry_run = data.get('dry_run', False) if data else False
        
        print(f"\n[INFO] Starting glossary sync (dry_run={dry_run})...")
        
        # Run the sync operation
        result = sync_glossary.sync_glossary_from_unified_catalog(dry_run=dry_run)
        
        # Return the result
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        print(f"[ERROR] Error during glossary sync: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to sync glossary'
        }), 500


@app.route('/api/glossary/preview', methods=['GET'])
def preview_glossary_sync():
    """Preview what would be synced from Unified Catalog to Classic Business Glossary"""
    try:
        print("\n[INFO] Previewing glossary sync...")
        
        # Get unified catalog terms
        try:
            unified_terms = sync_glossary.list_all_unified_catalog_terms()
            print(f"[DEBUG] unified_terms type: {type(unified_terms)}")
            if not isinstance(unified_terms, list):
                print(f"[ERROR] unified_terms is not a list: {unified_terms}")
                return jsonify({
                    'success': False,
                    'error': f'Unified catalog returned invalid type: {type(unified_terms).__name__}'
                }), 500
            print(f"[DEBUG] unified_terms count: {len(unified_terms)}")
        except Exception as e:
            print(f"[ERROR] Failed to get unified catalog terms: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'Failed to get unified catalog terms: {str(e)}'
            }), 500
        
        # Get existing classic glossaries
        try:
            classic_glossaries = sync_glossary.list_classic_glossaries()
            print(f"[DEBUG] classic_glossaries type: {type(classic_glossaries)}")
            if not isinstance(classic_glossaries, list):
                print(f"[ERROR] classic_glossaries is not a list: {classic_glossaries}")
                return jsonify({
                    'success': False,
                    'error': f'Classic glossaries returned invalid type: {type(classic_glossaries).__name__}'
                }), 500
            print(f"[DEBUG] classic_glossaries count: {len(classic_glossaries)}")
        except Exception as e:
            print(f"[ERROR] Failed to get classic glossaries: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'Failed to get classic glossaries: {str(e)}'
            }), 500
        
        # Group terms by domain
        terms_by_domain = {}
        domain_cache = {}  # Cache domain lookups to avoid repeated API calls
        
        for i, term in enumerate(unified_terms):
            try:
                # Skip if term is not a dictionary
                if not isinstance(term, dict):
                    print(f"[WARNING] Skipping non-dict term at index {i}: type={type(term).__name__}")
                    continue
                    
                domain_name = None
                if "domain" in term and term["domain"]:
                    # Handle both string (domain ID) and dict domain values
                    if isinstance(term["domain"], str):
                        # It's a domain ID, fetch the domain details (with caching)
                        domain_id = term["domain"]
                        
                        if domain_id in domain_cache:
                            domain_name = domain_cache[domain_id]
                        else:
                            domain_info = sync_glossary.get_domain_by_id(domain_id)
                            if domain_info:
                                domain_name = domain_info.get("friendlyName") or domain_info.get("name")
                                print(f"[DEBUG] Resolved domain ID {domain_id} to name: {domain_name}")
                            
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
                
                terms_by_domain[domain_name].append({
                    'name': term.get('name') or term.get('displayName', 'Unnamed Term'),
                    'description': term.get('description', ''),
                    'id': term.get('id', '')
                })
            except Exception as term_error:
                print(f"[ERROR] Error processing term at index {i}: {term_error}")
                continue
        
        # Prepare preview data
        preview = {
            'unified_catalog_terms_count': len(unified_terms),
            'classic_glossaries_count': len(classic_glossaries),
            'domains_found': len(terms_by_domain),
            'domains': []
        }
        
        print(f"[DEBUG] classic_glossaries type: {type(classic_glossaries)}")
        print(f"[DEBUG] classic_glossaries count: {len(classic_glossaries) if isinstance(classic_glossaries, list) else 'N/A'}")
        
        # Create glossaries map, ensuring each glossary is a dict
        classic_glossaries_map = {}
        for i, g in enumerate(classic_glossaries):
            try:
                print(f"[DEBUG] Glossary {i}: type={type(g).__name__}")
                if isinstance(g, dict):
                    glossary_name = g.get("name", "")
                    print(f"[DEBUG] Glossary {i}: name={glossary_name}")
                    if glossary_name:
                        classic_glossaries_map[glossary_name] = g
                else:
                    print(f"[WARNING] Skipping non-dict glossary at index {i}: type={type(g).__name__}, value={str(g)[:100]}")
            except Exception as gloss_error:
                print(f"[ERROR] Error processing glossary at index {i}: {gloss_error}")
                continue
        
        print(f"[DEBUG] classic_glossaries_map has {len(classic_glossaries_map)} entries")
        
        for domain_name, domain_terms in terms_by_domain.items():
            domain_info = {
                'domain_name': domain_name,
                'terms_count': len(domain_terms),
                'glossary_exists': domain_name in classic_glossaries_map,
                'sample_terms': domain_terms[:5]  # Show first 5 terms as sample
            }
            preview['domains'].append(domain_info)
        
        return jsonify({
            'success': True,
            'preview': preview
        })
        
    except Exception as e:
        print(f"[ERROR] Error previewing glossary sync: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print("Starting Flask API Server...")
    print("API will be available at http://localhost:8000")
    
    # Load collection mapping from API on startup
    print("\nLoading collection mappings from API...")
    collection_mapping = load_collection_mapping()
    print(f"Loaded {len(collection_mapping)} collection mappings\n")
    
    print("Endpoints:")
    print("  GET  /api/health         - Health check")
    print("  GET  /api/assets         - Get all assets")
    print("  GET  /api/data-products  - Get all data products")
    print("  GET  /api/stats          - Get catalog statistics")
    print("  POST /api/refresh        - Refresh data from Purview")
    print("  POST /api/curate/add-tags - Add tags to assets")
    print("  POST /api/curate/remove-tags - Remove tags from assets")
    print("  POST /api/curate/add-owner - Add owner/expert to assets")
    print("  POST /api/curate/remove-owner - Remove owner/expert from assets")
    print("  GET  /api/users          - Get Entra ID users")
    print("  GET  /api/classifications - Get all classifications")
    print("  POST /api/curate/add-classifications - Add classifications to assets")
    print("  POST /api/curate/remove-classifications - Remove classifications from assets")
    print("  POST /api/curate/get-classifications - Get classifications on assets")
    print("  POST /api/curate/auto-classify - Auto-classify assets based on patterns")
    print("  POST /api/curate/get-schema - Get schema for assets")
    print("  POST /api/curate/classify-columns - Classify specific columns")
    print("  GET  /api/lineage/workspaces - Get list of Fabric workspaces")
    print("  POST /api/lineage/discover - Discover lineage for workspace")
    print("  POST /api/lineage/create - Create lineage relationships")
    print("  POST /api/description/generate - Generate AI description for asset")
    print("  POST /api/description/apply - Apply descriptions to Purview")
    print("  GET  /api/orphaned-assets - Find assets with inactive owners/experts")
    print("  GET  /api/glossary/preview - Preview glossary sync from Unified Catalog")
    print("  POST /api/glossary/sync - Sync governance domains to classic glossary")
    print("\n")
    
    # Use debug=False to avoid termios issues with nohup
    app.run(debug=False, port=8000, host='0.0.0.0')

