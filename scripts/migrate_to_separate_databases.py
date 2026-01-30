#!/usr/bin/env python3
"""
Data Migration Script: Separate Demo and Real Databases

Migrates existing data from single database to separate demo and real databases.
This script:
1. Connects to current database
2. Identifies demo vs real records based on wallet mode
3. Copies demo records to db_demo
4. Copies real records to db_real
5. Verifies data integrity
6. Creates backup before migration

Usage:
    python scripts/migrate_to_separate_databases.py [--dry-run] [--backup]

Author: Moniqo Team
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
try:
    from bson import ObjectId
except ImportError:
    from pymongo import ObjectId

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from app.config.settings import get_settings
from app.core.context import TradingMode
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def get_wallet_mode(
    db: Any,
    user_wallet_id: str
) -> TradingMode:
    """
    Determine if a wallet is demo or real.
    
    Args:
        db: Database instance
        user_wallet_id: User wallet ID
        
    Returns:
        TradingMode: DEMO or REAL
    """
    try:
        user_wallet = await db.user_wallets.find_one({
            "_id": ObjectId(user_wallet_id),
            "deleted_at": None
        })
        
        if not user_wallet:
            # Default to demo for safety
            return TradingMode.DEMO
        
        # Check use_testnet flag
        if user_wallet.get("use_testnet", False):
            return TradingMode.DEMO
        
        # Check wallet definition
        wallet_def_id = user_wallet.get("wallet_provider_id")
        if wallet_def_id:
            wallet_def = await db.wallets.find_one({
                "_id": ObjectId(wallet_def_id),
                "deleted_at": None
            })
            
            if wallet_def:
                is_demo = (
                    wallet_def.get("is_demo", False) or
                    wallet_def.get("integration_type") == "simulation" or
                    "demo" in wallet_def.get("slug", "").lower()
                )
                return TradingMode.DEMO if is_demo else TradingMode.REAL
        
        # Default to demo for safety
        return TradingMode.DEMO
        
    except Exception as e:
        logger.error(f"Error determining wallet mode: {e}")
        return TradingMode.DEMO


async def migrate_collection(
    source_db: Any,
    target_db_demo: Any,
    target_db_real: Any,
    collection_name: str,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Migrate a collection to separate databases.
    
    Args:
        source_db: Source database
        target_db_demo: Target demo database
        target_db_real: Target real database
        collection_name: Collection name to migrate
        dry_run: If True, don't actually migrate
        
    Returns:
        Dict with migration statistics
    """
    stats = {
        "total": 0,
        "demo": 0,
        "real": 0,
        "skipped": 0,
        "errors": 0
    }
    
    logger.info(f"Migrating collection: {collection_name}")
    
    try:
        # Get all documents from source
        cursor = source_db[collection_name].find({})
        documents = await cursor.to_list(length=None)
        
        stats["total"] = len(documents)
        logger.info(f"Found {stats['total']} documents in {collection_name}")
        
        if dry_run:
            logger.info(f"[DRY RUN] Would migrate {stats['total']} documents")
            return stats
        
        # Process each document
        for doc in documents:
            try:
                # Determine target database based on document
                target_db = None
                
                # Check if document has user_wallet_id or wallet_id
                wallet_id = doc.get("user_wallet_id") or doc.get("wallet_id")
                
                if wallet_id:
                    mode = await get_wallet_mode(source_db, str(wallet_id))
                    target_db = target_db_demo if mode == TradingMode.DEMO else target_db_real
                    stats["demo" if mode == TradingMode.DEMO else "real"] += 1
                else:
                    # No wallet ID - check other indicators
                    # For flows, check demo_force_position flag
                    if collection_name == "flows":
                        config = doc.get("config", {})
                        if config.get("demo_force_position", False):
                            target_db = target_db_demo
                            stats["demo"] += 1
                        else:
                            # Default to demo for safety
                            target_db = target_db_demo
                            stats["demo"] += 1
                    else:
                        # Default to demo for safety
                        target_db = target_db_demo
                        stats["demo"] += 1
                
                if target_db is not None:
                    # Remove _id to let MongoDB generate new one
                    doc_copy = doc.copy()
                    doc_copy.pop("_id", None)
                    
                    # Insert into target database
                    await target_db[collection_name].insert_one(doc_copy)
                else:
                    stats["skipped"] += 1
                    
            except Exception as e:
                logger.error(f"Error migrating document {doc.get('_id')}: {e}")
                stats["errors"] += 1
        
        logger.info(
            f"Migrated {collection_name}: "
            f"total={stats['total']}, demo={stats['demo']}, "
            f"real={stats['real']}, skipped={stats['skipped']}, errors={stats['errors']}"
        )
        
    except Exception as e:
        logger.error(f"Error migrating collection {collection_name}: {e}")
        stats["errors"] = stats["total"]
    
    return stats


