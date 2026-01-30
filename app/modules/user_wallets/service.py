"""
User Wallets Service Layer

Business logic for wallet management operations.
Handles CRUD operations, connection testing, balance syncing.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from decimal import Decimal
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.wallets.models import (
    WalletDefinition,
    UserWallet,
    WalletSyncLog,
    UserWalletStatus,
    SyncStatus
)
from app.infrastructure.exchanges.factory import get_wallet_factory
from app.infrastructure.exchanges.base import (
    BaseWallet,
    WalletConnectionError,
    AuthenticationError
)
from app.utils.encryption import get_encryption_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class WalletServiceError(Exception):
    """Wallet service errors"""
    pass


# ==================== WALLET DEFINITIONS ====================

async def get_wallet_definitions(
    db: AsyncIOMotorDatabase,
    is_active: Optional[bool] = None,
    integration_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get wallet provider definitions.
    
    Args:
        db: MongoDB database
        is_active: Filter by active status (optional)
        integration_type: Filter by integration type (optional)
        
    Returns:
        List of wallet definition dicts
        
    Example:
        wallets = await get_wallet_definitions(db, is_active=True)
        for wallet in wallets:
            print(wallet["name"], wallet["integration_type"])
    """
    query = {"deleted_at": None}
    
    if is_active is not None:
        query["is_active"] = is_active
    
    if integration_type:
        query["integration_type"] = integration_type.lower()
    
    wallets = await db.wallets.find(query).sort("name", 1).to_list(length=100)
    
    # Normalize wallet definitions
    normalized_wallets = []
    for wallet in wallets:
        # Convert ObjectId to string
        wallet["id"] = str(wallet.pop("_id"))
        
        # Ensure required fields with defaults
        wallet.setdefault("required_credentials", [])
        wallet.setdefault("supported_symbols", [])
        wallet.setdefault("supported_order_types", ["market", "limit"])
        wallet.setdefault("supports_margin", False)
        wallet.setdefault("supports_futures", False)
        wallet.setdefault("description", None)
        wallet.setdefault("logo_url", None)
        
        # Ensure datetime fields are present
        if "created_at" not in wallet:
            wallet["created_at"] = datetime.now(timezone.utc)
        if "updated_at" not in wallet:
            wallet["updated_at"] = datetime.now(timezone.utc)
        
        normalized_wallets.append(wallet)
    
    logger.debug(f"Found {len(normalized_wallets)} wallet definitions")
    
    return normalized_wallets


