# Microsoft Purview Utility

> **⚠️ DISCLAIMER: UNDER CONSTRUCTION**  
> This project is currently under active development and **NOT PRODUCTION-READY**.  
> - Features are incomplete and may change significantly
> - Code has not been thoroughly tested in production environments and may cause damage, Only use for testing purposes in environments that are easily replaceable
> - Use at your own risk - I strongly advise against deploying this in production
> - Contributions and feedback are welcome as I work toward a stable release
> - Full Transparency, I had the ideas, Github Copilot Pro brought the code.

## 🚧 Known Limitations

- **Limited Error Handling**: Some API calls lack comprehensive error handling and retry logic
- **Debug Code Present**: Console.log statements and print statements remain in the codebase
- **Authentication**: Relies on Service Principal authentication only - no support for managed identities or interactive auth
- **Scalability**: Bulk operations may timeout on very large datasets (1000+ assets)
- **Browser Compatibility**: Tested primarily on Mozilla Firefox - other browsers may have issues
- **Documentation**: API documentation and inline code comments are incomplete
- **Testing Coverage**: Automated tests are minimal - manual testing required
- **Microsoft Foundry**: Requires specific agent setup and may not work with all Microsoft configurations
- **Fabric Integration**: Lineage discovery assumes specific Fabric workspace structures
- **Limited Testing**: I'm releasing this earlier with minimal testing so you're able to get your hands on the backend scripts.
- **Automatic Data Lineage**: Automatic Data Lineage can only be deleted with API's. 




## 🎯 Overview

A comprehensive web application for data governance, curation, and AI-powered catalog management in Microsoft Purview Unified Catalog, featuring intelligent classification, lineage discovery, and automated documentation.

This portal streamlines Microsoft Purview data governance with:

- **🤖 AI-Powered Classification**: Automatic classification suggestions using Microsoft Foundry agents (211 approved classifications)
- **🔗 Intelligent Lineage Discovery**: AI-driven analysis of Microsoft Fabric workspaces to map data relationships
- **📝 Automated Documentation**: Generate professional HTML descriptions for catalogs with tier detection
- **⚡ Bulk Operations**: Tag management, owner/expert assignment, and metadata operations at scale
- **🔒 Privacy-Focused UI**: Toggle technical details (GUIDs/qualified names) for secure demos and presentations
- **🎨 Modern Interface**: React + TypeScript + Tailwind CSS with responsive shadcn/ui components
- **Demo**: https://www.youtube.com/watch?v=zEfyTBmGh9I
- **Articles**: https://medium.com/@marcoOesterlin 

## ✨ Key Features

### AI-Powered Curation (Fabric Data Agent → Foundry Agent)
- **Smart Classification**: AI analyzes data from Fabric and suggests appropriate Purview classifications with validation
- **Data Lineage Intelligence**: Discovers table relationships and column mappings
- **Documentation Generation**: AI creates rich HTML descriptions with lakehouse tier detection (Bronze/Silver/Gold or Landing/Base/Curated)


### Bulk Operations Hub (Curate Portal)
Five specialized tabs for data governance:
1. **Tags**: Add/remove tags across multiple assets
2. **Contacts**: Manage owners and experts with Entra ID integration, including identifying orphaned assets
3. **Classifications**: Apply/remove/ classifications at column level for Microsoft Fabric Lakehouse Tables
4. **Description**: Generate and apply AI-powered descriptions
5. **Lineage**: Discover and create lineage relationships for Microsoft Fabric Workspaces

## 🏗️ Architecture

### Frontend Stack
- **React 18.3** with TypeScript for type safety
- **Vite** for fast development and optimized builds
- **Tailwind CSS** + **shadcn/ui** for modern, accessible components
- **React Router v6** for client-side routing
- **TanStack Query** for server state management
- **Radix UI** primitives for accessibility

### Backend Stack
- **Python 3.8+** with **Flask** REST API (31 endpoints)
- **Azure Identity** for authentication
- **Azure Purview SDK** (catalog, datamap, scanning)
- **OpenAI SDK** for AI Foundry agent communication
- **Flask-CORS** for cross-origin requests

### Azure Services Integration
- **Microsoft Purview**: Unified Catalog
- **Microsoft Foundry**: Three specialized agents (classification, lineage, documentation)
- **Microsoft Fabric**: Workspace, lakehouse, notebook integration
- **Azure Entra ID**: User management and directory services
- **Microsoft Graph API**: User profile and organizational data