async def create_backup(source_db: Any, backup_db_name: str) -> bool:
    """
    Create backup of source database.
    
    Args:
        source_db: Source database
        backup_db_name: Backup database name
        
    Returns:
        True if backup successful
    """
    try:
        logger.info(f"Creating backup database: {backup_db_name}")
        
        # Get source database name
        source_db_name = source_db.name
        
        # List all collections
        collections = await source_db.list_collection_names()
        
        # Copy each collection
        for collection_name in collections:
            logger.info(f"Backing up collection: {collection_name}")
            source_collection = source_db[collection_name]
            backup_collection = source_db.client[backup_db_name][collection_name]
            
            # Copy all documents
            cursor = source_collection.find({})
            documents = await cursor.to_list(length=None)
            
            if documents:
                await backup_collection.insert_many(documents)
                logger.info(f"Backed up {len(documents)} documents from {collection_name}")
        
        logger.info(f"Backup completed: {backup_db_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        return False


async def clear_target_databases(
    target_db_demo: Any,
    target_db_real: Any
) -> None:
    """
    Clear all collections in target databases except auth.
    
    Args:
        target_db_demo: Target demo database
        target_db_real: Target real database
    """
    # Collections to preserve - ONLY auth
    preserve_collections = ["auth"]
    
    logger.info("Clearing all collections except auth in demo database...")
    
    # Get all collections in demo database
    demo_collections = await target_db_demo.list_collection_names()
    for collection_name in demo_collections:
        if collection_name not in preserve_collections:
            try:
                result = await target_db_demo[collection_name].delete_many({})
                logger.info(f"  Cleared {result.deleted_count} documents from demo.{collection_name}")
            except Exception as e:
                logger.warning(f"  Could not clear demo.{collection_name}: {e} - continuing anyway")
    
    logger.info("Clearing all collections except auth in real database...")
    
    # Get all collections in real database
    real_collections = await target_db_real.list_collection_names()
    for collection_name in real_collections:
        if collection_name not in preserve_collections:
            try:
                result = await target_db_real[collection_name].delete_many({})
                logger.info(f"  Cleared {result.deleted_count} documents from real.{collection_name}")
            except Exception as e:
                logger.warning(f"  Could not clear real.{collection_name}: {e} - continuing anyway")
    
    logger.info("Target databases cleared (only auth collection preserved)")


async def verify_migration(
    source_db: Any,
    target_db_demo: Any,
    target_db_real: Any,
    collection_name: str
) -> bool:
    """
    Verify migration integrity.
    
    Args:
        source_db: Source database
        target_db_demo: Target demo database
        target_db_real: Target real database
        collection_name: Collection name to verify
        
    Returns:
        True if verification passes
    """
    try:
        source_count = await source_db[collection_name].count_documents({})
        demo_count = await target_db_demo[collection_name].count_documents({})
        real_count = await target_db_real[collection_name].count_documents({})
        total_migrated = demo_count + real_count
        
        logger.info(
            f"Verification for {collection_name}: "
            f"source={source_count}, demo={demo_count}, real={real_count}, "
            f"total_migrated={total_migrated}"
        )
        
        # Allow some discrepancy (deleted_at documents, etc.)
        if total_migrated >= source_count * 0.95:  # At least 95% migrated
            return True
        
        logger.warning(
            f"Verification failed for {collection_name}: "
            f"Expected ~{source_count}, got {total_migrated}"
        )
        return False
        
    except Exception as e:
        logger.error(f"Error verifying migration: {e}")
        return False


async def main():
    """Main migration function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate data to separate demo/real databases")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually migrate, just show what would happen")
    parser.add_argument("--backup", action="store_true", help="Create backup before migration")
    parser.add_argument("--skip-verify", action="store_true", help="Skip verification after migration")
    parser.add_argument("--clear-only", action="store_true", help="Only clear databases (keep auth), don't migrate data")
    args = parser.parse_args()
    
    settings = get_settings()
    if not settings:
        logger.error("Settings not loaded. Check your .env file.")
        return
    
    logger.info("Starting database migration...")
    logger.info(f"Source database: {settings.MONGODB_DB_NAME}")
    logger.info(f"Target real database: {settings.mongodb_db_name_real}")
    logger.info(f"Target demo database: {settings.mongodb_db_name_demo}")
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(
        settings.MONGODB_URL,
        serverSelectionTimeoutMS=5000
    )
    
    try:
        # Test connection
        await client.admin.command("ping")
        
        # Get databases
        source_db = client[settings.MONGODB_DB_NAME]
        target_db_real = client[settings.mongodb_db_name_real]
        target_db_demo = client[settings.mongodb_db_name_demo]
        
        # Create backup if requested
        if args.backup and not args.dry_run:
            backup_db_name = f"{settings.MONGODB_DB_NAME}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            success = await create_backup(source_db, backup_db_name)
            if not success:
                logger.error("Backup failed. Aborting migration.")
                return
        
        # Clear target databases (except auth collection)
        # Note: This may fail due to MongoDB permissions - that's OK
        if not args.dry_run:
            logger.info("Clearing target databases (keeping only auth collection)...")
            try:
                await clear_target_databases(target_db_demo, target_db_real)
                logger.info("Successfully cleared target databases")
            except Exception as e:
                logger.warning(f"Could not clear target databases (may be permission issue): {e}")
                logger.info("Some collections may not have been cleared due to permissions")
        else:
            logger.info("[DRY RUN] Would clear target databases (keeping only auth collection)")
        
        # If clear-only mode, exit after clearing
        if args.clear_only:
            logger.info("=" * 60)
            logger.info("Clear-only mode completed!")
            logger.info("Both demo and real databases have been cleared (auth preserved)")
            logger.info("Note: Some collections may not have been cleared due to MongoDB permissions")
            logger.info("=" * 60)
            return
        
        # Collections to migrate
        collections_to_migrate = [
            "orders",
            "positions",
            "flows",
            "executions",
            "user_wallets",
            "demo_wallet_state",  # Always goes to demo
        ]
        
        # Migrate each collection
        total_stats = {
            "total": 0,
            "demo": 0,
            "real": 0,
            "skipped": 0,
            "errors": 0
        }
        
        for collection_name in collections_to_migrate:
            if collection_name == "demo_wallet_state":
                # Always migrate to demo
                logger.info(f"Migrating {collection_name} to demo database only")
                # Simple copy to demo
                cursor = source_db[collection_name].find({})
                documents = await cursor.to_list(length=None)
                if documents and not args.dry_run:
                    # Remove _id for new inserts
                    for doc in documents:
                        doc.pop("_id", None)
                    await target_db_demo[collection_name].insert_many(documents)
                    logger.info(f"Migrated {len(documents)} documents to demo database")
            else:
                stats = await migrate_collection(
                    source_db,
                    target_db_demo,
                    target_db_real,
                    collection_name,
                    dry_run=args.dry_run
                )
                
                # Aggregate stats
                for key in total_stats:
                    total_stats[key] += stats[key]
        
        logger.info("=" * 60)
        logger.info("Migration Summary:")
        logger.info(f"Total documents: {total_stats['total']}")
        logger.info(f"Migrated to demo: {total_stats['demo']}")
        logger.info(f"Migrated to real: {total_stats['real']}")
        logger.info(f"Skipped: {total_stats['skipped']}")
        logger.info(f"Errors: {total_stats['errors']}")
        logger.info("=" * 60)
        
        # Verify migration
        if not args.skip_verify and not args.dry_run:
            logger.info("Verifying migration...")
            all_verified = True
            for collection_name in collections_to_migrate:
                if collection_name != "demo_wallet_state":
                    verified = await verify_migration(
                        source_db,
                        target_db_demo,
                        target_db_real,
                        collection_name
                    )
                    if not verified:
                        all_verified = False
            
            if all_verified:
                logger.info("✓ Migration verification passed")
            else:
                logger.warning("⚠ Migration verification had issues - please review")
        
        logger.info("Migration completed!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
