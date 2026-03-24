#!/usr/bin/env python3
"""
Test MongoDB Atlas Connection
This script tests if you can connect to MongoDB Atlas
"""

from pymongo import MongoClient
from urllib.parse import quote_plus
import sys

def test_connection():
    # Your credentials
    USERNAME = "riyaupadhyay162005_db_user"
    PASSWORD = "riya_123"
    CLUSTER_URL = "cluster0.npyd9ut.mongodb.net"
    
    print("=" * 60)
    print("MongoDB Atlas Connection Test")
    print("=" * 60)
    print()
    
    # URL encode credentials
    username = quote_plus(USERNAME)
    password = quote_plus(PASSWORD)
    
    # Build connection string
    connection_string = f"mongodb+srv://{username}:{password}@{CLUSTER_URL}/?retryWrites=true&w=majority&appName=Cluster0"
    
    print("🔍 Testing connection to MongoDB Atlas...")
    print(f"   Cluster: {CLUSTER_URL}")
    print(f"   Username: {USERNAME}")
    print()
    
    try:
        # Try with certifi
        try:
            import certifi
            print("✓ Using certifi for SSL certificates")
            client = MongoClient(
                connection_string,
                serverSelectionTimeoutMS=15000,
                tlsCAFile=certifi.where()
            )
        except ImportError:
            print("⚠ certifi not found, using alternative SSL settings")
            client = MongoClient(
                connection_string,
                serverSelectionTimeoutMS=15000,
                tlsAllowInvalidCertificates=True
            )
        
        # Test the connection
        print("⏳ Attempting to connect (15 second timeout)...")
        client.server_info()
        
        print()
        print("=" * 60)
        print("✅ SUCCESS! Connection established!")
        print("=" * 60)
        print()
        
        # Try to access database and collection
        db = client["ieeepb2"]
        collection = db["hallucinations"]
        
        # Count documents
        count = collection.count_documents({})
        print(f"📊 Database: ieeepb2")
        print(f"📊 Collection: hallucinations")
        print(f"📊 Document count: {count}")
        
        if count == 0:
            print()
            print("⚠ No documents found in collection.")
            print("💡 Run 'python3 load_mongodb.py' to import your data.")
        else:
            print()
            print("✓ Data found in collection!")
            
            # Show a sample document
            sample = collection.find_one()
            if sample:
                print()
                print("📄 Sample document fields:")
                for key in list(sample.keys())[:10]:
                    print(f"   - {key}")
        
        client.close()
        print()
        print("=" * 60)
        print("✅ All checks passed! Your MongoDB setup is working!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ CONNECTION FAILED")
        print("=" * 60)
        print()
        print(f"Error: {str(e)}")
        print()
        print("🔧 TROUBLESHOOTING STEPS:")
        print()
        print("1. ✅ Whitelist your IP address in MongoDB Atlas:")
        print("   → Go to https://cloud.mongodb.com")
        print("   → Click 'Network Access' in the left menu")
        print("   → Click 'ADD IP ADDRESS'")
        print("   → Click 'ADD CURRENT IP ADDRESS' (recommended)")
        print("   → Or use '0.0.0.0/0' for testing (allows all IPs)")
        print("   → Click 'Confirm'")
        print("   → Wait 1-2 minutes for changes to take effect")
        print()
        print("2. ✅ Check if your cluster is active:")
        print("   → Go to 'Database' in MongoDB Atlas")
        print("   → Make sure Cluster0 shows 'Active' (not 'Paused')")
        print("   → If paused, click 'Resume'")
        print()
        print("3. ✅ Verify your credentials:")
        print(f"   → Username: {USERNAME}")
        print(f"   → Password: {'*' * len(PASSWORD)}")
        print()
        print("4. ✅ Check your internet connection")
        print()
        print("5. 🔄 After fixing, run this script again:")
        print("   → python3 test_connection.py")
        print()
        print("=" * 60)
        return False

if __name__ == "__main__":
    print()
    success = test_connection()
    print()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)