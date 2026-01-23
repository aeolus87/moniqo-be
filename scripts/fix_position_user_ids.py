#!/usr/bin/env python3
"""
Migration script to fix positions with missing user_id.

This script:
1. Finds all positions where user_id is None or missing
2. Attempts to get user_id from the associated flow
3. Falls back to demo user if no user_id can be found
4. Updates the position documents

Usage:
    cd backend
    source venv/bin/activate
    python scripts/fix_position_user_ids.py
    
    # Dry run (no changes made):
    python scripts/fix_position_user_ids.py --dry-run
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


async def get_or_create_demo_user(db) -> str | None:
    """
    Get or create a demo user for demo mode positions.
    
    Returns:
        str: Demo user ID, or None if creation fails
    """
    try:
        # Try to find existing demo user by email
        auth = await db["auth"].find_one({"email": "demo@moniqo.com", "is_deleted": False})
        if auth:
            user = await db["users"].find_one({"auth_id": auth["_id"], "is_deleted": False})
            if user:
                print(f"  Found existing demo user: {user['_id']}")
                return str(user["_id"])
        
        # Create demo user if not found
        from app.core.security import hash_password
        import warnings
        
        # Suppress bcrypt version warning (non-critical)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning, module="passlib")
            # Create auth record
            auth_data = {
                "email": "demo@moniqo.com",
                "password_hash": hash_password("demo_password_not_used"),
                "is_verified": True,
                "is_active": True,
                "is_deleted": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            auth_result = await db["auth"].insert_one(auth_data)
            auth_id = auth_result.inserted_id
            
            # Create user record
            user_data = {
                "auth_id": auth_id,
                "first_name": "Demo",
                "last_name": "User",
                "is_deleted": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            user_result = await db["users"].insert_one(user_data)
            user_id = str(user_result.inserted_id)
            
            print(f"  Created demo user: {user_id}")
            return user_id
    except Exception as e:
        print(f"  ❌ Failed to get or create demo user: {e}")
        return None


async def fix_position_user_ids(dry_run: bool = False):
    """
    Fix positions with missing user_id.
    
    Args:
        dry_run: If True, only report what would be done without making changes
    """
    if settings is None:
        print("❌ Settings not loaded. Check your .env file.")
        return False
    
    print("=" * 60)
    print("Position user_id Migration Script")
    print("=" * 60)
    print()
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print()
    
    print("Connecting to MongoDB...")
    print(f"URL: {settings.MONGODB_URL}")
    print(f"Database: {settings.MONGODB_DB_NAME}")
    print()
    
    try:
        client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000
        )
        
        # Test connection
        await client.admin.command("ping")
        print("✅ MongoDB connection successful!")
        print()
        
        db = client[settings.MONGODB_DB_NAME]
        
        # Find positions with missing user_id
        print("Finding positions with missing user_id...")
        positions = await db.positions.find({
            "$or": [
                {"user_id": None},
                {"user_id": {"$exists": False}}
            ]
        }).to_list(length=None)
        
        total_positions = len(positions)
        print(f"Found {total_positions} positions with missing user_id")
        print()
        
        if total_positions == 0:
            print("✅ No positions need fixing!")
            client.close()
            return True
        
        # Get demo user for fallback
        print("Getting demo user for fallback...")
        demo_user_id = await get_or_create_demo_user(db)
        if not demo_user_id:
            print("❌ Could not get or create demo user. Some positions may remain unfixed.")
        print()
        
        # Process each position
        print("Processing positions...")
        print("-" * 60)
        
        stats = {
            "fixed_from_flow": 0,
            "fixed_with_demo": 0,
            "failed": 0,
            "skipped_deleted": 0
        }
        
        for i, pos in enumerate(positions, 1):
            pos_id = pos["_id"]
            flow_id = pos.get("flow_id")
            status = pos.get("status", "unknown")
            deleted_at = pos.get("deleted_at")
            
            print(f"[{i}/{total_positions}] Position {pos_id} (status: {status})")
            
            # Skip deleted positions
            if deleted_at:
                print(f"  ⏭️  Skipped - position is deleted")
                stats["skipped_deleted"] += 1
                continue
            
            user_id = None
            source = None
            
            # Try to get user_id from flow
            if flow_id:
                try:
                    flow = await db.flows.find_one({"_id": ObjectId(flow_id)})
                    if flow:
                        # Check config.user_id first
                        user_id = flow.get("config", {}).get("user_id")
                        if user_id:
                            source = "flow.config.user_id"
                        # Check root level user_id
                        elif flow.get("user_id"):
                            user_id = flow.get("user_id")
                            source = "flow.user_id"
                except Exception as e:
                    print(f"  ⚠️  Error getting flow {flow_id}: {e}")
            
            # Fallback to demo user
            if not user_id and demo_user_id:
                user_id = demo_user_id
                source = "demo_user"
            
            # Update position
            if user_id:
                try:
                    user_id_obj = ObjectId(str(user_id))
                    
                    if dry_run:
                        print(f"  📝 Would set user_id to {user_id_obj} (source: {source})")
                    else:
                        await db.positions.update_one(
                            {"_id": pos_id},
                            {"$set": {"user_id": user_id_obj, "updated_at": datetime.utcnow()}}
                        )
                        print(f"  ✅ Set user_id to {user_id_obj} (source: {source})")
                    
                    if source == "demo_user":
                        stats["fixed_with_demo"] += 1
                    else:
                        stats["fixed_from_flow"] += 1
                        
                except Exception as e:
                    print(f"  ❌ Failed to update: {e}")
                    stats["failed"] += 1
            else:
                print(f"  ❌ Could not determine user_id (no flow or demo user)")
                stats["failed"] += 1
        
        # Print summary
        print()
        print("=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"Total positions processed: {total_positions}")
        print(f"  Fixed from flow:    {stats['fixed_from_flow']}")
        print(f"  Fixed with demo:    {stats['fixed_with_demo']}")
        print(f"  Skipped (deleted):  {stats['skipped_deleted']}")
        print(f"  Failed:             {stats['failed']}")
        print()
        
        if dry_run:
            print("🔍 DRY RUN complete - no changes were made")
            print("   Run without --dry-run to apply changes")
        else:
            total_fixed = stats["fixed_from_flow"] + stats["fixed_with_demo"]
            if total_fixed > 0:
                print(f"✅ Successfully fixed {total_fixed} positions!")
            if stats["failed"] > 0:
                print(f"⚠️  {stats['failed']} positions could not be fixed")
        
        client.close()
        return stats["failed"] == 0
        
    except Exception as e:
        print(f"❌ Error during migration: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Fix positions with missing user_id"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only show what would be done, don't make changes"
    )
    args = parser.parse_args()
    
    success = asyncio.run(fix_position_user_ids(dry_run=args.dry_run))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
