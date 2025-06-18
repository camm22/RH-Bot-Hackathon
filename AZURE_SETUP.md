# Azure AI Setup Guide

## Overview
This application uses Azure AI Services for the chatbot functionality. When team members clone the repository, they need to configure Azure authentication to use the AI features.

## Authentication Methods

The application uses `DefaultAzureCredential` which tries authentication methods in this order:
1. Environment Variables
2. Managed Identity 
3. Azure CLI
4. Visual Studio Code
5. Azure PowerShell

## Option 1: Azure CLI Authentication (Recommended for Development)

### Step 1: Install Azure CLI

**Windows:**
```bash
# Using chocolatey
choco install azure-cli

# Or download from: https://aka.ms/installazurecliwindows
```

**macOS:**
```bash
# Using Homebrew
brew install azure-cli

# Or using curl
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

**Linux (Ubuntu/Debian):**
```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

### Step 2: Login to Azure CLI
```bash
# Login interactively
az login

# Or login with specific tenant
az login --tenant YOUR_TENANT_ID

# Verify login
az account show
```

### Step 3: Set the correct subscription
```bash
# List available subscriptions
az account list --output table

# Set the subscription used by the project
az account set --subscription "YOUR_SUBSCRIPTION_ID"
```

## Option 2: Environment Variables (Alternative)

If you have Azure service principal credentials, you can set environment variables:

### Create a `.env` file in the project root:
```bash
# .env file
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id
```

### Load environment variables in Django

Add to your `config/settings.py`:
```python
import os
from dotenv import load_dotenv

load_dotenv()

# Azure Authentication via environment variables
os.environ.setdefault('AZURE_CLIENT_ID', os.getenv('AZURE_CLIENT_ID'))
os.environ.setdefault('AZURE_CLIENT_SECRET', os.getenv('AZURE_CLIENT_SECRET'))
os.environ.setdefault('AZURE_TENANT_ID', os.getenv('AZURE_TENANT_ID'))
```

### Install python-dotenv:
```bash
pip install python-dotenv
```

## Option 3: Development Mode (Fallback)

If Azure isn't available, the application will use a local fallback system. To force this mode:

### Add to `config/settings.py`:
```python
# Force fallback mode for development
AZURE_AVAILABLE = False
```

## Troubleshooting

### Error: "DefaultAzureCredential failed to retrieve a token"

**Solution 1: Check Azure CLI login**
```bash
az account show
# If not logged in:
az login
```

**Solution 2: Check permissions**
```bash
# Make sure you have access to the Azure AI resource
az role assignment list --assignee $(az account show --query user.name -o tsv)
```

**Solution 3: Use specific credential**
Update `users/views.py` to use a specific credential method:
```python
# Replace this line:
credential=DefaultAzureCredential()

# With one of these:
from azure.identity import AzureCliCredential
credential=AzureCliCredential()

# Or:
from azure.identity import EnvironmentCredential  
credential=EnvironmentCredential()
```

### Error: "AZURE_AI_ENDPOINT not found"

Check that these settings are correct in `config/settings.py`:
```python
AZURE_AI_ENDPOINT = "https://hr-bot-hackathon-group4-resource.services.ai.azure.com/api/projects/hr-bot-hackathon-group4"
AZURE_AI_AGENT_ID = "asst_La9CRXiwP6eeKtSrficBdoFv"
AZURE_AI_THREAD_ID = "thread_FufuJu2292OEZPmj7ipUv7wG"
```

### Test Azure Connection

Create a test script `test_azure.py`:
```python
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from django.conf import settings

try:
    credential = DefaultAzureCredential()
    project = AIProjectClient(
        credential=credential,
        endpoint=settings.AZURE_AI_ENDPOINT
    )
    print("✅ Azure AI connection successful!")
    
    # Test getting the agent
    agent = project.agents.get_agent(settings.AZURE_AI_AGENT_ID)
    print(f"✅ Agent found: {agent.name}")
    
except Exception as e:
    print(f"❌ Azure AI connection failed: {e}")
    print("💡 The application will use fallback mode")
```

Run the test:
```bash
python manage.py shell -c "exec(open('test_azure.py').read())"
```

## Team Collaboration

### Shared Azure Resources
- The Azure AI endpoint, agent ID, and thread ID are already configured in the repository
- Each team member only needs to authenticate their personal Azure account
- No need to create new Azure resources

### Different Authentication per Developer
Each team member can use their preferred authentication method:
- Developer A: Azure CLI login
- Developer B: Environment variables
- Developer C: Fallback mode for testing

## Quick Setup Commands

For team members to quickly get started:

```bash
# 1. Clone the repository
git clone https://github.com/camm22/RH-Bot-Hackathon.git
cd RH-Bot-Hackathon

# 2. Set up Python environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Install and login to Azure CLI
# (Install Azure CLI first - see above)
az login

# 4. Run the application
python manage.py runserver

# 5. Test in browser
# Open http://127.0.0.1:8000 and try the chat feature
```

## Production Deployment

For production deployment, use Managed Identity or Service Principal:

```python
# In production settings
from azure.identity import ManagedIdentityCredential
credential = ManagedIdentityCredential()
```

The GitHub Actions workflow already handles this with the configured secrets:
- `AZUREAPPSERVICE_CLIENTID_E08E0CCEF05E4F8AB1F384EA6B507EE4`
- `AZUREAPPSERVICE_TENANTID_FD7F4D5D2BE9429CA4B13F8E14AD8372`
- `AZUREAPPSERVICE_SUBSCRIPTIONID_0A8A77AC076B407CA44444C4CBF9E59B` 