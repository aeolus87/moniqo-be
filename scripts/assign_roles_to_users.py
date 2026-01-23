#!/usr/bin/env python3
"""
Migration script to assign default "User" role to all users without a role.

This script:
1. Finds all users where user_role is None or missing
2. Finds the default "User" role
3. Assigns the role to all users without roles
4. Reports the results

Usage:
    cd backend
    source venv/bin/activate
    python scripts/assign_roles_to_users.py
    
    # Dry run (no changes made):
    python scripts/assign_roles_to_users.py --dry-run
"""

import asyncio
import sys
import argparse
from datetime import datetime
from pathlib import Path

# Add backend directory to Python path for imports
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from app.config.settings import settings


async def assign_roles_to_users(dry_run: bool = False):
    """
    Assign default "User" role to all users without a role.
    
    Args:
        dry_run: If True, only report what would be done without making changes
    """
    if settings is None:
        print("❌ Settings not loaded. Check your .env file.")
        return False
    
    try:
        # Connect to MongoDB
        print("🔌 Connecting to MongoDB...")
        client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000
        )
        db = client[settings.MONGODB_DB_NAME]
        
        # Test connection
        await client.admin.command("ping")
        print("✅ Connected to MongoDB\n")
        
        # Find or create the "User" role
        print("🔍 Looking for 'User' role...")
        user_role = await db["roles"].find_one({
            "name": "User",
            "is_deleted": False
        })
        
        if not user_role:
            print("⚠️  'User' role not found. Creating it...")
            
            # First, ensure we have the necessary permissions
            print("   Checking for required permissions...")
            required_permissions = [
                {"resource": "user_plans", "action": "read"},
                {"resource": "user_plans", "action": "write"},
                {"resource": "wallets", "action": "read"},
                {"resource": "wallets", "action": "write"},
                {"resource": "flows", "action": "read"},
                {"resource": "flows", "action": "write"},
                {"resource": "orders", "action": "read"},
                {"resource": "positions", "action": "read"},
            ]
            
            permission_ids = []
            for perm in required_permissions:
                existing_perm = await db["permissions"].find_one({
                    "resource": perm["resource"],
                    "action": perm["action"],
                    "is_deleted": False
                })
                
                if existing_perm:
                    permission_ids.append(existing_perm["_id"])
                else:
                    # Create permission if it doesn't exist
                    perm_doc = {
                        "resource": perm["resource"],
                        "action": perm["action"],
                        "description": f"{perm['resource']}:{perm['action']} permission",
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                        "is_deleted": False
                    }
                    result = await db["permissions"].insert_one(perm_doc)
                    permission_ids.append(result.inserted_id)
                    print(f"   ✅ Created permission: {perm['resource']}:{perm['action']}")
            
            # Create User role
            role_doc = {
                "name": "User",
                "description": "Default user role with basic permissions",
                "permissions": permission_ids,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "is_deleted": False
            }
            result = await db["roles"].insert_one(role_doc)
            user_role_id = result.inserted_id
            print(f"   ✅ Created 'User' role: {user_role_id}\n")
        else:
            user_role_id = user_role["_id"]
            print(f"✅ Found 'User' role: {user_role_id}\n")
        
        # Find all users without a role
        print("🔍 Finding users without roles...")
        users_without_role = await db["users"].find({
            "$or": [
                {"user_role": None},
                {"user_role": {"$exists": False}}
            ],
            "is_deleted": False
        }).to_list(length=None)
        
        user_count = len(users_without_role)
        print(f"📊 Found {user_count} users without roles\n")
        
        if user_count == 0:
            print("✅ All users already have roles assigned!")
            return True
        
        # Show users that will be updated
        print("👥 Users to update:")
        for user in users_without_role:
            auth = await db["auth"].find_one({"_id": user["auth_id"], "is_deleted": False})
            email = auth["email"] if auth else "unknown"
            print(f"   - {user['_id']} ({email})")
        print()
        
        if dry_run:
            print("🔍 DRY RUN MODE - No changes will be made")
            print(f"   Would assign 'User' role to {user_count} users")
            return True
        
        # Update users
        print(f"🔄 Assigning 'User' role to {user_count} users...")
        updated_count = 0
        failed_count = 0
        
        for user in users_without_role:
            try:
                result = await db["users"].update_one(
                    {"_id": user["_id"]},
                    {
                        "$set": {
                            "user_role": user_role_id,
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
                
                if result.modified_count > 0:
                    updated_count += 1
                    auth = await db["auth"].find_one({"_id": user["auth_id"], "is_deleted": False})
                    email = auth["email"] if auth else "unknown"
                    print(f"   ✅ Updated user {user['_id']} ({email})")
                else:
                    failed_count += 1
                    print(f"   ⚠️  Failed to update user {user['_id']}")
            except Exception as e:
                failed_count += 1
                print(f"   ❌ Error updating user {user['_id']}: {e}")
        
        print()
        print("=" * 60)
        print("📊 SUMMARY")
        print("=" * 60)
        print(f"✅ Successfully updated: {updated_count} users")
        if failed_count > 0:
            print(f"❌ Failed to update: {failed_count} users")
        print(f"📈 Total processed: {user_count} users")
        print("=" * 60)
        
        # Close connection
        client.close()
        
        return updated_count > 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Assign default 'User' role to all users without a role"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🔧 Assign Roles to Users Script")
    print("=" * 60)
    print()
    
    success = await assign_roles_to_users(dry_run=args.dry_run)
    
    if success:
        print("\n✅ Script completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Script completed with errors")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