## 📋 Prerequisites

### Required Azure Resources
1. **Microsoft Purview Account**
   - Data Curator or Data Source Administrator role
   - Access to data collections
   - API access enabled

2. **Microsoft Foundry Hub + Projects**
   - Three deployed agents: `classification-agent`, `datalineage-agent`, `documentation-agent`
   - GPT-4o model deployment used, recommends agents with completion.
   - Agent endpoints configured with proper access

3. **Microsoft Fabric Workspace**
   - Contributor or Admin role
   - Lakehouses with tables for lineage/classification
   - Network access from backend server

4. **Azure Entra ID**
   - Service Principal with the following:
     - **Microsoft Purview**: Data Curator role
     - **Microsoft Graph API**: `User.Read.All` (Application permission, admin consented)
     - **Microsoft Foundry**: Contributor on AI projects
     - **Microsoft Fabric**: Workspace Contributor/Admin

### Development Requirements
- **Backend**: Python 3.8+ with pip
- **Frontend**: Node.js 16+ with npm
- **OS**: Windows (PowerShell scripts provided) or Linux/macOS equivalent

## 🚀 Installation

### 1. Clone Repository
```bash
git clone https://github.com/your-org/Microsoft_Purview_Utility.git
cd Microsoft_Purview_Utility
```

### 2. Backend Setup
```bash
cd backend
pip install -r requirements.txt
```

**Required Python packages:**
- `flask`, `flask-cors` - Web server
- `azure-identity`, `azure-purview-catalog`, `azure-purview-datamap` - Purview SDK
- `azure-core` - Azure common libraries
- `python-dotenv` - Environment variable management
- `requests` - HTTP client
- `pandas` - Data manipulation (optional utilities)

### 3. Frontend Setup
```bash
cd ..  # Back to root
npm install
```

### 4. Environment Configuration

Create `.env` file in the **root directory**:

```bash
# ========================================
# Azure Authentication
# ========================================
CLIENTID=your-service-principal-client-id
CLIENTSECRET=your-service-principal-secret
TENANTID=your-azure-tenant-id

# ========================================
# Microsoft Purview Configuration
# ========================================
PURVIEWENDPOINT=https://your-account.purview.azure.com
PURVIEWACCOUNTNAME=your-account-name

# ========================================
# Microsoft Foundry - Unified Configuration
# ========================================
USE_FABRIC_AGENT=true
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_LOCATION=swedencentral
AZURE_EXISTING_AIPROJECT_ENDPOINT=https://your-resource.services.ai.azure.com/api/projects/your-project
AZURE_FOUNDRY_API_KEY=your-api-key

# Agent IDs and Environment Names
AZURE_CLASSIFICATION_EXISTING_AGENT_ID=classification-agent
AZURE_CLASSIFICATION_ENV_NAME=agents-playground-xxxx
AZURE_DATALINEAGE_EXISTING_AGENT_ID=datalineage-agent
AZURE_DATALINEAGE_ENV_NAME=agents-playground-xxxx
AZURE_DOCUMENTATION_EXISTING_AGENT_ID=documentation-agent
AZURE_DOCUMENTATION_ENV_NAME=agents-playground-xxxx

# Resource IDs (for Azure deployment tracking)
AZURE_EXISTING_AIPROJECT_RESOURCE_ID=/subscriptions/your-sub-id/resourceGroups/your-rg/providers/Microsoft.CognitiveServices/accounts/your-account/projects/your-project
AZURE_EXISTING_RESOURCE_ID=/subscriptions/your-sub-id/resourceGroups/your-rg/providers/Microsoft.CognitiveServices/accounts/your-account

# ========================================
# Optional Configuration
# ========================================
VITE_API_URL=http://localhost:8000
AZD_ALLOW_NON_EMPTY_FOLDER=true
```

**Important Notes:**
- `.env` is already in `.gitignore` - never commit credentials
- **All three agents use the same AI Foundry project** (unified endpoint)
- Each agent has its own agent ID and environment name
- `USE_FABRIC_AGENT=true` enables all AI-powered features (classification, lineage, documentation)

## 🎮 Running the Application


**Terminal 1 - Backend:**
```bash
cd backend
python api_server.py
```

**Terminal 2 - Frontend:**
```bash
npm run dev
```

