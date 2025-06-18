#!/usr/bin/env python3
"""
Azure AI Connection Test Script
Run this script to verify that Azure AI is properly configured and accessible.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings

def test_azure_imports():
    """Test if Azure AI libraries are properly installed"""
    try:
        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential
        from azure.ai.agents.models import ListSortOrder, MessageRole
        print("✅ Azure AI libraries imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Azure AI import failed: {e}")
        print("💡 Run: pip install -r requirements.txt")
        return False

def test_azure_settings():
    """Test if Azure settings are properly configured"""
    required_settings = [
        'AZURE_AI_ENDPOINT',
        'AZURE_AI_AGENT_ID', 
        'AZURE_AI_THREAD_ID'
    ]
    
    missing_settings = []
    for setting in required_settings:
        if not hasattr(settings, setting) or not getattr(settings, setting):
            missing_settings.append(setting)
    
    if missing_settings:
        print(f"❌ Missing Azure settings: {', '.join(missing_settings)}")
        return False
    
    print("✅ Azure settings configured:")
    print(f"   - Endpoint: {settings.AZURE_AI_ENDPOINT}")
    print(f"   - Agent ID: {settings.AZURE_AI_AGENT_ID}")
    print(f"   - Thread ID: {settings.AZURE_AI_THREAD_ID}")
    return True

def test_azure_authentication():
    """Test Azure authentication"""
    try:
        from azure.identity import DefaultAzureCredential
        credential = DefaultAzureCredential()
        
        # Try to get a token (this will trigger the authentication flow)
        token = credential.get_token("https://management.azure.com/.default")
        print("✅ Azure authentication successful")
        print(f"   - Token acquired (expires: {token.expires_on})")
        return True
        
    except Exception as e:
        print(f"❌ Azure authentication failed: {e}")
        print("\n💡 Troubleshooting tips:")
        print("   1. Install Azure CLI: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli")
        print("   2. Login: az login")
        print("   3. Set subscription: az account set --subscription YOUR_SUBSCRIPTION_ID")
        print("   4. Or set environment variables: AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID")
        return False

def test_azure_ai_connection():
    """Test connection to Azure AI Project"""
    try:
        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential
        
        credential = DefaultAzureCredential()
        project = AIProjectClient(
            credential=credential,
            endpoint=settings.AZURE_AI_ENDPOINT
        )
        
        print("✅ Azure AI Project connection successful")
        
        # Try to get the agent
        agent = project.agents.get_agent(settings.AZURE_AI_AGENT_ID)
        print(f"✅ Agent found: {agent.name}")
        
        # Try to get the thread
        thread = project.agents.threads.get(settings.AZURE_AI_THREAD_ID)
        print(f"✅ Thread found: {thread.id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Azure AI connection failed: {e}")
        print("\n💡 This might mean:")
        print("   1. Your Azure account doesn't have access to this AI resource")
        print("   2. The endpoint, agent ID, or thread ID is incorrect")
        print("   3. The Azure AI resource is not available")
        print("   4. Network connectivity issues")
        return False

def test_fallback_mode():
    """Test the fallback response system"""
    try:
        from users.views import get_fallback_response
        from users.models import CustomUser
        
        # Test with a simple message
        response = get_fallback_response("hello", user=None)
        
        if response and len(response) > 0:
            print("✅ Fallback response system working")
            print(f"   - Sample response length: {len(response)} characters")
            return True
        else:
            print("❌ Fallback response system failed")
            return False
            
    except Exception as e:
        print(f"❌ Fallback response test failed: {e}")
        return False

def main():
    """Run all Azure AI tests"""
    print("🔍 Testing Azure AI Configuration\n")
    print("=" * 50)
    
    tests = [
        ("Azure Libraries Import", test_azure_imports),
        ("Azure Settings", test_azure_settings),
        ("Azure Authentication", test_azure_authentication),
        ("Azure AI Connection", test_azure_ai_connection),
        ("Fallback Mode", test_fallback_mode)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}:")
        print("-" * 30)
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Azure AI is properly configured.")
        print("   You can now use the full AI-powered chatbot features.")
    elif passed >= total - 1:  # Allow Azure AI to fail but fallback to work
        print("\n⚠️  Azure AI not available, but fallback mode is working.")
        print("   The application will work with reduced AI functionality.")
    else:
        print("\n🚨 Multiple tests failed. Please check your configuration.")
        print("   Refer to AZURE_SETUP.md for detailed setup instructions.")
    
    return passed == total

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