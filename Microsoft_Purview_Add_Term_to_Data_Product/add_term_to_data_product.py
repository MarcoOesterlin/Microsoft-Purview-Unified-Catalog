import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from azure.identity import ClientSecretCredential
from dotenv import load_dotenv


# Load .env from the same directory as this script.
load_dotenv(Path(__file__).parent / ".env")

API_VERSION = "2025-09-15-preview"
PURVIEW_SCOPE = "https://purview.azure.net/.default"

# Target values requested
TARGET_TERM_NAME = "customer"
TARGET_DATA_PRODUCT_NAME = "Customer Master Data Product"


def get_env(*names: str, required: bool = False, default: Optional[str] = None) -> Optional[str]:
	for name in names:
		value = os.getenv(name)
		if value:
			return value

	if required:
		raise ValueError(f"Missing required environment variable. Expected one of: {', '.join(names)}")

	return default


TENANT_ID = get_env("TENANTID", "TENANT_ID", required=True)
CLIENT_ID = get_env("CLIENTID", "CLIENT_ID", required=True)
CLIENT_SECRET = get_env("CLIENTSECRET", "CLIENT_SECRET", required=True)
PURVIEW_ENDPOINT = (
	get_env("PURVIEWENDPOINT", "PURVIEW_ENDPOINT", default="https://api.purview-service.microsoft.com")
	or "https://api.purview-service.microsoft.com"
).rstrip("/")


def get_access_token() -> str:
	credential = ClientSecretCredential(
		tenant_id=TENANT_ID,
		client_id=CLIENT_ID,
		client_secret=CLIENT_SECRET,
	)
	token = credential.get_token(PURVIEW_SCOPE)
	return token.token


def get_headers() -> Dict[str, str]:
	return {
		"Authorization": f"Bearer {get_access_token()}",
		"Content-Type": "application/json",
	}


def list_data_products(skip: int = 0, top: int = 100) -> Dict[str, Any]:
	url = f"{PURVIEW_ENDPOINT}/datagovernance/catalog/dataProducts"
	params = {
		"api-version": API_VERSION,
		"top": top,
		"skip": skip,
	}
	response = requests.get(url, headers=get_headers(), params=params, timeout=60)
	response.raise_for_status()
	return response.json()


def list_terms(skip: int = 0, top: int = 100, keyword: Optional[str] = None) -> Dict[str, Any]:
	url = f"{PURVIEW_ENDPOINT}/datagovernance/catalog/terms"
	params: Dict[str, Any] = {
		"api-version": API_VERSION,
		"top": top,
		"skip": skip,
	}
	if keyword:
		params["keyword"] = keyword

	response = requests.get(url, headers=get_headers(), params=params, timeout=60)
	response.raise_for_status()
	return response.json()


def find_data_product_by_name(name: str) -> Optional[Dict[str, Any]]:
	skip = 0
	top = 100
	name_lower = name.strip().lower()

	while True:
		result = list_data_products(skip=skip, top=top)
		products = result.get("value", [])

		for product in products:
			if str(product.get("name", "")).strip().lower() == name_lower:
				return product

		if not result.get("nextLink"):
			return None
		skip += top


def find_term_by_name(name: str) -> Optional[Dict[str, Any]]:
	skip = 0
	top = 100
	name_lower = name.strip().lower()

	# Start with keyword-filtered search to reduce pages.
	while True:
		result = list_terms(skip=skip, top=top, keyword=name)
		terms = result.get("value", [])

		for term in terms:
			if str(term.get("name", "")).strip().lower() == name_lower:
				return term

		if not result.get("nextLink"):
			break
		skip += top

	# Fallback: full scan if keyword filtering didn't return exact name.
	skip = 0
	while True:
		result = list_terms(skip=skip, top=top)
		terms = result.get("value", [])

		for term in terms:
			if str(term.get("name", "")).strip().lower() == name_lower:
				return term

		if not result.get("nextLink"):
			return None
		skip += top


def update_data_product_status(data_product: Dict[str, Any], status: str) -> Dict[str, Any]:
	data_product_id = data_product["id"]
	url = f"{PURVIEW_ENDPOINT}/datagovernance/catalog/dataProducts/{data_product_id}"
	params = {"api-version": API_VERSION}
	payload = {**data_product, "status": status}
	response = requests.put(url, headers=get_headers(), params=params, json=payload, timeout=60)
	response.raise_for_status()
	return response.json()


def create_data_product_term_relationship(data_product_id: str, term_id: str) -> Dict[str, Any]:
	url = f"{PURVIEW_ENDPOINT}/datagovernance/catalog/dataProducts/{data_product_id}/relationships"
	params = {
		"api-version": API_VERSION,
		"entityType": "TERM",
	}
	payload = {
		"description": "Linked term to data product via script",
		"relationshipType": "Related",
		"assetId": data_product_id,
		"entityId": term_id,
	}

	response = requests.post(url, headers=get_headers(), params=params, json=payload, timeout=60)

	if response.status_code in (200, 201):
		return response.json()

	if response.status_code == 409:
		return {
			"status": "already_exists",
			"details": response.text,
		}

	response.raise_for_status()
	return {}


def format_error_response(exc: requests.HTTPError) -> str:
	response = exc.response
	if response is None:
		return str(exc)

	try:
		return f"HTTP {response.status_code}: {response.json()}"
	except Exception:
		return f"HTTP {response.status_code}: {response.text}"


def main() -> int:
	try:
		print(f"Searching for term: '{TARGET_TERM_NAME}'")
		term = find_term_by_name(TARGET_TERM_NAME)
		if not term:
			print(f"Term not found: '{TARGET_TERM_NAME}'")
			return 1

		term_id = term.get("id")
		if not term_id:
			print(f"Found term '{TARGET_TERM_NAME}', but no 'id' was returned: {term}")
			return 1

		print(f"Found term '{term.get('name')}' with id: {term_id}")

		print(f"Searching for data product: '{TARGET_DATA_PRODUCT_NAME}'")
		data_product = find_data_product_by_name(TARGET_DATA_PRODUCT_NAME)
		if not data_product:
			print(f"Data product not found: '{TARGET_DATA_PRODUCT_NAME}'")
			return 1

		data_product_id = data_product.get("id")
		if not data_product_id:
			print(
				f"Found data product '{TARGET_DATA_PRODUCT_NAME}', but no 'id' was returned: {data_product}"
			)
			return 1

		print(f"Found data product '{data_product.get('name')}' with id: {data_product_id}")

		# try:
		print("Creating TERM relationship...")
		relationship = create_data_product_term_relationship(data_product_id=data_product_id, term_id=term_id)
		# finally:
		# 	if is_published:
		# 		print("Restoring status to PUBLISHED...")
		# 		update_data_product_status(data_product, "PUBLISHED")
		# 		print("Status restored to PUBLISHED.")

		if relationship.get("status") == "already_exists":
			print("Relationship already exists.")
			return 0

		print("Relationship created successfully.")
		print(relationship)
		return 0

	except requests.HTTPError as http_error:
		print(f"Request failed: {format_error_response(http_error)}")
		return 1
	except Exception as exc:
		print(f"Unexpected error: {exc}")
		return 1


if __name__ == "__main__":
	sys.exit(main())