async def get_wallet_definition(
    db: AsyncIOMotorDatabase,
    wallet_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get single wallet definition.
    
    Args:
        db: MongoDB database
        wallet_id: Wallet definition ID
        
    Returns:
        Wallet definition dict or None
    """
    wallet = await db.wallets.find_one({
        "_id": ObjectId(wallet_id),
        "deleted_at": None
    })
    
    if wallet:
        wallet["id"] = str(wallet.pop("_id"))
    
    return wallet


async def create_wallet_definition(
    db: AsyncIOMotorDatabase,
    wallet_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create new wallet definition (Admin only).
    
    Args:
        db: MongoDB database
        wallet_data: Wallet definition data
        
    Returns:
        Created wallet dict with ID
        
    Example:
        wallet = await create_wallet_definition(db, {
            "name": "Binance",
            "slug": "binance-v1",
            "integration_type": "cex",
            "required_credentials": ["api_key", "api_secret"]
        })
    """
    # Validate required fields
    required = ["name", "slug", "integration_type"]
    for field in required:
        if field not in wallet_data:
            raise ValueError(f"Missing required field: {field}")
    
    # Check slug uniqueness
    existing = await db.wallets.find_one({
        "slug": wallet_data["slug"],
        "deleted_at": None
    })
    
    if existing:
        raise ValueError(f"Wallet with slug '{wallet_data['slug']}' already exists")
    
    # Add timestamps
    now = datetime.now(timezone.utc)
    wallet_data["created_at"] = now
    wallet_data["updated_at"] = now
    wallet_data["deleted_at"] = None
    
    # Insert
    result = await db.wallets.insert_one(wallet_data)
    wallet_data["id"] = str(result.inserted_id)
    
    logger.info(f"Created wallet definition: {wallet_data['name']} ({wallet_data['slug']})")
    
    return wallet_data


# ==================== USER WALLETS ====================

async def get_user_wallets(
    db: AsyncIOMotorDatabase,
    user_id: str,
    is_active: Optional[bool] = None
) -> List[Dict[str, Any]]:
    """
    Get user's wallet connections.
    
    Args:
        db: MongoDB database
        user_id: User ID
        is_active: Filter by active status (optional)
        
    Returns:
        List of user wallet dicts
    """
    query = {
        "user_id": user_id,
        "deleted_at": None
    }
    
    if is_active is not None:
        query["is_active"] = is_active
    
    wallets = await db.user_wallets.find(query).sort("created_at", -1).to_list(length=100)
    
    # Populate wallet provider names
    for wallet in wallets:
        wallet["id"] = str(wallet.pop("_id"))
        
        provider = await db.wallets.find_one({"_id": ObjectId(wallet["wallet_provider_id"])})
        if provider:
            wallet["wallet_provider_name"] = provider["name"]
            wallet["wallet_provider_logo"] = provider.get("logo_url")
        
        # Remove credentials from response
        wallet.pop("credentials", None)
    
    logger.debug(f"Found {len(wallets)} wallets for user {user_id}")
    
    return wallets


async def get_user_wallet(
    db: AsyncIOMotorDatabase,
    user_wallet_id: str,
    user_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get single user wallet.
    
    Args:
        db: MongoDB database
        user_wallet_id: User wallet ID
        user_id: User ID (for access control)
        
    Returns:
        User wallet dict or None
    """
    wallet = await db.user_wallets.find_one({
        "_id": ObjectId(user_wallet_id),
        "user_id": user_id,
        "deleted_at": None
    })
    
    if wallet:
        wallet["id"] = str(wallet.pop("_id"))
        
        # Populate provider name
        provider = await db.wallets.find_one({"_id": ObjectId(wallet["wallet_provider_id"])})
        if provider:
            wallet["wallet_provider_name"] = provider["name"]
        
        # Remove credentials
        wallet.pop("credentials", None)
    
    return wallet


async def create_user_wallet(
    db: AsyncIOMotorDatabase,
    user_id: str,
    wallet_provider_id: str,
    custom_name: str,
    credentials: Dict[str, str],
    risk_limits: Optional[Dict[str, float]] = None,
    use_testnet: bool = False
) -> Dict[str, Any]:
    """
    Create user wallet connection.
    
    Args:
        db: MongoDB database
        user_id: User ID
        wallet_provider_id: Wallet provider ID
        custom_name: User's custom name
        credentials: Plain credentials (will be encrypted)
        risk_limits: Risk limits (optional)
        use_testnet: Use testnet/demo network (default False for mainnet)
        
    Returns:
        Created user wallet dict
        
    Raises:
        ValueError: If wallet provider doesn't exist or custom_name is duplicate
        
    Example:
        wallet = await create_user_wallet(
            db=db,
            user_id="user_123",
            wallet_provider_id="wallet_001",
            custom_name="My Binance Main",
            credentials={
                "api_key": "abc123",
                "api_secret": "secret456"
            },
            use_testnet=False
        )
    """
    # Validate wallet provider exists
    provider = await db.wallets.find_one({
        "_id": ObjectId(wallet_provider_id),
        "deleted_at": None
    })
    
    if not provider:
        raise ValueError(f"Wallet provider {wallet_provider_id} not found")
    
    if not provider.get("is_active", False):
        raise ValueError(f"Wallet provider {provider['name']} is not active")
    
    # Check custom_name uniqueness for user
    existing = await db.user_wallets.find_one({
        "user_id": user_id,
        "custom_name": custom_name,
        "deleted_at": None
    })
    
    if existing:
        raise ValueError(f"You already have a wallet named '{custom_name}'")
    
    # Encrypt credentials
    encryption = get_encryption_service()
    encrypted_credentials = encryption.encrypt_credentials(credentials)
    
    # Create user wallet
    now = datetime.now(timezone.utc)
    
    user_wallet_data = {
        "user_id": user_id,
        "wallet_provider_id": wallet_provider_id,
        "custom_name": custom_name,
        "is_active": True,
        "use_testnet": use_testnet,
        "credentials": encrypted_credentials,
        "connection_status": UserWalletStatus.DISCONNECTED.value,
        "last_connection_test": None,
        "last_connection_error": None,
        "balance": {},
        "balance_last_synced": None,
        "risk_limits": risk_limits or {
            "max_position_size_usd": 1000.00,
            "daily_loss_limit": 100.00,
            "stop_loss_default_percent": 0.02
        },
        "total_trades": 0,
        "total_pnl": 0.0,
        "last_trade_at": None,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None
    }
    
    result = await db.user_wallets.insert_one(user_wallet_data)
    user_wallet_data["id"] = str(result.inserted_id)
    
    logger.info(
        f"Created user wallet: user={user_id}, provider={provider['name']}, "
        f"name={custom_name}"
    )
    
    # Remove credentials from response
    user_wallet_data.pop("credentials")
    user_wallet_data["wallet_provider_name"] = provider["name"]
    
    return user_wallet_data


async def update_user_wallet(
    db: AsyncIOMotorDatabase,
    user_wallet_id: str,
    user_id: str,
    update_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update user wallet.
    
    Args:
        db: MongoDB database
        user_wallet_id: User wallet ID
        user_id: User ID (for access control)
        update_data: Fields to update
        
    Returns:
        Updated user wallet dict
        
    Example:
        updated = await update_user_wallet(
            db=db,
            user_wallet_id="wallet_123",
            user_id="user_456",
            update_data={
                "custom_name": "My New Name",
                "is_active": False
            }
        )
    """
    # Verify ownership
    existing = await db.user_wallets.find_one({
        "_id": ObjectId(user_wallet_id),
        "user_id": user_id,
        "deleted_at": None
    })
    
    if not existing:
        raise ValueError("User wallet not found")
    
    # Handle credentials encryption
    if "credentials" in update_data:
        encryption = get_encryption_service()
        update_data["credentials"] = encryption.encrypt_credentials(
            update_data["credentials"]
        )
    
    # Update timestamp
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    # Update
    await db.user_wallets.update_one(
        {"_id": ObjectId(user_wallet_id)},
        {"$set": update_data}
    )
    
    # Fetch updated
    updated = await get_user_wallet(db, user_wallet_id, user_id)
    
    logger.info(f"Updated user wallet: {user_wallet_id}")
    
    return updated


async def delete_user_wallet(
    db: AsyncIOMotorDatabase,
    user_wallet_id: str,
    user_id: str
):
    """
    Delete user wallet (soft delete).
    
    Args:
        db: MongoDB database
        user_wallet_id: User wallet ID
        user_id: User ID (for access control)
    """
    # Verify ownership
    existing = await db.user_wallets.find_one({
        "_id": ObjectId(user_wallet_id),
        "user_id": user_id,
        "deleted_at": None
    })
    
    if not existing:
        raise ValueError("User wallet not found")
    
    # Soft delete
    await db.user_wallets.update_one(
        {"_id": ObjectId(user_wallet_id)},
        {"$set": {
            "deleted_at": datetime.now(timezone.utc),
            "is_active": False
        }}
    )
    
    logger.info(f"Deleted user wallet: {user_wallet_id}")


# ==================== WALLET OPERATIONS ====================

async def test_wallet_connection(
    db: AsyncIOMotorDatabase,
    user_wallet_id: str,
    user_id: str
) -> Dict[str, Any]:
    """
    Test wallet connection.
    
    Creates wallet instance and tests connection to exchange/service.
    Updates connection_status in database.
    
    Args:
        db: MongoDB database
        user_wallet_id: User wallet ID
        user_id: User ID (for access control)
        
    Returns:
        Connection test result dict
        
    Example:
        result = await test_wallet_connection(db, "wallet_123", "user_456")
        if result["success"]:
            print(f"Connected! Latency: {result['latency_ms']}ms")
        else:
            print(f"Failed: {result['error']}")
    """
    # Verify ownership
    user_wallet = await db.user_wallets.find_one({
        "_id": ObjectId(user_wallet_id),
        "user_id": user_id,
        "deleted_at": None
    })
    
    if not user_wallet:
        raise ValueError("User wallet not found")
    
    try:
        # Create wallet instance
        factory = get_wallet_factory()
        wallet = await factory.create_wallet_from_db(db, user_wallet_id)
        
        # Test connection
        start_time = datetime.now(timezone.utc)
        result = await wallet.test_connection()
        end_time = datetime.now(timezone.utc)
        
        latency_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # Update database
        await db.user_wallets.update_one(
            {"_id": ObjectId(user_wallet_id)},
            {"$set": {
                "connection_status": UserWalletStatus.CONNECTED.value,
                "last_connection_test": datetime.now(timezone.utc),
                "last_connection_error": None,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        logger.info(f"Connection test successful: {user_wallet_id} (latency: {latency_ms}ms)")
        
        return {
            "success": True,
            "latency_ms": latency_ms,
            "server_time": result.get("server_time"),
            "message": "Connection successful",
            "error": None
        }
    
    except (WalletConnectionError, AuthenticationError) as e:
        # Connection/auth failed
        error_msg = str(e)
        
        await db.user_wallets.update_one(
            {"_id": ObjectId(user_wallet_id)},
            {"$set": {
                "connection_status": UserWalletStatus.ERROR.value,
                "last_connection_error": error_msg,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        logger.warning(f"Connection test failed: {user_wallet_id} - {error_msg}")
        
        return {
            "success": False,
            "latency_ms": 0,
            "server_time": None,
            "message": "Connection failed",
            "error": error_msg
        }
    
    except Exception as e:
        # Unexpected error
        error_msg = f"Unexpected error: {str(e)}"
        
        await db.user_wallets.update_one(
            {"_id": ObjectId(user_wallet_id)},
            {"$set": {
                "connection_status": UserWalletStatus.ERROR.value,
                "last_connection_error": error_msg,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        logger.error(f"Connection test error: {user_wallet_id} - {error_msg}")
        
        return {
            "success": False,
            "latency_ms": 0,
            "server_time": None,
            "message": "Connection test failed",
            "error": error_msg
        }


async def sync_wallet_balance(
    db: AsyncIOMotorDatabase,
    user_wallet_id: str,
    user_id: str
) -> Dict[str, Any]:
    """
    Sync wallet balance from exchange.
    
    Fetches latest balances and updates database.
    Creates sync log entry.
    
    Args:
        db: MongoDB database
        user_wallet_id: User wallet ID
        user_id: User ID (for access control)
        
    Returns:
        Sync result dict
        
    Example:
        result = await sync_wallet_balance(db, "wallet_123", "user_456")
        if result["success"]:
            print(f"Balances: {result['balances']}")
            print(f"Changes: {result['changes']}")
    """
    # Verify ownership
    user_wallet = await db.user_wallets.find_one({
        "_id": ObjectId(user_wallet_id),
        "user_id": user_id,
        "deleted_at": None
    })
    
    if not user_wallet:
        raise ValueError("User wallet not found")
    
    start_time = datetime.now(timezone.utc)
    
    try:
        # Create wallet instance
        factory = get_wallet_factory()
        wallet = await factory.create_wallet_from_db(db, user_wallet_id)
        
        # Fetch balances
        balances_decimal = await wallet.get_all_balances()
        
        # Convert Decimal to float
        balances = {
            asset: float(amount)
            for asset, amount in balances_decimal.items()
        }
        
        end_time = datetime.now(timezone.utc)
        sync_duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # Calculate changes
        old_balances = user_wallet.get("balance", {})
        changes = {}
        
        for asset in set(list(balances.keys()) + list(old_balances.keys())):
            old_val = old_balances.get(asset, 0.0)
            new_val = balances.get(asset, 0.0)
            diff = new_val - old_val
            
            if abs(diff) > 0.00000001:  # Ignore tiny differences
                changes[asset] = diff
        
        # Update database
        await db.user_wallets.update_one(
            {"_id": ObjectId(user_wallet_id)},
            {"$set": {
                "balance": balances,
                "balance_last_synced": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        # Create sync log
        await db.wallet_sync_log.insert_one({
            "user_wallet_id": user_wallet_id,
            "status": SyncStatus.SUCCESS.value,
            "balance_snapshot": balances,
            "balance_changes": changes if changes else None,
            "sync_duration_ms": sync_duration_ms,
            "error_message": None,
            "error_code": None,
            "retry_count": 0,
            "synced_at": datetime.now(timezone.utc),
            "triggered_by": "manual"
        })
        
        logger.info(
            f"Balance sync successful: {user_wallet_id} "
            f"(duration: {sync_duration_ms}ms, changes: {len(changes)} assets)"
        )
        
        # DEPOSIT DETECTION & FLOW TRIGGERING (AI AUTONOMY)
        deposit_detected = False
        deposit_amount_usd = 0.0
        triggered_flows = []
        
        if changes:
            # Check for positive balance changes (deposits)
            # Convert changes to USD for threshold checking
            try:
                # Get current price for major assets (USDT, USD, BTC, ETH)
                from app.infrastructure.market_data.binance_client import BinanceClient
                async with BinanceClient() as binance_client:
                    usdt_price = 1.0  # USDT/USD is always ~1
                    
                    # Calculate total deposit in USD
                    for asset, diff in changes.items():
                        if diff > 0:  # Positive change = deposit
                            deposit_detected = True
                            if asset in ["USDT", "USD", "USDC"]:
                                deposit_amount_usd += diff * usdt_price
                            elif asset == "BTC":
                                try:
                                    btc_price = await binance_client.get_price("BTC/USDT")
                                    deposit_amount_usd += diff * float(btc_price)
                                except:
                                    logger.warning(f"Could not fetch BTC price for deposit calculation")
                            elif asset == "ETH":
                                try:
                                    eth_price = await binance_client.get_price("ETH/USDT")
                                    deposit_amount_usd += diff * float(eth_price)
                                except:
                                    logger.warning(f"Could not fetch ETH price for deposit calculation")
                            else:
                                # For other assets, use a conservative estimate or skip
                                logger.debug(f"Deposit detected for {asset}: {diff}, but USD conversion skipped")
            except Exception as e:
                logger.warning(f"Failed to calculate deposit amount in USD: {e}")
                # Still mark as deposit if we have positive changes
                if any(diff > 0 for diff in changes.values()):
                    deposit_detected = True
        
        # Trigger flows if deposit detected and amount > threshold ($10)
        DEPOSIT_THRESHOLD_USD = 10.0
        if deposit_detected and deposit_amount_usd >= DEPOSIT_THRESHOLD_USD:
            logger.info(
                f"Deposit detected: ${deposit_amount_usd:.2f} USD for user {user_id}. "
                f"Triggering active flows..."
            )
            
            try:
                # Find and trigger active flows for this user
                from app.modules.flows import service as flow_service
                from app.modules.flows.models import FlowStatus
                from bson import ObjectId
                
                # Query active flows for this user
                active_flows = await db.flows.find({
                    "config.user_id": str(user_id),
                    "status": FlowStatus.ACTIVE.value,
                    "config.auto_loop_enabled": True,  # Only trigger flows with auto-loop enabled
                }).to_list(length=100)
                
                if active_flows:
                    logger.info(f"Found {len(active_flows)} active flows for user {user_id}")
                    
                    # Trigger each flow (with throttling to prevent spam)
                    for flow_doc in active_flows:
                        flow_id = str(flow_doc["_id"])
                        
                        # Throttle: Check last execution time (prevent triggers within 30 seconds)
                        try:
                            last_execution = await db.executions.find_one(
                                {"flow_id": ObjectId(flow_id)},
                                sort=[("started_at", -1)]
                            )
                            
                            if last_execution:
                                last_execution_time = last_execution.get("started_at")
                                if last_execution_time:
                                    time_since_last = (datetime.now(timezone.utc) - last_execution_time).total_seconds()
                                    if time_since_last < 30:  # 30 second throttle
                                        logger.debug(
                                            f"Skipping flow {flow_id} trigger: "
                                            f"last execution was {time_since_last:.1f}s ago (< 30s throttle)"
                                        )
                                        continue
                        except Exception as throttle_error:
                            logger.warning(f"Failed to check throttle for flow {flow_id}: {throttle_error}")
                            # Continue anyway - throttle check failure shouldn't block trigger
                        
                        # Trigger flow execution
                        try:
                            flow = await flow_service.get_flow_by_id(db, flow_id)
                            if flow and flow.status == FlowStatus.ACTIVE:
                                # Trigger execution asynchronously to avoid blocking sync
                                import asyncio
                                asyncio.create_task(
                                    flow_service.execute_flow(flow, "groq", None)
                                )
                                triggered_flows.append(flow_id)
                                logger.info(f"Triggered flow {flow_id} ({flow.name}) due to deposit")
                        except Exception as trigger_error:
                            logger.error(f"Failed to trigger flow {flow_id} after deposit: {trigger_error}")
                            # Continue with other flows - don't fail sync if trigger fails
                    
                    if triggered_flows:
                        logger.info(
                            f"Deposit-triggered execution: {len(triggered_flows)} flows triggered "
                            f"for user {user_id} (deposit: ${deposit_amount_usd:.2f} USD)"
                        )
                else:
                    logger.debug(f"No active flows found for user {user_id}")
                    
            except Exception as e:
                logger.error(f"Failed to trigger flows after deposit detection: {e}")
                # Don't fail sync if flow triggering fails
        
        return {
            "success": True,
            "balances": balances,
            "sync_duration_ms": sync_duration_ms,
            "synced_at": datetime.now(timezone.utc),
            "changes": changes,
            "deposit_detected": deposit_detected,
            "deposit_amount_usd": deposit_amount_usd if deposit_detected else 0.0,
            "triggered_flows": triggered_flows,
            "changes": changes if changes else None,
            "error": None
        }
    
    except Exception as e:
        end_time = datetime.now(timezone.utc)
        sync_duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        error_msg = str(e)
        
        # Create sync log (failed)
        await db.wallet_sync_log.insert_one({
            "user_wallet_id": user_wallet_id,
            "status": SyncStatus.FAILED.value,
            "balance_snapshot": None,
            "balance_changes": None,
            "sync_duration_ms": sync_duration_ms,
            "error_message": error_msg,
            "error_code": type(e).__name__,
            "retry_count": 0,
            "synced_at": datetime.now(timezone.utc),
            "triggered_by": "manual"
        })
        
        logger.error(f"Balance sync failed: {user_wallet_id} - {error_msg}")
        
        return {
            "success": False,
            "balances": {},
            "sync_duration_ms": sync_duration_ms,
            "synced_at": datetime.now(timezone.utc),
            "changes": None,
            "error": error_msg
        }


async def get_wallet_sync_logs(
    db: AsyncIOMotorDatabase,
    user_wallet_id: str,
    user_id: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get sync logs for user wallet.
    
    Args:
        db: MongoDB database
        user_wallet_id: User wallet ID
        user_id: User ID (for access control)
        limit: Max number of logs
        
    Returns:
        List of sync log dicts
    """
    # Verify ownership
    user_wallet = await db.user_wallets.find_one({
        "_id": ObjectId(user_wallet_id),
        "user_id": user_id
    })
    
    if not user_wallet:
        raise ValueError("User wallet not found")
    
    logs = await db.wallet_sync_log.find({
        "user_wallet_id": user_wallet_id
    }).sort("synced_at", -1).limit(limit).to_list(length=limit)
    
    for log in logs:
        log["id"] = str(log.pop("_id"))
    
    return logs
