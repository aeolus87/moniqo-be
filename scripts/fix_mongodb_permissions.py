#!/usr/bin/env python3
"""
Script to fix MongoDB permissions for the application user.

This script grants readWrite permissions to the MongoDB user on the required databases.
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from urllib.parse import quote_plus
import sys


async def grant_permissions(mongodb_url: str):
    """
    Grant readWrite permissions to the user on required databases.
    
    Args:
        mongodb_url: MongoDB connection string
    """
    # Parse the connection string to extract user and database info
    # Format: mongodb://user:password@host:port/database
    try:
        # Connect to admin database to grant roles
        # Extract admin connection string (connect to admin DB instead of app DB)
        if "@" in mongodb_url:
            # Split to get the part before database and after credentials
            parts = mongodb_url.split("@")
            if len(parts) == 2:
                credentials_part = parts[0].replace("mongodb://", "")
                host_part = parts[1].split("/")[0]  # Get host:port part
                admin_url = f"mongodb://{credentials_part}@{host_part}/admin"
            else:
                print("Error: Invalid MongoDB URL format")
                return False
        else:
            print("Error: MongoDB URL must include authentication")
            return False
        
        print(f"Connecting to MongoDB admin database...")
        client = AsyncIOMotorClient(admin_url, serverSelectionTimeoutMS=5000)
        
        # Test connection
        await client.admin.command("ping")
        print("✅ Connected to MongoDB")
        
        # Extract username from connection string
        credentials = mongodb_url.split("://")[1].split("@")[0]
        username = credentials.split(":")[0]
        
        # Extract database name from connection string
        db_name = mongodb_url.split("/")[-1].split("?")[0]
        
        # Determine demo and real database names
        db_name_demo = f"{db_name}_demo"
        db_name_real = f"{db_name}_real"
        
        print(f"\nUsername: {username}")
        print(f"Base database: {db_name}")
        print(f"Demo database: {db_name_demo}")
        print(f"Real database: {db_name_real}")
        
        # Grant permissions
        admin_db = client.admin
        
        try:
            # Grant readWrite on demo database
            print(f"\nGranting readWrite permission on '{db_name_demo}'...")
            await admin_db.command({
                "grantRolesToUser": username,
                "roles": [{"role": "readWrite", "db": db_name_demo}]
            })
            print(f"✅ Granted readWrite permission on '{db_name_demo}'")
        except Exception as e:
            if "not found" in str(e).lower():
                print(f"⚠️  User '{username}' not found. Creating user with permissions...")
                # Extract password from connection string
                password = credentials.split(":")[1]
                # URL decode password if needed
                password = password.replace("%21", "!").replace("%3F", "?")
                
                await admin_db.command({
                    "createUser": username,
                    "pwd": password,
                    "roles": [
                        {"role": "readWrite", "db": db_name_demo},
                        {"role": "readWrite", "db": db_name_real},
                        {"role": "readWrite", "db": db_name}
                    ]
                })
                print(f"✅ Created user '{username}' with readWrite permissions")
            else:
                print(f"⚠️  Error granting permission on '{db_name_demo}': {e}")
        
        try:
            # Grant readWrite on real database
            print(f"\nGranting readWrite permission on '{db_name_real}'...")
            await admin_db.command({
                "grantRolesToUser": username,
                "roles": [{"role": "readWrite", "db": db_name_real}]
            })
            print(f"✅ Granted readWrite permission on '{db_name_real}'")
        except Exception as e:
            print(f"⚠️  Error granting permission on '{db_name_real}': {e}")
        
        try:
            # Grant readWrite on base database (for backward compatibility)
            print(f"\nGranting readWrite permission on '{db_name}'...")
            await admin_db.command({
                "grantRolesToUser": username,
                "roles": [{"role": "readWrite", "db": db_name}]
            })
            print(f"✅ Granted readWrite permission on '{db_name}'")
        except Exception as e:
            print(f"⚠️  Error granting permission on '{db_name}': {e}")
        
        # Verify permissions
        print(f"\nVerifying user permissions...")
        user_info = await admin_db.command({"usersInfo": username})
        if user_info.get("users"):
            user = user_info["users"][0]
            print(f"\nCurrent roles for user '{username}':")
            for role in user.get("roles", []):
                print(f"  - {role.get('role')} on {role.get('db')}")
        
        client.close()
        print("\n✅ Permissions setup complete!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure you're connecting as a user with admin privileges")
        print("2. Check that the MongoDB server is accessible")
        print("3. Verify the connection string is correct")
        return False


async def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python fix_mongodb_permissions.py <mongodb_url>")
        print("\nExample:")
        print('  python fix_mongodb_permissions.py "mongodb://user:pass@host:port/database"')
        sys.exit(1)
    
    mongodb_url = sys.argv[1]
    success = await grant_permissions(mongodb_url)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
