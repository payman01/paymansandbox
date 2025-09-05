#!/usr/bin/env python3
"""
Test script for the Azure Inactive Users Scanner Function
This script allows you to test the function locally before deployment.
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from unittest.mock import Mock

# Add the function directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'InactiveUsersScanner'))

# Import the function
from InactiveUsersScanner import InactiveUsersScanner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_configuration():
    """Test that all required environment variables are set."""
    print("Testing configuration...")
    
    required_vars = [
        'TENANT_ID',
        'CLIENT_ID', 
        'CLIENT_SECRET',
        'STORAGE_CONNECTION_STRING'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("\nPlease set the following environment variables:")
        for var in missing_vars:
            print(f"  export {var}='your-value-here'")
        return False
    
    print("✅ All required environment variables are set")
    return True

def test_token_acquisition():
    """Test Microsoft Graph token acquisition."""
    print("\nTesting token acquisition...")
    
    try:
        scanner = InactiveUsersScanner()
        token = scanner.get_access_token()
        
        if token:
            print("✅ Successfully acquired access token")
            print(f"   Token length: {len(token)} characters")
            return True
        else:
            print("❌ Failed to acquire access token")
            return False
            
    except Exception as e:
        print(f"❌ Error acquiring token: {str(e)}")
        return False

def test_graph_api_access():
    """Test Microsoft Graph API access."""
    print("\nTesting Microsoft Graph API access...")
    
    try:
        scanner = InactiveUsersScanner()
        token = scanner.get_access_token()
        
        # Test with a small batch of users
        import requests
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Try to get first 5 users
        url = f"{scanner.graph_endpoint}/users"
        params = {
            '$select': 'id,userPrincipalName,displayName',
            '$top': 5
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        users = data.get('value', [])
        
        print(f"✅ Successfully accessed Microsoft Graph API")
        print(f"   Retrieved {len(users)} users (sample)")
        
        if users:
            print("   Sample user data:")
            for user in users[:2]:  # Show first 2 users
                print(f"     - {user.get('displayName', 'N/A')} ({user.get('userPrincipalName', 'N/A')})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error accessing Microsoft Graph API: {str(e)}")
        return False

def test_storage_access():
    """Test Azure Blob Storage access."""
    print("\nTesting Azure Blob Storage access...")
    
    try:
        from azure.storage.blob import BlobServiceClient
        
        connection_string = os.environ.get('STORAGE_CONNECTION_STRING')
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        # Test connection by listing containers
        containers = list(blob_service_client.list_containers())
        
        print("✅ Successfully connected to Azure Blob Storage")
        print(f"   Found {len(containers)} containers")
        
        # Test creating the required container
        container_name = os.environ.get('BLOB_CONTAINER_NAME', 'inactive-users-reports')
        try:
            container_client = blob_service_client.get_container_client(container_name)
            container_client.create_container()
            print(f"✅ Created container: {container_name}")
        except Exception:
            print(f"ℹ️  Container {container_name} already exists")
        
        return True
        
    except Exception as e:
        print(f"❌ Error accessing Azure Blob Storage: {str(e)}")
        return False

def test_csv_generation():
    """Test CSV generation functionality."""
    print("\nTesting CSV generation...")
    
    try:
        scanner = InactiveUsersScanner()
        
        # Create sample data
        sample_data = [
            {
                'username': 'John Doe',
                'userPrincipalName': 'john.doe@company.com',
                'userPrincipalId': '12345-67890-abcdef',
                'lastLoginDate': '2024-01-15 10:30:00 UTC',
                'daysSinceLastLogin': 75
            },
            {
                'username': 'Jane Smith',
                'userPrincipalName': 'jane.smith@company.com', 
                'userPrincipalId': '98765-43210-fedcba',
                'lastLoginDate': 'Never logged in',
                'daysSinceLastLogin': 'N/A'
            }
        ]
        
        csv_content = scanner.generate_csv(sample_data)
        
        if csv_content and len(csv_content) > 0:
            print("✅ Successfully generated CSV content")
            print(f"   CSV length: {len(csv_content)} characters")
            
            # Show first few lines
            lines = csv_content.split('\n')[:4]
            print("   Sample CSV content:")
            for line in lines:
                if line.strip():
                    print(f"     {line}")
            
            return True
        else:
            print("❌ Failed to generate CSV content")
            return False
            
    except Exception as e:
        print(f"❌ Error generating CSV: {str(e)}")
        return False

def run_dry_run():
    """Run a dry run of the inactive users scan (without uploading to blob storage)."""
    print("\nRunning dry run of inactive users scan...")
    
    try:
        scanner = InactiveUsersScanner()
        
        print("Getting inactive users...")
        inactive_users = scanner.get_inactive_users()
        
        print(f"✅ Found {len(inactive_users)} inactive users")
        
        if inactive_users:
            print("\nSample inactive users:")
            for i, user in enumerate(inactive_users[:3]):  # Show first 3
                print(f"  {i+1}. {user.get('username', 'N/A')} ({user.get('userPrincipalName', 'N/A')})")
                print(f"     Last login: {user.get('lastLoginDate', 'N/A')}")
                print(f"     Days since login: {user.get('daysSinceLastLogin', 'N/A')}")
                print()
            
            if len(inactive_users) > 3:
                print(f"     ... and {len(inactive_users) - 3} more users")
        
        # Generate CSV
        csv_content = scanner.generate_csv(inactive_users)
        print(f"✅ Generated CSV with {len(csv_content)} characters")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in dry run: {str(e)}")
        return False

def main():
    """Main test function."""
    print("Azure Inactive Users Scanner - Test Suite")
    print("=" * 50)
    
    tests = [
        ("Configuration", test_configuration),
        ("Token Acquisition", test_token_acquisition),
        ("Microsoft Graph API Access", test_graph_api_access),
        ("Azure Blob Storage Access", test_storage_access),
        ("CSV Generation", test_csv_generation),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Results Summary:")
    print("=" * 50)
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<30} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The function should work correctly.")
        
        # Ask if user wants to run dry run
        try:
            response = input("\nWould you like to run a dry run of the inactive users scan? (y/n): ")
            if response.lower() in ['y', 'yes']:
                run_dry_run()
        except KeyboardInterrupt:
            print("\nTest completed.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please fix the issues before deploying.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