**Access the application:** Open browser to `http://localhost:8080`


## 🛠️ Configuration Details

### Environment Variables Explained

#### Required for Basic Operation
- `CLIENTID`, `CLIENTSECRET`, `TENANTID`: Service Principal credentials for Azure authentication
- `PURVIEWENDPOINT`: Full URL to your Purview account (e.g., `https://myaccount.purview.azure.com`)
- Replace myaccount with your Microsoft Purview Account Name
- `PURVIEWACCOUNTNAME`: Short name of your Purview account (e.g., `myaccount`)

#### AI Feature Configuration
- `USE_FABRIC_AGENT=true`: Enables all AI-powered features (classification, lineage, documentation)
- `AZURE_EXISTING_AIPROJECT_ENDPOINT`: Unified AI Foundry project endpoint
- `AZURE_FOUNDRY_API_KEY`: API key for Microsoft Foundry authentication
- `AZURE_SUBSCRIPTION_ID`: Azure subscription ID (required for Fabric workspace enumeration)

#### AI Agent Configuration
All three agents use the same project endpoint but have unique agent IDs:
- `AZURE_CLASSIFICATION_EXISTING_AGENT_ID`: Agent ID for classification (e.g., `classification-agent`)
- `AZURE_DATALINEAGE_EXISTING_AGENT_ID`: Agent ID for lineage discovery (e.g., `datalineage-agent`)
- `AZURE_DOCUMENTATION_EXISTING_AGENT_ID`: Agent ID for documentation generation (e.g., `documentation-agent`)

Each agent also has an environment name:
- `AZURE_CLASSIFICATION_ENV_NAME`: Environment identifier (e.g., `agents-playground-3931`)
- `AZURE_DATALINEAGE_ENV_NAME`: Environment identifier (e.g., `agents-playground-7745`)
- `AZURE_DOCUMENTATION_ENV_NAME`: Environment identifier (e.g., `agents-playground-3720`)

Example configuration:
```bash
AZURE_EXISTING_AIPROJECT_ENDPOINT=https://myresource.services.ai.azure.com/api/projects/myproject
AZURE_FOUNDRY_API_KEY=your-api-key-here
AZURE_CLASSIFICATION_EXISTING_AGENT_ID=classification-agent
```

### Service Principal Setup

1. **Create Service Principal** in Azure Portal:
   ```bash
   az ad sp create-for-rbac --name "purview-utility-sp"
   ```

2. **Grant Purview Access**:
   - Open the Data Map
   - Go to Data map → Collections → First collection under Root collection
   - Role assignments → Add → Data Curator
   - Select your service principal

3. **Grant Graph API Permissions**:
   - Azure Portal → App registrations → Your SP
   - API permissions → Add permission
   - Microsoft Graph → Application permissions
   - Select `User.Read.All`
   - Grant admin consent

4. **Grant AI Foundry Access**:
   - Azure Portal → AI Foundry Hub resource
   - Access control (IAM) → Add role assignment
   - Role: Contributor
   - Assign to your service principal

5. **Grant Fabric Access**:
   - Fabric Portal → Workspace settings
   - Add member → Your service principal
   - Role: Contributor or Admin

### Backend Test Files
Test files are excluded from git:
- `backend/test_*.py` - Excluded via `.gitignore`
- Examples: `test_classification.py`, `test_lineage.py`, `test_names.py`
- Real GUIDs and workspace IDs anonymized in examples

### Development Server Ports
- Backend API: `http://localhost:8000`
- Frontend Dev: `http://localhost:8080`
- Frontend Preview: `http://localhost:4173` (after `npm run build`)

### Debugging Tips

**Backend Debugging:**
```bash
# Enable Flask debug mode (add to api_server.py)
app.run(debug=True, host='0.0.0.0', port=8000)

# Check logs for authentication issues
# Check environment variables are loaded
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('CLIENTID'))"
```

**Frontend Debugging:**
- Open browser DevTools (F12)
- Check Network tab for API call failures
- Check Console for JavaScript errors
- Verify `VITE_API_URL` matches backend address

## 🔧 Troubleshooting

### Issue: Backend Won't Start

**Symptoms:** `ModuleNotFoundError` or import errors

**Solutions:**
```bash
# Check Python version (need 3.8+)
python --version

# Reinstall dependencies
cd backend
pip install -r requirements.txt --force-reinstall

# Check for conflicting packages
pip list | grep azure
```

