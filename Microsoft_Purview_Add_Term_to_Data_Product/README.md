# Microsoft Purview – Add Term to Data Product

This script links a glossary term to a data product in the **Microsoft Purview Unified Catalog** using the Purview Data Governance REST API.

## What it does

1. Looks up a glossary term by name (e.g. `Customer`)
2. Looks up a data product by name (e.g. `Customer Master Data Product`)
3. Creates a `TERM` relationship between the two

## Prerequisites

- Python 3.9+
- An Azure AD **Service Principal** (App Registration) with:
  - **Owner** contact role on the target data product in the Purview Unified Catalog
  - (Open the data product → **Contacts** → add the service principal as an **Owner**)
- The following Python packages:
  ```
  requests
  azure-identity
  python-dotenv
  ```

Install dependencies:
```bash
pip install requests azure-identity python-dotenv
```

Or with `uv`:
```bash
uv run --with requests --with azure-identity --with python-dotenv add_term_to_data_product.py
```

## Configuration

Create a `.env` file in the same folder as the script (it is excluded from source control via `.gitignore`):

```env
TENANTID=<your-tenant-id>
CLIENTID=<your-client-id>
CLIENTSECRET=<your-client-secret>
PURVIEWENDPOINT=https://<your-account>.purview.azure.com
```

| Variable          | Description                                      |
|-------------------|--------------------------------------------------|
| `TENANTID`        | Azure Active Directory tenant ID                 |
| `CLIENTID`        | Service principal application (client) ID        |
| `CLIENTSECRET`    | Service principal client secret                  |
| `PURVIEWENDPOINT` | Purview account endpoint URL                     |

> **Never commit the `.env` file** — it contains secrets. It is already listed in `.gitignore`.

## Usage

Edit the target values at the top of `add_term_to_data_product.py`:

```python
TARGET_TERM_NAME = "customer"
TARGET_DATA_PRODUCT_NAME = "Customer Master Data Product"
```

Then run:
```bash
python add_term_to_data_product.py
```

### Expected output

```
Searching for term: 'customer'
Found term 'Customer' with id: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
Searching for data product: 'Customer Master Data Product'
Found data product 'Customer Master Data Product' with id: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
Creating TERM relationship...
Relationship created successfully.
```

## Notes

- The script performs a **case-insensitive** name match for both the term and data product.
- If the relationship already exists, the script exits gracefully with `Relationship already exists.`
- The `update_data_product_status` function (commented out in `main`) can be used to temporarily set a data product to `DRAFT` before writing and restore it to `PUBLISHED` afterward, if required by your Purview configuration.
