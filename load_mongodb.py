from pymongo import MongoClient
from urllib.parse import quote_plus
import json
import ssl

# Step 1: Your credentials
USERNAME = "riyaupadhyay162005_db_user"
PASSWORD = "riya"  # Password with @ will be URL encoded automatically
CLUSTER_URL = "cluster0.npyd9ut.mongodb.net"  # ONLY the cluster hostname

# Step 2: Configuration
DATABASE_NAME = "myDatabase"  # Change to your desired database name
COLLECTION_NAME = "myCollection"  # Change to your desired collection name
JSON_FILE_PATH = "/Users/riya/Downloads/ieeepb2.hallucinations.json"

def import_json_to_mongodb():
    try:
        # URL encode credentials to handle special characters (like @ in password)
        username = quote_plus(USERNAME)
        password = quote_plus(PASSWORD)
        
        # Build connection string
        connection_string = f"mongodb+srv://{username}:{password}@{CLUSTER_URL}/?retryWrites=true&w=majority&appName=Cluster0"
        
        print("Connecting to MongoDB Atlas...")
        
        # Try with certifi first (recommended)
        try:
            import certifi
            client = MongoClient(
                connection_string, 
                serverSelectionTimeoutMS=10000,
                tlsCAFile=certifi.where()
            )
            print("Using certifi for SSL...")
        except ImportError:
            # Fallback: disable SSL verification (not recommended for production)
            print("Warning: certifi not found, using SSL workaround...")
            client = MongoClient(
                connection_string,
                serverSelectionTimeoutMS=10000,
                tlsAllowInvalidCertificates=True
            )
        
        # Test connection
        client.server_info()
        print("✓ Connected successfully!")
        
        # Access database and collection
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        
        # Read JSON file
        print(f"\nReading JSON file: {JSON_FILE_PATH}")
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        # Convert MongoDB extended JSON format to regular format
        def convert_extended_json(obj):
            """Convert MongoDB extended JSON to regular format"""
            if isinstance(obj, dict):
                # Convert $oid to ObjectId
                if '$oid' in obj and len(obj) == 1:
                    from bson import ObjectId
                    return ObjectId(obj['$oid'])
                # Convert $date to datetime
                elif '$date' in obj and len(obj) == 1:
                    from datetime import datetime
                    return datetime.fromisoformat(obj['$date'].replace('Z', '+00:00'))
                # Recursively convert nested objects
                else:
                    return {k: convert_extended_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_extended_json(item) for item in obj]
            else:
                return obj
        
        print("Converting extended JSON format...")
        data = convert_extended_json(data)
        
        # Import data
        print("Importing data to MongoDB...")
        if isinstance(data, list):
            if len(data) > 0:
                result = collection.insert_many(data)
                print(f"✓ Successfully inserted {len(result.inserted_ids)} documents")
            else:
                print("⚠ JSON file contains an empty array")
        else:
            result = collection.insert_one(data)
            print(f"✓ Successfully inserted 1 document")
        
        # Verify the import
        count = collection.count_documents({})
        print(f"\n✓ Total documents in '{COLLECTION_NAME}' collection: {count}")
        
        # Show sample document (first 500 characters)
        sample = collection.find_one()
        if sample:
            print("\nSample document (preview):")
            sample_str = json.dumps(sample, indent=2, default=str)
            if len(sample_str) > 500:
                print(sample_str[:500] + "...\n(truncated)")
            else:
                print(sample_str)
        
        client.close()
        print("\n" + "="*60)
        print("✓ IMPORT COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"Database: {DATABASE_NAME}")
        print(f"Collection: {COLLECTION_NAME}")
        print(f"Total Documents: {count}")
        print(f"\nView your data at: https://cloud.mongodb.com")
        print("="*60)
        
    except FileNotFoundError:
        print(f"✗ Error: File '{JSON_FILE_PATH}' not found")
        print("Please check the file path is correct")
    except json.JSONDecodeError as e:
        print(f"✗ Error: Invalid JSON format - {e}")
    except Exception as e:
        print(f"✗ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Install certifi: pip install certifi")
        print("2. Verify your username and password are correct")
        print("3. Check that your IP address is whitelisted in MongoDB Atlas:")
        print("   - Go to 'Network Access' in MongoDB Atlas")
        print("   - Click 'Add IP Address'")
        print("   - Add your current IP or use 0.0.0.0/0 for testing")
        print("4. Ensure your cluster is active (not paused)")

if __name__ == "__main__":
    import_json_to_mongodb()