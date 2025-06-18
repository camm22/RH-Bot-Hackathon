#!/usr/bin/env python3
"""
Azure AI Production Test Script
This script tests Azure authentication specifically for Azure App Service environment
"""

import os
import sys

def test_environment_variables():
    """Test if Azure environment variables are set"""
    print("🔍 Checking Environment Variables...")
    
    required_vars = ['AZURE_TENANT_ID', 'AZURE_CLIENT_ID']
    optional_vars = ['AZURE_CLIENT_SECRET', 'MSI_ENDPOINT', 'MSI_SECRET']
    
    missing_vars = []
    
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: {value[:8]}***")
        else:
            print(f"❌ {var}: Not set")
            missing_vars.append(var)
    
    for var in optional_vars:
        value = os.environ.get(var)
        if value:
            print(f"ℹ️  {var}: Present")
        else:
            print(f"ℹ️  {var}: Not set")
    
    if missing_vars:
        print(f"\n⚠️  Missing required variables: {', '.join(missing_vars)}")
        return False
    
    return True

def test_managed_identity():
    """Test Managed Identity authentication"""
    print("\n🔍 Testing Managed Identity...")
    
    try:
        from azure.identity import ManagedIdentityCredential
        credential = ManagedIdentityCredential()
        
        # Try to get a token
        token = credential.get_token("https://management.azure.com/.default")
        print("✅ Managed Identity authentication successful")
        print(f"   Token acquired (expires: {token.expires_on})")
        return True
        
    except Exception as e:
        print(f"❌ Managed Identity failed: {e}")
        return False

def test_default_credential():
    """Test DefaultAzureCredential"""
    print("\n🔍 Testing DefaultAzureCredential...")
    
    try:
        from azure.identity import DefaultAzureCredential
        credential = DefaultAzureCredential()
        
        # Try to get a token
        token = credential.get_token("https://management.azure.com/.default")
        print("✅ DefaultAzureCredential authentication successful")
        print(f"   Token acquired (expires: {token.expires_on})")
        return True
        
    except Exception as e:
        print(f"❌ DefaultAzureCredential failed: {e}")
        return False

def test_azure_ai_connection():
    """Test Azure AI connection without Django"""
    print("\n🔍 Testing Azure AI Connection...")
    
    # Azure AI configuration (hardcoded for testing)
    AZURE_AI_ENDPOINT = "https://hr-bot-hackathon-group4-resource.services.ai.azure.com/api/projects/hr-bot-hackathon-group4"
    AZURE_AI_AGENT_ID = "asst_La9CRXiwP6eeKtSrficBdoFv"
    
    try:
        from azure.ai.projects import AIProjectClient
        from azure.identity import ManagedIdentityCredential, DefaultAzureCredential
        
        # Try Managed Identity first
        try:
            credential = ManagedIdentityCredential()
            print("   Using ManagedIdentityCredential...")
        except:
            credential = DefaultAzureCredential()
            print("   Using DefaultAzureCredential...")
        
        project = AIProjectClient(
            credential=credential,
            endpoint=AZURE_AI_ENDPOINT
        )
        
        print("✅ Azure AI Project connection successful")
        
        # Try to get the agent
        agent = project.agents.get_agent(AZURE_AI_AGENT_ID)
        print(f"✅ Agent found: {agent.name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Azure AI connection failed: {e}")
        return False

def detect_environment():
    """Detect if running in Azure App Service"""
    print("🔍 Environment Detection...")
    
    # Check for Azure App Service specific environment variables
    app_service_indicators = [
        'WEBSITE_SITE_NAME',
        'WEBSITE_RESOURCE_GROUP', 
        'WEBSITE_OWNER_NAME',
        'MSI_ENDPOINT'
    ]
    
    is_app_service = any(os.environ.get(var) for var in app_service_indicators)
    
    if is_app_service:
        print("✅ Running in Azure App Service")
        site_name = os.environ.get('WEBSITE_SITE_NAME', 'Unknown')
        resource_group = os.environ.get('WEBSITE_RESOURCE_GROUP', 'Unknown')
        print(f"   Site: {site_name}")
        print(f"   Resource Group: {resource_group}")
    else:
        print("ℹ️  Running in local development environment")
    
    return is_app_service

def main():
    """Run production-focused Azure tests"""
    print("🔍 Azure AI Production Configuration Test\n")
    print("=" * 60)
    
    # Detect environment
    is_production = detect_environment()
    
    tests = [
        ("Environment Variables", test_environment_variables),
        ("Managed Identity", test_managed_identity),
        ("Default Credential", test_default_credential),
        ("Azure AI Connection", test_azure_ai_connection)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}:")
        print("-" * 40)
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Azure AI is properly configured for production.")
    elif passed >= 2:  # At least auth works
        print("\n⚠️  Some tests failed, but authentication is working.")
        print("   Check Azure AI resource permissions and configuration.")
    else:
        print("\n🚨 Authentication failed. Check your App Service configuration:")
        print("   1. Enable System Managed Identity")
        print("   2. Set AZURE_TENANT_ID environment variable")
        print("   3. Optionally set AZURE_CLIENT_ID")
    
    # Production-specific recommendations
    if is_production:
        print("\n📝 Production Recommendations:")
        print("   • Use Managed Identity (avoid client secrets)")
        print("   • Set environment variables via Azure Portal")
        print("   • Monitor authentication logs in App Service")
        print("   • Consider using Key Vault for sensitive config")
    
    return passed >= 2  # Success if auth works

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1) 