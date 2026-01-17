#!/usr/bin/env python3
"""
Seed script to create default plans in the database.

Usage:
    python scripts/seed_plans.py
"""

import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from app.config.settings import settings
from app.modules.plans.models import Plan

async def seed_plans():
    """Seed default plans into the database."""
    if settings is None:
        print("❌ Settings not loaded. Check your .env file.")
        return False
    
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
        
        db = client[settings.MONGODB_DB_NAME]
        
        # Define default plans
        default_plans = [
            {
                "name": "Free",
                "description": "Perfect for getting started with AI trading. Basic features to explore the platform.",
                "price": 0.0,
                "features": [
                    {
                        "resource": "agents",
                        "title": "1 AI Agent",
                        "description": "Access to one AI trading agent"
                    },
                    {
                        "resource": "api_calls",
                        "title": "1,000 API Calls/Month",
                        "description": "Limited API requests per month"
                    },
                    {
                        "resource": "support",
                        "title": "Community Support",
                        "description": "Access to community forums and documentation"
                    },
                    {
                        "resource": "wallet",
                        "title": "1 Connected Wallet",
                        "description": "Connect one wallet for trading"
                    }
                ],
                "limits": [
                    {
                        "resource": "trades_per_day",
                        "title": "Daily Trades",
                        "description": "Maximum trades per day",
                        "value": 10
                    },
                    {
                        "resource": "agents",
                        "title": "AI Agents",
                        "description": "Maximum number of active agents",
                        "value": 1
                    },
                    {
                        "resource": "position_size",
                        "title": "Max Position Size",
                        "description": "Maximum position size in USD",
                        "value": 1000
                    }
                ]
            },
            {
                "name": "Pro",
                "description": "For serious traders. Advanced features, more agents, and higher limits.",
                "price": 29.0,
                "features": [
                    {
                        "resource": "agents",
                        "title": "5 AI Agents",
                        "description": "Access to up to 5 AI trading agents"
                    },
                    {
                        "resource": "api_calls",
                        "title": "50,000 API Calls/Month",
                        "description": "Generous API request limit"
                    },
                    {
                        "resource": "support",
                        "title": "Priority Email Support",
                        "description": "Faster response times via email"
                    },
                    {
                        "resource": "wallet",
                        "title": "5 Connected Wallets",
                        "description": "Connect multiple wallets for trading"
                    },
                    {
                        "resource": "analytics",
                        "title": "Advanced Analytics",
                        "description": "Detailed performance metrics and insights"
                    },
                    {
                        "resource": "backtesting",
                        "title": "Strategy Backtesting",
                        "description": "Test strategies before deploying"
                    }
                ],
                "limits": [
                    {
                        "resource": "trades_per_day",
                        "title": "Daily Trades",
                        "description": "Maximum trades per day",
                        "value": 100
                    },
                    {
                        "resource": "agents",
                        "title": "AI Agents",
                        "description": "Maximum number of active agents",
                        "value": 5
                    },
                    {
                        "resource": "position_size",
                        "title": "Max Position Size",
                        "description": "Maximum position size in USD",
                        "value": 10000
                    }
                ]
            },
            {
                "name": "Enterprise",
                "description": "For professional traders and teams. Unlimited features, priority support, and custom solutions.",
                "price": 99.0,
                "features": [
                    {
                        "resource": "agents",
                        "title": "Unlimited AI Agents",
                        "description": "No limit on AI trading agents"
                    },
                    {
                        "resource": "api_calls",
                        "title": "Unlimited API Calls",
                        "description": "No API request limits"
                    },
                    {
                        "resource": "support",
                        "title": "24/7 Priority Support",
                        "description": "Round-the-clock dedicated support"
                    },
                    {
                        "resource": "wallet",
                        "title": "Unlimited Wallets",
                        "description": "Connect as many wallets as needed"
                    },
                    {
                        "resource": "analytics",
                        "title": "Enterprise Analytics",
                        "description": "Advanced analytics and custom reports"
                    },
                    {
                        "resource": "backtesting",
                        "title": "Advanced Backtesting",
                        "description": "Comprehensive strategy testing tools"
                    },
                    {
                        "resource": "custom",
                        "title": "Custom Integrations",
                        "description": "Custom API integrations and features"
                    },
                    {
                        "resource": "team",
                        "title": "Team Management",
                        "description": "Multi-user accounts and permissions"
                    }
                ],
                "limits": [
                    {
                        "resource": "trades_per_day",
                        "title": "Daily Trades",
                        "description": "Maximum trades per day",
                        "value": 10000
                    },
                    {
                        "resource": "agents",
                        "title": "AI Agents",
                        "description": "Maximum number of active agents",
                        "value": 999999
                    },
                    {
                        "resource": "position_size",
                        "title": "Max Position Size",
                        "description": "Maximum position size in USD",
                        "value": 1000000
                    }
                ]
            }
        ]
        
        print("Creating plans...")
        created_count = 0
        skipped_count = 0
        
        for plan_data in default_plans:
            # Check if plan already exists
            existing_plan = await Plan.get_plan_by_name(db, plan_data["name"])
            
            if existing_plan:
                print(f"⏭️  Plan '{plan_data['name']}' already exists, skipping...")
                skipped_count += 1
                continue
            
            # Create plan
            plan = await Plan.create_plan(
                db=db,
                name=plan_data["name"],
                description=plan_data["description"],
                price=plan_data["price"],
                features=plan_data["features"],
                limits=plan_data["limits"]
            )
            
            print(f"✅ Created plan: {plan_data['name']} (${plan_data['price']}/month)")
            created_count += 1
        
        print()
        print(f"✅ Seeding complete!")
        print(f"   Created: {created_count} plans")
        print(f"   Skipped: {skipped_count} plans")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Error seeding plans: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(seed_plans())
    sys.exit(0 if success else 1)
