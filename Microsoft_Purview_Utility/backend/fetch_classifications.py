import os
import csv
import requests
from dotenv import load_dotenv
from azure.identity import ClientSecretCredential

# Load environment variables
load_dotenv()

# Purview API configuration
PURVIEW_ENDPOINT = os.getenv("PURVIEW_ENDPOINT")
TENANT_ID = os.getenv("TENANTID")
CLIENT_ID = os.getenv("CLIENTID")
CLIENT_SECRET = os.getenv("CLIENTSECRET")
PURVIEW_ENDPOINT = os.getenv("PURVIEWENDPOINT")

def get_access_token():
    """Get Azure AD access token using Service Principal"""
    credential = ClientSecretCredential(
        tenant_id=TENANT_ID,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
    token = credential.get_token("https://purview.azure.net/.default")
    return token.token

def fetch_all_classifications():
    """Fetch all classifications from Purview"""
    access_token = get_access_token()
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Get all classification definitions
    url = f"{PURVIEW_ENDPOINT}/catalog/api/atlas/v2/types/typedefs"
    
    params = {
        "type": "classification"
    }
    
    print(f"Fetching classifications from {PURVIEW_ENDPOINT}...")
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        data = response.json()
        classifications = data.get("classificationDefs", [])
        print(f" Found {len(classifications)} classifications")
        return classifications
    else:
        print(f" Failed to fetch classifications: {response.status_code}")
        print(f"Response: {response.text}")
        return []

def save_to_csv(classifications):
    """Save classifications to CSV file"""
    csv_file = "classification_mapping.csv"
    
    print(f"\nSaving classifications to {csv_file}...")
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Write header
        writer.writerow(['classification_name', 'display_name', 'description', 'category'])
        
        # Sort classifications by name
        classifications.sort(key=lambda x: x.get('name', ''))
        
        # Write data
        for classification in classifications:
            name = classification.get('name', '')
            # For display name, use the name without the "MICROSOFT." prefix if it exists
            display_name = name.replace('MICROSOFT.', '').replace('_', ' ').title() if name.startswith('MICROSOFT.') else name
            description = classification.get('description', '')
            category = classification.get('category', '')
            
            writer.writerow([name, display_name, description, category])
    
    print(f" Saved {len(classifications)} classifications to {csv_file}")
    print(f"\nFirst 10 classifications:")
    for i, classification in enumerate(classifications[:10], 1):
        print(f"  {i}. {classification.get('name', 'N/A')}")

def main():
    print("=" * 60)
    print("Purview Classification Fetcher")
    print("=" * 60)
    
    # Fetch classifications
    classifications = fetch_all_classifications()
    
    if classifications:
        # Save to CSV
        save_to_csv(classifications)
        print("\n" + "=" * 60)
        print(" Classification mapping file created successfully!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print(" No classifications found or error occurred")
        print("=" * 60)

if __name__ == "__main__":
    main()