### Issue: AI Classification Not Working

**Symptoms:** "AI agent error" or empty suggestions

**Checklist:**
- [ ] `USE_FABRIC_AGENT=true` in `.env`
- [ ] `AZURE_EXISTING_AIPROJECT_ENDPOINT` and `AZURE_CLASSIFICATION_EXISTING_AGENT_ID` set correctly
- [ ] `AZURE_FOUNDRY_API_KEY` is valid and not expired
- [ ] Service principal has Fabric workspace access
- [ ] AI Foundry agent is deployed and running
- [ ] Check backend logs for authentication errors

**Validation:**
```bash
# Test agent endpoint manually
curl -X GET "https://your-resource.services.ai.azure.com/api/projects/your-project/agents" \
  -H "api-key: your-api-key-here"
```

### Issue: Lineage Discovery Fails

**Symptoms:** "Failed to discover lineage" error

**Common Causes:**
1. Workspace ID incorrect (get from Fabric URL)
2. Workspace has no tables or notebooks
3. Assets not yet in Purview catalog
4. Lineage agent not configured

**Debug Steps:**
```bash
# Check workspace ID format (should be GUID)
# Example: 7cd911c1-f5d0-4923-8925-123b8b45683

# Verify workspace has assets
GET /api/lineage/workspaces
# Should return workspace with asset_count > 0
```

### Issue: Frontend Connection Errors

**Symptoms:** "Failed to fetch" or CORS errors

**Solutions:**
1. Verify backend is running: `http://localhost:8000/api/health`
2. Check CORS configuration in `backend/api_server.py`
3. Verify `VITE_API_URL` in frontend (if customized)
4. Check firewall/antivirus isn't blocking localhost

### Issue: Authentication Failures

**Symptoms:** 401 Unauthorized or 403 Forbidden

**Checklist:**
- [ ] Service principal credentials correct in `.env`
- [ ] Service principal has required permissions (see Setup section)
- [ ] Admin consent granted for Graph API permissions
- [ ] Purview collection access configured
- [ ] Credentials not expired

**Test Authentication:**
```python
# Test file: test_auth.py
from azure.identity import ClientSecretCredential
import os
from dotenv import load_dotenv

load_dotenv()
credential = ClientSecretCredential(
    tenant_id=os.getenv("TENANTID"),
    client_id=os.getenv("CLIENTID"),
    client_secret=os.getenv("CLIENTSECRET")
)
token = credential.get_token("https://purview.azure.net/.default")
print(f"Token acquired: {token.token[:20]}...")
```

## 📚 Additional Resources

### Microsoft Documentation
- [Microsoft Purview REST API](https://learn.microsoft.com/en-us/rest/api/purview/)
- [Microsoft Foundry Foundry Agents](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/agent)
- [Microsoft Fabric REST API](https://learn.microsoft.com/en-us/rest/api/fabric/)
- [Microsoft Graph API](https://learn.microsoft.com/en-us/graph/overview)

### Project Information
- Backend Server: Flask running on port 8000
- Frontend Server: Vite dev server on port 8080
- Three AI Agents: Classification, Lineage, Documentation
- Direct Table Lineage: No process intermediary (simplified lineage model)
- 211 Approved Classifications: Validated against Purview classification list

### Agent Architecture

**Classification Agent:**
- Reads sample data from Fabric tables
- Analyzes column content patterns
- Suggests classifications from approved list
- Returns JSON with column → classification mappings

**Lineage Agent (Two-Stage):**
- **Stage 1 - Fabric Data Agent**: Analyzes workspace structure, reads notebooks, identifies data flows
- **Stage 2 - Foundry Agent**: Formats discoveries into Purview lineage JSON with column mappings
- Returns validated lineage relationships

**Documentation Agent:**
- Analyzes asset metadata (columns, types, names)
- Detects lakehouse tiers from qualified names
- Generates HTML descriptions
- Includes context-aware formatting

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

This is an enterprise data governance tool designed for Microsoft Purview environments. For questions, feature requests, or issues:

1. Check existing documentation above
2. Review troubleshooting section
3. Contact your organization's data governance team
4. For bugs: Create an issue with reproduction steps

---

**Built with:** React · TypeScript · Python · Flask · Microsoft Foundry · Microsoft Purview · Microsoft Fabric

**Version:** 1.0.0  
**Last Updated:** February 2026