# 🚀 PHASE 2: TRADING INFRASTRUCTURE SETUP - COMPLETE AI IMPLEMENTATION PROMPT

You are an expert FastAPI backend developer tasked with building the **Trading Infrastructure** for the AI Agent Trading Platform. This phase creates all the foundational modules needed for AI-powered automated trading, but does NOT yet connect them for live trading execution (that's Phase 3).

---

## 🎯 YOUR MISSION

Build a comprehensive trading infrastructure with:
- **Wallet abstraction layer** (support ANY exchange/wallet provider)
- **AI agent abstraction layer** (support ANY AI model provider)
- **Prompt management system** (system templates + user custom prompts)
- **Market data pipeline** (OHLC data + technical indicators)
- **Whale alert monitoring** (on-chain large transaction detection)
- **Flow configuration system** (automation workflows - config only, no execution yet)
- **Trade records** (manual trade entry - no auto-execution yet)
- **Risk management** (risk calculation functions)
- **User settings** (preferences and configuration)

**CRITICAL:** Each module should be **fully functional independently** but NOT yet connected for live trading. You're building the pieces; Phase 3 will connect them.

---

## 📋 WHAT YOU NEED TO DO

### **CRITICAL: Test-Driven Development (TDD)**

**YOU MUST FOLLOW THIS ORDER FOR EVERY MODULE:**

1. ✅ **FIRST:** Write comprehensive tests (positive, negative, edge cases)
2. ✅ **SECOND:** Implement the module to make tests pass
3. ✅ **THIRD:** Run tests and verify everything works
4. ✅ **FOURTH:** Document the module (API docs, docstrings, comments)

**DO NOT write implementation before tests!**

---

## 🗄️ DATABASE MODELS YOU WILL CREATE

### **Collections to Implement:**

1. **wallets** - Provider definitions (Binance, Coinbase, MetaMask, etc.)
2. **agents** - AI model definitions (GPT-4, Claude, Gemini, etc.)
3. **prompts** - System prompt templates (admin-managed)
4. **user_prompts** - User custom prompts
5. **user_wallets** - User's connected wallet credentials
6. **user_flows** - Automation workflow configurations
7. **user_trades** - Trade execution records
8. **market_data** - OHLC data + technical indicators (time-series)
9. **whale_alerts** - Large on-chain transaction monitoring
10. **market_sentiment** - Aggregated sentiment data
11. **risk_assessments** - AI risk analysis results
12. **user_settings** - User preferences and configuration

---

## 📁 PROJECT STRUCTURE YOU WILL CREATE

```
backend/
├── app/
│   ├── modules/
│   │   │
│   │   ├── wallets/                     # NEW MODULE
│   │   │   ├── __init__.py
│   │   │   ├── models.py               # Wallet MongoDB model
│   │   │   ├── schemas.py              # Pydantic DTOs
│   │   │   ├── service.py              # Business logic
│   │   │   ├── router.py               # API endpoints
│   │   │   └── providers/              # Provider implementations
│   │   │       ├── __init__.py
│   │   │       ├── base.py             # Abstract base class
│   │   │       ├── binance.py          # Binance implementation
│   │   │       ├── coinbase.py         # Coinbase implementation
│   │   │       └── mock.py             # Mock for testing
│   │   │
│   │   ├── agents/                      # NEW MODULE
│   │   │   ├── __init__.py
│   │   │   ├── models.py               # Agent MongoDB model
│   │   │   ├── schemas.py              # Pydantic DTOs
│   │   │   ├── service.py              # Business logic
│   │   │   ├── router.py               # API endpoints
│   │   │   └── providers/              # AI provider implementations
│   │   │       ├── __init__.py
│   │   │       ├── base.py             # Abstract base class
│   │   │       ├── openai_provider.py  # OpenAI (GPT-4)
│   │   │       ├── anthropic_provider.py # Anthropic (Claude)
│   │   │       ├── google_provider.py  # Google (Gemini)
│   │   │       └── mock.py             # Mock for testing
│   │   │
│   │   ├── prompts/                     # NEW MODULE
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── router.py
│   │   │
│   │   ├── user_prompts/                # NEW MODULE
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── router.py
│   │   │
│   │   ├── user_wallets/                # NEW MODULE
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── router.py
│   │   │
│   │   ├── user_flows/                  # NEW MODULE
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── router.py
│   │   │
│   │   ├── user_trades/                 # NEW MODULE
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── router.py
│   │   │
│   │   ├── market_data/                 # NEW MODULE
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   ├── router.py
│   │   │   ├── indicators.py           # Technical indicator calculations
│   │   │   └── ingestion.py            # Data ingestion service
│   │   │
│   │   ├── whale_alerts/                # NEW MODULE
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   ├── router.py
│   │   │   └── monitoring.py           # Whale monitoring service
│   │   │
│   │   ├── risk_management/             # NEW MODULE
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   ├── router.py
│   │   │   └── calculators.py          # Risk calculation functions
│   │   │
│   │   └── user_settings/               # NEW MODULE
│   │       ├── __init__.py
│   │       ├── models.py
│   │       ├── schemas.py
│   │       ├── service.py
│   │       └── router.py
│   │
│   └── tests/
│       ├── test_wallets.py              # NEW
│       ├── test_agents.py               # NEW
│       ├── test_prompts.py              # NEW
│       ├── test_user_prompts.py         # NEW
│       ├── test_user_wallets.py         # NEW
│       ├── test_user_flows.py           # NEW
│       ├── test_user_trades.py          # NEW
│       ├── test_market_data.py          # NEW
│       ├── test_whale_alerts.py         # NEW
│       ├── test_risk_management.py      # NEW
│       └── test_user_settings.py        # NEW
```

---

## 🔧 IMPLEMENTATION ORDER

Build modules in this exact order (dependencies first):

### **WEEK 1: Provider Abstractions**

#### **MODULE 1: WALLETS (3-4 days)**
- Abstract wallet provider interface
- 2 concrete implementations (Binance + Coinbase)
- Mock provider for testing
- CRUD operations for wallet definitions

#### **MODULE 2: AGENTS (3-4 days)**
- Abstract AI agent interface
- 3 concrete implementations (OpenAI + Anthropic + Google)
- Mock provider for testing
- CRUD operations for agent definitions

---

### **WEEK 2: Content & Configuration**

#### **MODULE 3: PROMPTS (2 days)**
- System prompt templates (admin-managed)
- CRUD operations
- Template parameters

#### **MODULE 4: USER_PROMPTS (2 days)**
- User custom prompts
- CRUD operations
- Fork from system templates

#### **MODULE 5: USER_SETTINGS (1 day)**
- User preferences
- Trading defaults
- Notification settings

---

### **WEEK 3: Market Data & Monitoring**

#### **MODULE 6: MARKET_DATA (4-5 days)**
- OHLC data storage (time-series)
- Technical indicator calculations (RSI, MACD, EMA, Bollinger Bands)
- Data ingestion pipeline
- Caching strategy

#### **MODULE 7: WHALE_ALERTS (2-3 days)**
- On-chain transaction monitoring
- Classification logic
- Significance scoring

---

### **WEEK 4: Trading Infrastructure**

#### **MODULE 8: USER_WALLETS (2 days)**
- User wallet connections
- Credential encryption
- Balance syncing (basic)

#### **MODULE 9: USER_FLOWS (2-3 days)**
- Flow configuration (NO EXECUTION YET)
- Trigger condition definitions
- Risk management settings

#### **MODULE 10: USER_TRADES (2 days)**
- Trade records
- Manual trade entry
- Performance tracking

#### **MODULE 11: RISK_MANAGEMENT (2 days)**
- Risk scoring calculations
- Position sizing
- Risk factor detection

---

## 📊 DETAILED MODULE SPECIFICATIONS

---

## 🏦 MODULE 1: WALLETS

### **Purpose:**
Abstract different wallet/exchange providers so the system can communicate with ANY provider using a generic interface.

### **Database Model (models.py):**

```python
"""
Wallets MongoDB model.

This collection stores wallet provider definitions (Binance, Coinbase, etc.)
that users can connect to their accounts.
"""

from beanie import Document
from datetime import datetime
from typing import List, Dict, Optional


class Wallet(Document):
    """
    Wallet provider definition.
    
    Represents a supported wallet/exchange provider with its configuration.
    """
    
    name: str  # "Binance", "Coinbase", "MetaMask"
    type: str  # "CEX", "DEX", "WALLET"
    provider: str  # "binance", "coinbase", "metamask"
    
    provider_config: Dict = {
        "api_base_url": str,
        "auth_type": str,  # "api_key", "oauth", "web3"
        "supported_operations": List[str],  # ["spot_trading", "futures"]
        "rate_limits": {
            "requests_per_minute": int,
            "requests_per_day": int
        }
    }
    
    supported_currencies: List[str]  # ["BTC", "ETH", "USDT"]
    supported_markets: List[str]  # ["spot", "futures", "margin"]
    
    fees: Dict = {
        "trading_fee_percent": float,
        "withdrawal_fee": Dict[str, float]  # {"BTC": 0.0005}
    }
    
    is_active: bool = True
    logo_url: Optional[str] = None
    documentation_url: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False
    
    class Settings:
        name = "wallets"
        indexes = [
            "provider",
            "is_active",
            "is_deleted"
        ]
```

### **Provider Interface (providers/base.py):**

```python
"""
Abstract base class for wallet providers.

All wallet providers must implement this interface to ensure consistent
communication regardless of the underlying exchange/wallet API.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class WalletProvider(ABC):
    """
    Abstract wallet provider interface.
    
    Implements the Strategy Pattern to abstract different wallet providers.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize wallet provider with configuration.
        
        Args:
            config: Provider-specific configuration
        """
        self.config = config
    
    @abstractmethod
    async def validate_credentials(self, credentials: Dict) -> bool:
        """
        Validate user credentials for this provider.
        
        Args:
            credentials: User's API keys, secrets, etc.
            
        Returns:
            bool: True if credentials are valid
            
        Raises:
            InvalidCredentialsError: If credentials are invalid
        """
        pass
    
    @abstractmethod
    async def get_balance(self, credentials: Dict) -> Dict[str, float]:
        """
        Get account balance for all assets.
        
        Args:
            credentials: User's credentials
            
        Returns:
            Dict mapping currency to amount: {"BTC": 0.5, "ETH": 2.3}
        """
        pass
    
    @abstractmethod
    async def get_markets(self) -> List[Dict]:
        """
        Get available trading markets/pairs.
        
        Returns:
            List of market information
        """
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Dict:
        """
        Get current ticker price for a symbol.
        
        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            
        Returns:
            Dict with price info: {"symbol": "BTC/USDT", "price": 67500.0}
        """
        pass
    
    @abstractmethod
    async def get_order_history(
        self, 
        credentials: Dict, 
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get order history.
        
        Args:
            credentials: User's credentials
            symbol: Optional filter by trading pair
            limit: Max number of orders to return
            
        Returns:
            List of order records
        """
        pass
    
    @abstractmethod
    async def place_order(
        self, 
        credentials: Dict, 
        symbol: str,
        side: str,  # "buy" or "sell"
        order_type: str,  # "market", "limit"
        quantity: float,
        price: Optional[float] = None
    ) -> Dict:
        """
        Place a trading order.
        
        Args:
            credentials: User's credentials
            symbol: Trading pair
            side: "buy" or "sell"
            order_type: "market" or "limit"
            quantity: Amount to trade
            price: Limit price (required for limit orders)
            
        Returns:
            Order confirmation with order_id
        """
        pass
    
    @abstractmethod
    async def cancel_order(
        self, 
        credentials: Dict, 
        order_id: str,
        symbol: str
    ) -> bool:
        """
        Cancel an open order.
        
        Args:
            credentials: User's credentials
            order_id: Order ID to cancel
            symbol: Trading pair
            
        Returns:
            bool: True if cancelled successfully
        """
        pass
```

### **Concrete Implementation Example (providers/binance.py):**

```python
"""
Binance wallet provider implementation.

Implements the WalletProvider interface for Binance exchange.
"""

from app.modules.wallets.providers.base import WalletProvider
from typing import Dict, List, Optional
import aiohttp


class BinanceProvider(WalletProvider):
    """Binance exchange provider."""
    
    async def validate_credentials(self, credentials: Dict) -> bool:
        """Validate Binance API keys."""
        # TODO: Implement Binance API key validation
        # Make request to /api/v3/account with signature
        pass
    
    async def get_balance(self, credentials: Dict) -> Dict[str, float]:
        """Get Binance account balance."""
        # TODO: Implement Binance balance fetching
        # GET /api/v3/account
        pass
    
    # ... implement all other methods
```

### **API Endpoints (router.py):**

```python
"""
Wallets router.

Endpoints for managing wallet provider definitions (admin only).
"""

from fastapi import APIRouter, Depends, status
from typing import List
from app.modules.wallets.schemas import WalletCreate, WalletUpdate, WalletResponse
from app.core.dependencies import require_permission


router = APIRouter(
    prefix="/api/v1/wallets",
    tags=["Wallets"]
)


@router.get(
    "",
    response_model=List[WalletResponse],
    summary="List all wallet providers",
    description="""
    Get a list of all supported wallet/exchange providers.
    
    **Returns:**
    - List of wallet providers with configuration
    - Includes only active providers by default
    
    **Accessible to:** All authenticated users
    """
)
async def list_wallets(
    include_inactive: bool = False
):
    """List all wallet providers."""
    pass


@router.get(
    "/{wallet_id}",
    response_model=WalletResponse,
    summary="Get wallet provider by ID"
)
async def get_wallet(wallet_id: str):
    """Get specific wallet provider details."""
    pass


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=WalletResponse,
    summary="Create new wallet provider",
    description="Create a new wallet provider definition. Admin only.",
    dependencies=[Depends(require_permission("wallets", "write"))]
)
async def create_wallet(wallet_data: WalletCreate):
    """Create new wallet provider."""
    pass


@router.put(
    "/{wallet_id}",
    response_model=WalletResponse,
    summary="Update wallet provider",
    dependencies=[Depends(require_permission("wallets", "write"))]
)
async def update_wallet(wallet_id: str, wallet_data: WalletUpdate):
    """Update wallet provider configuration."""
    pass


@router.delete(
    "/{wallet_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete wallet provider",
    dependencies=[Depends(require_permission("wallets", "delete"))]
)
async def delete_wallet(wallet_id: str):
    """Soft delete wallet provider."""
    pass
```

### **Tests (tests/test_wallets.py):**

```python
"""
Tests for wallets module.

Comprehensive tests covering:
- CRUD operations
- Provider validation
- Permission checks
- Error cases
"""

import pytest
from httpx import AsyncClient


class TestWalletsCRUD:
    """Test wallet CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_list_wallets_returns_active_only(self, client: AsyncClient):
        """
        Test listing wallets returns only active providers.
        
        Positive test case:
        - Should return 200
        - Should return list of active wallets
        - Should not include inactive wallets
        """
        pass
    
    @pytest.mark.asyncio
    async def test_create_wallet_as_admin_success(
        self, 
        client: AsyncClient,
        admin_token: str
    ):
        """
        Test admin can create new wallet provider.
        
        Positive test case:
        - Should return 201
        - Should create wallet in database
        - Should return wallet with ID
        """
        pass
    
    @pytest.mark.asyncio
    async def test_create_wallet_as_user_forbidden(
        self,
        client: AsyncClient,
        user_token: str
    ):
        """
        Test regular user cannot create wallet provider.
        
        Negative test case:
        - Should return 403
        - Should not create wallet
        """
        pass
    
    @pytest.mark.asyncio
    async def test_create_wallet_with_duplicate_provider_fails(
        self,
        client: AsyncClient,
        admin_token: str
    ):
        """
        Test cannot create duplicate provider.
        
        Negative test case:
        - Should return 400
        - Should have error: DUPLICATE_PROVIDER
        """
        pass
    
    # Add 20+ more test cases for all operations and edge cases
```

---

## 🤖 MODULE 2: AGENTS

### **Purpose:**
Abstract different AI model providers so the system can use ANY AI model with the same interface.

### **Database Model:**

```python
"""Agents MongoDB model."""

from beanie import Document
from datetime import datetime
from typing import List, Dict, Optional


class Agent(Document):
    """
    AI agent/model definition.
    
    Represents an AI model from any provider (OpenAI, Anthropic, Google, etc.)
    """
    
    name: str  # "GPT-4 Turbo", "Claude Sonnet 4"
    provider: str  # "openai", "anthropic", "google"
    model_id: str  # "gpt-4-turbo", "claude-sonnet-4"
    version: str  # "1.0"
    
    capabilities: List[str]  # ["trading_analysis", "risk_assessment"]
    specialization: str  # "crypto", "forex", "multi_asset"
    
    provider_config: Dict = {
        "api_base_url": str,
        "auth_type": str,
        "max_tokens": int,
        "temperature_range": {
            "min": float,
            "max": float,
            "default": float
        }
    }
    
    pricing: Dict = {
        "cost_per_1k_tokens": float,
        "cost_per_call": Optional[float]
    }
    
    performance_metrics: Dict = {
        "avg_response_time_ms": int,
        "success_rate_percent": float,
        "avg_accuracy_percent": Optional[float]
    }
    
    context_window: int  # Max tokens in context
    is_active: bool = True
    logo_url: Optional[str] = None
    description: str
    
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False
    
    class Settings:
        name = "agents"
        indexes = [
            "provider",
            "model_id",
            "is_active",
            "is_deleted"
        ]
```

### **Provider Interface (providers/base.py):**

```python
"""
Abstract base class for AI agent providers.

All AI providers must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
from pydantic import BaseModel


class AIResponse(BaseModel):
    """Standardized AI response format."""
    
    recommendation: str  # "BUY", "SELL", "HOLD"
    confidence: float  # 0-100
    reasoning: str  # Why the AI made this decision
    suggested_entry: Optional[float] = None
    suggested_stop_loss: Optional[float] = None
    suggested_take_profit: Optional[float] = None
    risk_score: float  # 0-100
    additional_data: Optional[Dict] = None


class AIAgent(ABC):
    """
    Abstract AI agent interface.
    
    Implements Strategy Pattern for AI providers.
    """
    
    def __init__(self, config: Dict):
        """Initialize AI agent with configuration."""
        self.config = config
    
    @abstractmethod
    async def analyze_market(
        self, 
        prompt: str, 
        market_data: Dict,
        config: Optional[Dict] = None
    ) -> AIResponse:
        """
        Analyze market data and provide trading recommendation.
        
        Args:
            prompt: Trading strategy prompt
            market_data: Current market data (OHLC, indicators, etc.)
            config: Optional model configuration (temperature, max_tokens)
            
        Returns:
            AIResponse with recommendation and reasoning
        """
        pass
    
    @abstractmethod
    async def assess_risk(
        self, 
        trade_data: Dict, 
        portfolio: Dict
    ) -> Dict:
        """
        Assess risk for a proposed trade.
        
        Args:
            trade_data: Proposed trade details
            portfolio: Current portfolio state
            
        Returns:
            Risk assessment with score and factors
        """
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict) -> bool:
        """
        Validate model configuration.
        
        Args:
            config: Model config to validate
            
        Returns:
            bool: True if valid
        """
        pass
```

### **Implementation Pattern:**
Follow same structure as Wallets:
- Concrete implementations: OpenAI, Anthropic, Google, Mock
- CRUD router with permission checks
- Comprehensive tests (positive, negative, edge cases)

---

## 📊 MODULE 6: MARKET_DATA

### **Purpose:**
Store OHLC (Open, High, Low, Close) data and calculate technical indicators for AI agents to use in decision-making.

### **Database Model:**

```python
"""Market data MongoDB model (time-series)."""

from beanie import Document
from datetime import datetime
from typing import Dict, Optional


class MarketData(Document):
    """
    Market OHLC data with technical indicators.
    
    Time-series data for crypto/forex markets.
    """
    
    symbol: str  # "BTC/USDT"
    exchange: str  # "binance"
    timeframe: str  # "1m", "5m", "1h", "1d"
    timestamp: datetime
    
    # OHLC Data
    open: float
    high: float
    low: float
    close: float
    volume: float
    trades_count: Optional[int] = None
    
    # Technical Indicators (calculated)
    indicators: Dict = {
        "RSI_14": Optional[float],
        "MACD": Optional[Dict],  # {macd_line, signal_line, histogram}
        "EMA_50": Optional[float],
        "EMA_200": Optional[float],
        "SMA_20": Optional[float],
        "bollinger_bands": Optional[Dict],  # {upper, middle, lower}
        "volume_sma_20": Optional[float],
        "atr_14": Optional[float]
    }
    
    created_at: datetime
    
    class Settings:
        name = "market_data"
        indexes = [
            [("symbol", 1), ("timeframe", 1), ("timestamp", -1)],
            "timestamp",
            "exchange"
        ]
        timeseries = {
            "timeField": "timestamp",
            "metaField": "symbol",
            "granularity": "minutes"
        }
```

### **Indicator Calculations (indicators.py):**

```python
"""
Technical indicator calculation functions.

Implements common trading indicators:
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- EMA (Exponential Moving Average)
- Bollinger Bands
- ATR (Average True Range)
"""

from typing import List, Dict
import pandas as pd


def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """
    Calculate Relative Strength Index.
    
    Args:
        prices: List of closing prices
        period: RSI period (default 14)
        
    Returns:
        float: RSI value (0-100)
    """
    # TODO: Implement RSI calculation
    # 1. Calculate price changes
    # 2. Separate gains and losses
    # 3. Calculate average gain and loss
    # 4. Calculate RS (Relative Strength)
    # 5. Calculate RSI = 100 - (100 / (1 + RS))
    pass


def calculate_macd(
    prices: List[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> Dict:
    """
    Calculate MACD indicator.
    
    Args:
        prices: List of closing prices
        fast_period: Fast EMA period
        slow_period: Slow EMA period
        signal_period: Signal line period
        
    Returns:
        Dict with macd_line, signal_line, histogram
    """
    # TODO: Implement MACD calculation
    pass


def calculate_ema(prices: List[float], period: int) -> float:
    """
    Calculate Exponential Moving Average.
    
    Args:
        prices: List of closing prices
        period: EMA period
        
    Returns:
        float: EMA value
    """
    # TODO: Implement EMA calculation
    pass


def calculate_bollinger_bands(
    prices: List[float],
    period: int = 20,
    std_dev: float = 2.0
) -> Dict:
    """
    Calculate Bollinger Bands.
    
    Args:
        prices: List of closing prices
        period: SMA period
        std_dev: Standard deviation multiplier
        
    Returns:
        Dict with upper, middle, lower bands
    """
    # TODO: Implement Bollinger Bands calculation
    pass


def calculate_atr(
    high: List[float],
    low: List[float],
    close: List[float],
    period: int = 14
) -> float:
    """
    Calculate Average True Range (volatility indicator).
    
    Args:
        high: List of high prices
        low: List of low prices
        close: List of close prices
        period: ATR period
        
    Returns:
        float: ATR value
    """
    # TODO: Implement ATR calculation
    pass
```

### **Data Ingestion Service (ingestion.py):**

```python
"""
Market data ingestion service.

Background service that fetches OHLC data from exchanges and calculates indicators.
"""

from datetime import datetime, timedelta
from typing import List
from app.modules.market_data.models import MarketData
from app.modules.market_data.indicators import (
    calculate_rsi,
    calculate_macd,
    calculate_ema,
    calculate_bollinger_bands,
    calculate_atr
)


class MarketDataIngestionService:
    """
    Background service for ingesting market data.
    
    Runs periodically to fetch and store OHLC data with indicators.
    """
    
    def __init__(self):
        """Initialize ingestion service."""
        self.symbols = ["BTC/USDT", "ETH/USDT"]  # TODO: Make configurable
        self.timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]
        self.exchanges = ["binance"]
    
    async def ingest_data(self, symbol: str, timeframe: str, exchange: str):
        """
        Ingest OHLC data for a symbol/timeframe.
        
        Args:
            symbol: Trading pair
            timeframe: Candlestick timeframe
            exchange: Exchange to fetch from
        """
        # TODO: Implement data ingestion
        # 1. Fetch OHLC data from exchange API
        # 2. Calculate all technical indicators
        # 3. Store in MarketData collection
        # 4. Cache in Redis
        pass
    
    async def run_ingestion_cycle(self):
        """
        Run one complete ingestion cycle for all symbols/timeframes.
        
        This should be called by a background task scheduler (Celery/ARQ).
        ```python
        """
        for symbol in self.symbols:
            for timeframe in self.timeframes:
                for exchange in self.exchanges:
                    try:
                        await self.ingest_data(symbol, timeframe, exchange)
                    except Exception as e:
                        # Log error but continue with other symbols
                        logger.error(f"Failed to ingest {symbol} {timeframe}: {e}")
    
    async def backfill_historical_data(
        self,
        symbol: str,
        timeframe: str,
        exchange: str,
        start_date: datetime,
        end_date: datetime
    ):
        """
        Backfill historical market data.
        
        Args:
            symbol: Trading pair
            timeframe: Candlestick timeframe
            exchange: Exchange to fetch from
            start_date: Start date for backfill
            end_date: End date for backfill
        """
        # TODO: Implement historical data backfill
        # Useful for testing and training AI models
        pass
```

### **API Endpoints (router.py):**

```python
"""
Market data router.

Endpoints for accessing OHLC data and technical indicators.
"""

from fastapi import APIRouter, Query
from datetime import datetime
from typing import List, Optional
from app.modules.market_data.schemas import MarketDataResponse, IndicatorQuery


router = APIRouter(
    prefix="/api/v1/market-data",
    tags=["Market Data"]
)


@router.get(
    "",
    response_model=List[MarketDataResponse],
    summary="Get market OHLC data with indicators",
    description="""
    Retrieve OHLC (Open, High, Low, Close) candlestick data with calculated technical indicators.
    
    **Use Cases:**
    - Display charts in frontend
    - Feed data to AI agents for analysis
    - Backtest trading strategies
    
    **Data Included:**
    - OHLC prices
    - Volume
    - Technical indicators: RSI, MACD, EMA, Bollinger Bands, ATR
    
    **Caching:**
    - Data is cached in Redis for 1 minute
    - Historical data cached for 1 hour
    
    **Rate Limiting:**
    - 100 requests/minute for regular users
    - Unlimited for admins
    """
)
async def get_market_data(
    symbol: str = Query(..., description="Trading pair (e.g., BTC/USDT)"),
    timeframe: str = Query("1h", description="Timeframe: 1m, 5m, 15m, 1h, 4h, 1d"),
    exchange: str = Query("binance", description="Exchange name"),
    start_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    limit: int = Query(100, ge=1, le=1000, description="Max candles to return")
):
    """
    Get OHLC market data with technical indicators.
    
    Args:
        symbol: Trading pair
        timeframe: Candlestick timeframe
        exchange: Exchange to query
        start_time: Optional start time filter
        end_time: Optional end time filter
        limit: Max number of candles
        
    Returns:
        List of market data candles with indicators
    """
    pass


@router.get(
    "/latest",
    response_model=MarketDataResponse,
    summary="Get latest market data",
    description="Get the most recent market data candle for a symbol."
)
async def get_latest_market_data(
    symbol: str = Query(..., description="Trading pair"),
    timeframe: str = Query("1h", description="Timeframe"),
    exchange: str = Query("binance", description="Exchange")
):
    """Get latest market data candle."""
    pass


@router.get(
    "/indicators",
    summary="Get specific indicators only",
    description="""
    Get only technical indicators without full OHLC data.
    
    **Use Case:**
    - Lightweight endpoint for checking indicator values
    - Used by AI agents for quick analysis
    """
)
async def get_indicators(
    symbol: str,
    timeframe: str = "1h",
    exchange: str = "binance",
    indicators: List[str] = Query(
        ["RSI_14", "MACD", "EMA_50"],
        description="List of indicators to return"
    )
):
    """Get specific technical indicators."""
    pass


@router.post(
    "/backfill",
    status_code=202,
    summary="Trigger historical data backfill",
    description="Trigger background job to backfill historical data. Admin only.",
    dependencies=[Depends(require_permission("market_data", "write"))]
)
async def trigger_backfill(
    symbol: str,
    timeframe: str,
    exchange: str,
    start_date: datetime,
    end_date: datetime
):
    """
    Trigger historical data backfill.
    
    This starts a background job to fetch and store historical data.
    """
    pass
```

---

## 🐋 MODULE 7: WHALE_ALERTS

### **Purpose:**
Monitor blockchain for large transactions (whales) that might indicate market movements.

### **Database Model:**

```python
"""Whale alerts MongoDB model."""

from beanie import Document
from datetime import datetime
from typing import Optional


class WhaleAlert(Document):
    """
    On-chain large transaction alert.
    
    Tracks significant cryptocurrency movements that might impact markets.
    """
    
    blockchain: str  # "ethereum", "bitcoin", "binance_smart_chain"
    transaction_hash: str  # Unique transaction ID
    
    from_address: str
    to_address: str
    from_label: Optional[str] = None  # "Binance Hot Wallet"
    to_label: Optional[str] = None  # "Unknown"
    
    # Transaction Details
    currency: str  # "BTC", "ETH", "USDT"
    amount: float
    amount_usd: float
    
    # Classification
    transaction_type: str  # "exchange_inflow", "exchange_outflow", "whale_transfer"
    significance_score: float  # 1-10 (how significant)
    
    # Market Impact (tracked after detection)
    price_before: Optional[float] = None
    price_after: Optional[float] = None
    price_change_percent: Optional[float] = None
    
    timestamp: datetime  # When transaction occurred
    detected_at: datetime  # When we detected it
    created_at: datetime
    
    class Settings:
        name = "whale_alerts"
        indexes = [
            "transaction_hash",
            "currency",
            "transaction_type",
            [("timestamp", -1)],
            "significance_score"
        ]
```

### **Monitoring Service (monitoring.py):**

```python
"""
Whale alert monitoring service.

Background service that monitors blockchain for large transactions.
"""

from datetime import datetime
from typing import Dict, Optional
from app.modules.whale_alerts.models import WhaleAlert
import aiohttp


class WhaleMonitoringService:
    """
    Service for monitoring whale transactions.
    
    Monitors blockchains and classifies significant transactions.
    """
    
    def __init__(self):
        """Initialize whale monitoring service."""
        self.min_amount_usd = 1_000_000  # $1M minimum to be considered
        self.known_addresses = {}  # TODO: Load from database/config
    
    async def monitor_blockchain(self, blockchain: str):
        """
        Monitor a blockchain for large transactions.
        
        Args:
            blockchain: Blockchain to monitor
        """
        # TODO: Implement blockchain monitoring
        # Options:
        # 1. Use Whale Alert API (paid service)
        # 2. Use blockchain explorer APIs (Etherscan, etc.)
        # 3. Run own blockchain nodes (advanced)
        pass
    
    def classify_transaction(
        self,
        from_address: str,
        to_address: str,
        amount_usd: float
    ) -> Dict:
        """
        Classify a transaction and calculate significance score.
        
        Args:
            from_address: Source address
            to_address: Destination address
            amount_usd: Transaction value in USD
            
        Returns:
            Dict with transaction_type and significance_score
        """
        # TODO: Implement classification logic
        
        # Classification rules:
        # 1. Exchange inflow = from unknown to known exchange
        #    - Bearish signal (potential selling)
        # 2. Exchange outflow = from known exchange to unknown
        #    - Bullish signal (accumulation)
        # 3. Whale-to-whale = between unknown addresses
        #    - Neutral (but watch for patterns)
        
        # Significance score factors:
        # - Transaction size (larger = higher)
        # - Known addresses involved
        # - Timing (multiple whales moving = higher)
        # - Historical correlation with price moves
        
        transaction_type = "unknown"
        significance_score = 5.0
        
        # Determine if addresses are exchanges
        from_is_exchange = self._is_exchange_address(from_address)
        to_is_exchange = self._is_exchange_address(to_address)
        
        if not from_is_exchange and to_is_exchange:
            transaction_type = "exchange_inflow"
            significance_score = 7.0  # Potentially bearish
        elif from_is_exchange and not to_is_exchange:
            transaction_type = "exchange_outflow"
            significance_score = 8.0  # Potentially bullish
        elif not from_is_exchange and not to_is_exchange:
            transaction_type = "whale_transfer"
            significance_score = 6.0
        
        # Adjust score based on amount
        if amount_usd > 10_000_000:  # $10M+
            significance_score = min(10.0, significance_score + 2.0)
        elif amount_usd > 50_000_000:  # $50M+
            significance_score = 10.0
        
        return {
            "transaction_type": transaction_type,
            "significance_score": significance_score
        }
    
    def _is_exchange_address(self, address: str) -> bool:
        """
        Check if address belongs to a known exchange.
        
        Args:
            address: Wallet address
            
        Returns:
            bool: True if known exchange address
        """
        # TODO: Check against database of known exchange addresses
        return address in self.known_addresses
    
    async def track_price_impact(self, alert_id: str):
        """
        Track price movement after a whale alert.
        
        Args:
            alert_id: Whale alert ID to track
        """
        # TODO: Implement price impact tracking
        # 1. Get price before transaction
        # 2. Wait 1 hour
        # 3. Get price after
        # 4. Calculate change
        # 5. Update whale alert record
        pass
    
    async def run_monitoring_cycle(self):
        """
        Run one complete monitoring cycle.
        
        Called by background task scheduler.
        """
        blockchains = ["ethereum", "bitcoin", "binance_smart_chain"]
        
        for blockchain in blockchains:
            try:
                await self.monitor_blockchain(blockchain)
            except Exception as e:
                logger.error(f"Failed to monitor {blockchain}: {e}")
```

### **API Endpoints (router.py):**

```python
"""
Whale alerts router.

Endpoints for accessing whale transaction data.
"""

from fastapi import APIRouter, Query
from datetime import datetime, timedelta
from typing import List, Optional


router = APIRouter(
    prefix="/api/v1/whale-alerts",
    tags=["Whale Alerts"]
)


@router.get(
    "",
    summary="Get whale alerts",
    description="""
    Retrieve whale transaction alerts.
    
    **What are Whale Alerts?**
    Large cryptocurrency transactions (typically $1M+) that might indicate:
    - Institutional movements
    - Potential market manipulation
    - Accumulation or distribution patterns
    
    **Transaction Types:**
    - **exchange_inflow**: Tokens moved TO exchange (potentially bearish)
    - **exchange_outflow**: Tokens moved FROM exchange (potentially bullish)
    - **whale_transfer**: Large transfer between unknown wallets
    
    **Use Cases:**
    - Set up flow triggers based on whale activity
    - Monitor market sentiment
    - Identify potential price movements before they happen
    """
)
async def get_whale_alerts(
    currency: Optional[str] = Query(None, description="Filter by currency (BTC, ETH)"),
    transaction_type: Optional[str] = Query(None, description="Filter by type"),
    min_amount_usd: Optional[float] = Query(None, description="Minimum USD amount"),
    min_significance: Optional[float] = Query(None, ge=1, le=10, description="Min significance score"),
    start_time: Optional[datetime] = Query(None, description="Start time"),
    end_time: Optional[datetime] = Query(None, description="End time"),
    limit: int = Query(50, ge=1, le=500)
):
    """Get whale alerts with filters."""
    pass


@router.get(
    "/recent",
    summary="Get recent whale alerts",
    description="Get the most recent whale alerts from the last 24 hours."
)
async def get_recent_whale_alerts(
    limit: int = Query(20, ge=1, le=100)
):
    """Get recent whale alerts (last 24h)."""
    pass


@router.get(
    "/{alert_id}",
    summary="Get whale alert by ID",
    description="Get detailed information about a specific whale transaction."
)
async def get_whale_alert(alert_id: str):
    """Get specific whale alert details."""
    pass


@router.get(
    "/stats",
    summary="Get whale activity statistics",
    description="""
    Get aggregated statistics about whale activity.
    
    **Returned Data:**
    - Total alerts in time period
    - Total volume moved (USD)
    - Breakdown by transaction type
    - Most active currencies
    - Average significance score
    """
)
async def get_whale_statistics(
    currency: Optional[str] = None,
    days: int = Query(7, ge=1, le=90, description="Days to analyze")
):
    """Get whale activity statistics."""
    pass
```

---

## 🔄 MODULE 9: USER_FLOWS

### **Purpose:**
Allow users to configure automated trading workflows that combine AI agents, prompts, and market conditions. **NOTE:** This module only handles configuration; actual execution happens in Phase 3.

### **Database Model:**

```python
"""User flows MongoDB model."""

from beanie import Document
from datetime import datetime
from typing import List, Dict, Optional
from bson import ObjectId


class UserFlow(Document):
    """
    User automation workflow configuration.
    
    Defines a multi-step workflow combining prompts, agents, and market conditions.
    Phase 2: Configuration only. Phase 3: Execution engine.
    """
    
    user_id: ObjectId
    title: str
    description: str
    
    # Workflow steps (executed in order)
    flow_steps: List[Dict] = [
        {
            "step_number": int,  # 0, 1, 2, ...
            "prompt_id": Optional[ObjectId],  # System prompt
            "user_prompt_id": Optional[ObjectId],  # User custom prompt
            "agent_id": ObjectId,  # Which AI agent to use
            "agent_config": {
                "temperature": float,  # 0.0-1.0
                "max_tokens": int,
                "custom_parameters": Dict
            },
            "expected_output": str  # "trading_signal", "risk_assessment"
        }
    ]
    
    # Trigger conditions (when should this flow run?)
    trigger_conditions: Dict = {
        "type": str,  # "manual", "scheduled", "market_condition", "whale_alert"
        "schedule": Optional[str],  # Cron expression for scheduled runs
        "market_conditions": Optional[Dict],  # Price/indicator conditions
        "whale_conditions": Optional[Dict]  # Whale alert conditions
    }
    
    # Risk management settings
    risk_management: Dict = {
        "max_position_size_usd": float,
        "max_loss_per_trade_percent": float,
        "stop_loss_percent": float,
        "take_profit_percent": float,
        "max_daily_trades": int,
        "max_concurrent_trades": int
    }
    
    # Execution settings
    target_wallet_id: ObjectId  # Which wallet to trade with
    target_markets: List[str]  # ["BTC/USDT", "ETH/USDT"]
    
    # Status
    status: str  # "active", "paused", "stopped", "error"
    
    # Execution statistics (tracked in Phase 3)
    execution_stats: Dict = {
        "total_runs": int,
        "successful_runs": int,
        "failed_runs": int,
        "total_trades_executed": int,
        "total_profit_loss_usd": float,
        "last_run_at": Optional[datetime],
        "next_run_at": Optional[datetime]
    }
    
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False
    
    class Settings:
        name = "user_flows"
        indexes = [
            "user_id",
            "status",
            [("user_id", 1), ("status", 1)],
            "is_deleted"
        ]
```

### **Schemas (schemas.py):**

```python
"""User flows Pydantic schemas."""

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional
from datetime import datetime


class FlowStepCreate(BaseModel):
    """Single step in a flow."""
    
    step_number: int = Field(ge=0, description="Step order (0-based)")
    prompt_id: Optional[str] = Field(None, description="System prompt ID")
    user_prompt_id: Optional[str] = Field(None, description="User prompt ID")
    agent_id: str = Field(..., description="AI agent ID")
    agent_config: Dict = Field(
        default={
            "temperature": 0.7,
            "max_tokens": 2000
        },
        description="Agent configuration"
    )
    expected_output: str = Field(
        ...,
        description="Expected output type: trading_signal, risk_assessment, market_analysis"
    )
    
    @field_validator("expected_output")
    @classmethod
    def validate_output_type(cls, v: str) -> str:
        """Validate expected output type."""
        valid_outputs = ["trading_signal", "risk_assessment", "market_analysis"]
        if v not in valid_outputs:
            raise ValueError(f"Invalid output type. Must be one of: {valid_outputs}")
        return v


class TriggerConditions(BaseModel):
    """Flow trigger conditions."""
    
    type: str = Field(
        ...,
        description="Trigger type: manual, scheduled, market_condition, whale_alert"
    )
    schedule: Optional[str] = Field(
        None,
        description="Cron expression for scheduled triggers"
    )
    market_conditions: Optional[Dict] = Field(
        None,
        description="Market condition triggers",
        example={
            "BTC/USDT": {
                "price_above": 50000,
                "RSI_14": {"below": 30}
            }
        }
    )
    whale_conditions: Optional[Dict] = Field(
        None,
        description="Whale alert triggers",
        example={
            "currency": "BTC",
            "min_amount_usd": 10000000,
            "transaction_type": "exchange_outflow"
        }
    )


class RiskManagement(BaseModel):
    """Risk management settings."""
    
    max_position_size_usd: float = Field(
        ...,
        gt=0,
        description="Maximum position size in USD"
    )
    max_loss_per_trade_percent: float = Field(
        ...,
        gt=0,
        le=100,
        description="Max loss per trade as % of position"
    )
    stop_loss_percent: float = Field(
        ...,
        gt=0,
        le=100,
        description="Stop loss percentage"
    )
    take_profit_percent: float = Field(
        ...,
        gt=0,
        description="Take profit percentage"
    )
    max_daily_trades: int = Field(
        ...,
        ge=1,
        description="Maximum trades per day"
    )
    max_concurrent_trades: int = Field(
        ...,
        ge=1,
        description="Maximum concurrent open trades"
    )


class UserFlowCreate(BaseModel):
    """Create new user flow."""
    
    title: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    flow_steps: List[FlowStepCreate] = Field(..., min_items=1)
    trigger_conditions: TriggerConditions
    risk_management: RiskManagement
    target_wallet_id: str = Field(..., description="Wallet to use for trading")
    target_markets: List[str] = Field(
        ...,
        min_items=1,
        description="Trading pairs to monitor"
    )
    
    @field_validator("flow_steps")
    @classmethod
    def validate_flow_steps(cls, v: List[FlowStepCreate]) -> List[FlowStepCreate]:
        """Validate flow steps are properly ordered."""
        step_numbers = [step.step_number for step in v]
        expected = list(range(len(v)))
        if step_numbers != expected:
            raise ValueError("Flow steps must be numbered sequentially starting from 0")
        return v


class UserFlowUpdate(BaseModel):
    """Update existing user flow."""
    
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    flow_steps: Optional[List[FlowStepCreate]] = None
    trigger_conditions: Optional[TriggerConditions] = None
    risk_management: Optional[RiskManagement] = None
    target_wallet_id: Optional[str] = None
    target_markets: Optional[List[str]] = None
    status: Optional[str] = Field(None, description="active, paused, stopped")


class UserFlowResponse(BaseModel):
    """User flow response."""
    
    id: str
    user_id: str
    title: str
    description: str
    flow_steps: List[Dict]
    trigger_conditions: Dict
    risk_management: Dict
    target_wallet_id: str
    target_markets: List[str]
    status: str
    execution_stats: Dict
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "user_id": "507f1f77bcf86cd799439012",
                "title": "BTC Trend Following Bot",
                "description": "Automated BTC trading using AI trend analysis",
                "flow_steps": [
                    {
                        "step_number": 0,
                        "prompt_id": "trend-analysis-prompt-id",
                        "agent_id": "claude-sonnet-4-id",
                        "agent_config": {"temperature": 0.3},
                        "expected_output": "trading_signal"
                    }
                ],
                "status": "active",
                "execution_stats": {
                    "total_runs": 45,
                    "successful_runs": 42,
                    "total_trades_executed": 15,
                    "total_profit_loss_usd": 1250.50
                }
            }
        }
```

### **API Endpoints (router.py):**

```python
"""
User flows router.

Endpoints for managing automation workflows.
"""

from fastapi import APIRouter, Depends, status, HTTPException
from typing import List
from app.modules.user_flows.schemas import (
    UserFlowCreate,
    UserFlowUpdate,
    UserFlowResponse
)
from app.core.dependencies import get_current_user


router = APIRouter(
    prefix="/api/v1/user-flows",
    tags=["User Flows"]
)


@router.get(
    "",
    response_model=List[UserFlowResponse],
    summary="List user's flows",
    description="""
    Get all automation flows for the current user.
    
    **What are Flows?**
    Flows are automated trading workflows that combine:
    - AI agents (for analysis)
    - Prompts (trading strategies)
    - Market conditions (triggers)
    - Risk management rules
    
    **Flow Lifecycle:**
    1. Create flow with configuration
    2. Activate flow (status = "active")
    3. Flow monitors triggers
    4. When triggered, AI analyzes market
    5. If conditions met, trade is executed
    6. Results tracked in execution_stats
    
    **Note:** Phase 2 only handles configuration. Execution engine in Phase 3.
    """
)
async def list_user_flows(
    current_user: dict = Depends(get_current_user),
    status_filter: Optional[str] = Query(None, description="Filter by status")
):
    """List all flows for current user."""
    pass


@router.get(
    "/{flow_id}",
    response_model=UserFlowResponse,
    summary="Get flow by ID"
)
async def get_user_flow(
    flow_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get specific flow details."""
    pass


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=UserFlowResponse,
    summary="Create new flow",
    description="""
    Create a new automation workflow.
    
    **Workflow:**
    1. Validate all references (prompts, agents, wallets exist)
    2. Validate flow steps are properly ordered
    3. Validate risk management settings
    4. Create flow with status="paused" (user must activate)
    5. Return created flow
    
    **Validation:**
    - At least 1 flow step required
    - All agents must exist and be active
    - Wallet must belong to user
    - Market pairs must be valid
    - Risk settings must be reasonable
    """
)
async def create_user_flow(
    flow_data: UserFlowCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create new automation flow."""
    pass


@router.put(
    "/{flow_id}",
    response_model=UserFlowResponse,
    summary="Update flow"
)
async def update_user_flow(
    flow_id: str,
    flow_data: UserFlowUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update existing flow configuration."""
    pass


@router.patch(
    "/{flow_id}/status",
    response_model=UserFlowResponse,
    summary="Change flow status",
    description="""
    Activate, pause, or stop a flow.
    
    **Status Transitions:**
    - **paused → active**: Start monitoring triggers
    - **active → paused**: Stop monitoring but keep config
    - **active → stopped**: Stop permanently (can't reactivate)
    - **paused → stopped**: Stop permanently
    
    **Note:** Stopped flows cannot be reactivated. Create new flow instead.
    """
)
async def change_flow_status(
    flow_id: str,
    new_status: str = Query(..., description="New status: active, paused, stopped"),
    current_user: dict = Depends(get_current_user)
):
    """Change flow status (activate/pause/stop)."""
    pass


@router.delete(
    "/{flow_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete flow"
)
async def delete_user_flow(
    flow_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Soft delete user flow."""
    pass


@router.post(
    "/{flow_id}/validate",
    summary="Validate flow configuration",
    description="""
    Validate a flow configuration without executing it.
    
    **Checks:**
    - All referenced resources exist
    - Trigger conditions are valid
    - Risk management settings are reasonable
    - Flow steps are properly ordered
    - Agent configurations are valid
    
    **Use Case:** Test flow before activating
    """
)
async def validate_flow(
    flow_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Validate flow configuration."""
    pass


@router.post(
    "/{flow_id}/test-run",
    summary="Test run flow (dry run)",
    description="""
    Simulate flow execution without placing real trades.
    
    **What Happens:**
    1. Fetch current market data
    2. Execute all flow steps with AI agents
    3. Get trading recommendation
    4. Calculate risk assessment
    5. Return what WOULD have happened (no actual trade)
    
    **Use Case:** Test strategy before going live
    
    **Note:** This is Phase 3 functionality. Phase 2: Return placeholder.
    """
)
async def test_run_flow(
    flow_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Test run flow without executing trades (Phase 3)."""
    # TODO Phase 3: Implement dry run
    return {
        "message": "Test run functionality will be available in Phase 3",
        "flow_id": flow_id
    }
```

---

## ✅ COMPREHENSIVE TESTING REQUIREMENTS

For **EVERY module**, you MUST create comprehensive tests covering:

### **1. Positive Test Cases (Happy Path)**

```python
@pytest.mark.asyncio
async def test_create_resource_with_valid_data_returns_201():
    """Test creating resource with valid data succeeds."""
    pass

@pytest.mark.asyncio
async def test_list_resources_returns_paginated_results():
    """Test listing resources returns paginated data."""
    pass

@pytest.mark.asyncio
async def test_get_resource_by_id_returns_resource():
    """Test getting resource by ID succeeds."""
    pass

@pytest.mark.asyncio
async def test_update_resource_with_valid_data_succeeds():
    """Test updating resource succeeds."""
    pass

@pytest.mark.asyncio
async def test_delete_resource_soft_deletes():
    """Test deleting resource soft deletes it."""
    pass
```

### **2. Negative Test Cases (Error Scenarios)**

```python
@pytest.mark.asyncio
async def test_create_resource_without_auth_returns_401():
    """Test creating resource without authentication fails."""
    pass

@pytest.mark.asyncio
async def test_create_resource_without_permission_returns_403():
    """Test creating resource without permission fails."""
    pass

@pytest.mark.asyncio
async def test_create_resource_with_invalid_data_returns_422():
    """Test creating resource with invalid data fails."""
    pass

@pytest.mark.asyncio
async def test_get_nonexistent_resource_returns_404():
    """Test getting non-existent resource returns 404."""
    pass

@pytest.mark.asyncio
async def test_create_duplicate_resource_returns_400():
    """Test creating duplicate resource fails."""
    pass

@pytest.mark.asyncio
async def test_update_resource_with_invalid_data_returns_422():
    """Test updating with invalid data fails."""
    pass
```

### **3. Edge Cases**

```python
@pytest.mark.asyncio
async def test_pagination_with_limit_exceeding_max_uses_max():
    """Test pagination respects max limit."""
    pass

@pytest.mark.asyncio
async def test_soft_deleted_resources_not_returned_in_list():
    """Test soft deleted items don't appear in lists."""
    ```python
    pass

@pytest.mark.asyncio
async def test_cache_invalidation_after_update():
    """Test cache is invalidated after resource update."""
    pass

@pytest.mark.asyncio
async def test_rate_limit_exceeded_returns_429():
    """Test rate limiting works correctly."""
    pass

@pytest.mark.asyncio
async def test_concurrent_updates_handle_race_condition():
    """Test concurrent updates are handled safely."""
    pass
```

### **4. Provider-Specific Tests (for Wallets & Agents)**

```python
@pytest.mark.asyncio
async def test_binance_provider_validates_credentials():
    """Test Binance provider validates API keys correctly."""
    pass

@pytest.mark.asyncio
async def test_binance_provider_fetches_balance():
    """Test Binance provider can fetch account balance."""
    pass

@pytest.mark.asyncio
async def test_openai_provider_generates_valid_response():
    """Test OpenAI provider returns standardized AIResponse."""
    pass

@pytest.mark.asyncio
async def test_mock_provider_works_for_testing():
    """Test mock provider can be used in tests."""
    pass
```

---

## 📚 DOCUMENTATION REQUIREMENTS

For **EVERY module**, ensure comprehensive documentation:

### **1. Code Documentation**

```python
"""
Module description at the top of every file.

Explain:
- Purpose of this module
- Key responsibilities
- Dependencies
- Usage examples
"""

class SomeClass:
    """
    Class description.
    
    Detailed explanation of what this class does and when to use it.
    """
    
    def some_method(self, param: str) -> Dict:
        """
        Method description.
        
        Args:
            param: What this parameter is for
            
        Returns:
            Dict: What is returned and structure
            
        Raises:
            ValueError: When this error occurs
            HTTPException: When this error occurs
            
        Example:
            >>> obj = SomeClass()
            >>> result = obj.some_method("test")
            >>> print(result)
        """
        pass
```

### **2. API Documentation (OpenAPI)**

```python
@router.post(
    "/endpoint",
    status_code=status.HTTP_201_CREATED,
    response_model=ResponseSchema,
    summary="Short summary (5-10 words)",
    description="""
    Detailed multi-paragraph description.
    
    **What it does:**
    - Main functionality
    - Business logic
    
    **Workflow:**
    1. Step-by-step process
    2. What happens internally
    
    **Requirements:**
    - Authentication needed?
    - Permissions required?
    
    **Examples:**
    Request body example here
    
    **Notes:**
    - Important information
    - Rate limiting
    - Caching
    """,
    response_description="Brief success response description",
    responses={
        201: {
            "description": "Success case",
            "content": {
                "application/json": {
                    "example": { /* realistic example */ }
                }
            }
        },
        400: {
            "description": "Error case",
            "content": {
                "application/json": {
                    "example": { /* error example */ }
                }
            }
        }
    }
)
```

### **3. README for Each Module**

Create `README.md` in each module folder:

```markdown
# Module Name

## Purpose
What this module does and why it exists.

## Key Features
- Feature 1
- Feature 2

## Database Schema
Brief overview of the collection structure.

## API Endpoints
- `GET /api/v1/resource` - List resources
- `POST /api/v1/resource` - Create resource
- etc.

## Usage Examples

### Creating a Resource
```python
# Example code
```

### Using the Provider
```python
# Example code
```

## Testing
How to run tests for this module.

## Dependencies
- Other modules this depends on
- External services required

## Phase 3 Integration
What will be added in Phase 3.
```

---

## 🚀 IMPLEMENTATION CHECKLIST

Use this checklist for **EACH MODULE**:

### **Pre-Implementation**
- [ ] Read and understand module requirements
- [ ] Review database model design
- [ ] Plan test cases (positive, negative, edge cases)

### **Step 1: Tests First (TDD)**
- [ ] Create test file (`test_module_name.py`)
- [ ] Write positive test cases (at least 5)
- [ ] Write negative test cases (at least 5)
- [ ] Write edge case tests (at least 3)
- [ ] Write provider-specific tests (if applicable)
- [ ] All tests should FAIL initially (no implementation yet)

### **Step 2: Database Model**
- [ ] Create `models.py` with MongoDB Document class
- [ ] Add all required fields with type hints
- [ ] Add field descriptions in docstrings
- [ ] Define indexes for query optimization
- [ ] Add `Settings` class with collection name
- [ ] Run tests - should fail (no service/router yet)

### **Step 3: Pydantic Schemas**
- [ ] Create `schemas.py` with DTOs
- [ ] Create Request schemas (Create, Update)
- [ ] Create Response schemas
- [ ] Add Field() with descriptions and examples
- [ ] Add validators with `@field_validator`
- [ ] Add `Config` class with examples
- [ ] Run tests - should still fail

### **Step 4: Service Layer**
- [ ] Create `service.py` with business logic
- [ ] Implement CRUD operations
- [ ] Add validation logic
- [ ] Add error handling with custom exceptions
- [ ] Add caching logic (Redis)
- [ ] Add logging
- [ ] Run tests - some should pass now

### **Step 5: Provider Implementations (if applicable)**
- [ ] Create `providers/base.py` with abstract interface
- [ ] Create concrete implementations (2-3 providers)
- [ ] Create mock provider for testing
- [ ] Implement all abstract methods
- [ ] Add provider-specific error handling
- [ ] Run provider tests - should pass

### **Step 6: Router/Endpoints**
- [ ] Create `router.py` with FastAPI router
- [ ] Implement all CRUD endpoints
- [ ] Add authentication dependencies
- [ ] Add permission checks
- [ ] Add comprehensive OpenAPI documentation
- [ ] Add request/response examples
- [ ] Run all tests - should pass

### **Step 7: Documentation**
- [ ] Add module docstrings to all files
- [ ] Add function/method docstrings
- [ ] Add inline comments for complex logic
- [ ] Create module README.md
- [ ] Update main README with module info
- [ ] Verify OpenAPI docs render correctly

### **Step 8: Integration**
- [ ] Register router in main.py
- [ ] Add module tag to OpenAPI
- [ ] Update initialization scripts if needed
- [ ] Run full test suite
- [ ] Test manually via Swagger UI
- [ ] Verify caching works
- [ ] Verify rate limiting works

### **Step 9: Final Verification**
- [ ] All tests pass (100%)
- [ ] Code coverage > 80%
- [ ] No linting errors
- [ ] API documentation complete
- [ ] Manual testing completed
- [ ] Performance tested (if applicable)
- [ ] Security reviewed

---

## 🎯 MODULE IMPLEMENTATION ORDER (REPEAT FOR EACH)

### **Week 1: Provider Abstractions**

**Day 1-2: Wallets Module**
1. Write tests (2 hours)
2. Implement models (1 hour)
3. Implement schemas (1 hour)
4. Implement base provider interface (2 hours)
5. Implement Binance provider (3 hours)
6. Implement Coinbase provider (3 hours)
7. Implement mock provider (1 hour)
8. Implement service layer (2 hours)
9. Implement router (2 hours)
10. Documentation (1 hour)
11. Integration & testing (2 hours)

**Day 3-4: Agents Module**
(Same structure as Wallets, with OpenAI, Anthropic, Google providers)

---

### **Week 2: Content & Configuration**

**Day 5: Prompts Module**
1. Write tests (1 hour)
2. Implement models (1 hour)
3. Implement schemas (1 hour)
4. Implement service (2 hours)
5. Implement router (2 hours)
6. Documentation (1 hour)
7. Integration & testing (1 hour)

**Day 6: User Prompts Module**
(Similar to Prompts but with user ownership)

**Day 7: User Settings Module**
(Simple CRUD module)

---

### **Week 3: Market Data & Monitoring**

**Day 8-10: Market Data Module**
1. Write tests (2 hours)
2. Implement models (1 hour)
3. Implement indicators.py (6 hours - complex math)
4. Implement ingestion service (4 hours)
5. Implement schemas (1 hour)
6. Implement service (2 hours)
7. Implement router (2 hours)
8. Setup background task (2 hours)
9. Documentation (1 hour)
10. Integration & testing (3 hours)

**Day 11-12: Whale Alerts Module**
1. Write tests (1 hour)
2. Implement models (1 hour)
3. Implement monitoring service (4 hours)
4. Implement classification logic (2 hours)
5. Implement schemas (1 hour)
6. Implement service (1 hour)
7. Implement router (2 hours)
8. Setup background task (1 hour)
9. Documentation (1 hour)
10. Integration & testing (2 hours)

---

### **Week 4: Trading Infrastructure**

**Day 13-14: User Wallets Module**
**Day 15-16: User Flows Module**
**Day 17: User Trades Module**
**Day 18: Risk Management Module**

---

## 🔒 SECURITY REQUIREMENTS

### **Critical Security Considerations:**

1. **Credential Encryption**
```python
# In user_wallets module, encrypt sensitive data
from cryptography.fernet import Fernet

def encrypt_credentials(credentials: Dict) -> str:
    """
    Encrypt wallet credentials before storing.
    
    Uses Fernet symmetric encryption with key from env.
    """
    # TODO: Implement encryption
    # - Get encryption key from env (ENCRYPTION_KEY)
    # - Serialize credentials to JSON
    # - Encrypt with Fernet
    # - Return encrypted string
    pass

def decrypt_credentials(encrypted: str) -> Dict:
    """Decrypt wallet credentials."""
    # TODO: Implement decryption
    pass
```

2. **API Key Security**
```python
# Never log API keys or secrets
# Never return them in API responses
# Store in environment variables
# Use secret management in production (AWS Secrets Manager, etc.)
```

3. **Rate Limiting Per User**
```python
# Implement strict rate limiting for expensive operations:
# - Market data ingestion: 10 requests/minute
# - AI agent calls: 100 requests/hour
# - Wallet operations: 50 requests/minute
```

4. **Input Validation**
```python
# Validate ALL inputs with Pydantic
# Sanitize user-generated content (prompts)
# Prevent SQL injection (use parameterized queries)
# Prevent XSS (escape HTML in responses)
```

5. **Permission Checks**
```python
# ALWAYS check:
# - User owns the resource (user_id matches)
# - User has permission for the action
# - Resource is not soft-deleted
# - Resource is active (if applicable)
```

---

## ⚙️ ENVIRONMENT VARIABLES TO ADD

Update `.env.example` with new variables:

```ini
# Market Data
MARKET_DATA_API_KEY=your-market-data-api-key
MARKET_DATA_REFRESH_INTERVAL_SECONDS=300  # 5 minutes

# Whale Monitoring
WHALE_ALERT_API_KEY=your-whale-alert-api-key
WHALE_MONITORING_INTERVAL_SECONDS=60  # 1 minute
MIN_WHALE_AMOUNT_USD=1000000

# AI Providers
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
GOOGLE_API_KEY=your-google-api-key

# Exchange APIs (for wallet providers)
BINANCE_API_KEY=your-binance-api-key
BINANCE_API_SECRET=your-binance-api-secret
COINBASE_API_KEY=your-coinbase-api-key
COINBASE_API_SECRET=your-coinbase-api-secret

# Encryption
ENCRYPTION_KEY=your-32-byte-encryption-key  # For encrypting wallet credentials

# Background Tasks
BACKGROUND_TASK_CONCURRENCY=4
TASK_QUEUE_REDIS_URL=redis://localhost:6379/2

# Caching (Phase 2 specific)
CACHE_MARKET_DATA_TTL_SECONDS=60
CACHE_WHALE_ALERTS_TTL_SECONDS=300
CACHE_INDICATORS_TTL_SECONDS=120
```

---

## 📊 DEPENDENCIES TO ADD

Update `requirements.txt`:

```txt
# Existing dependencies...

# AI Providers
openai==1.3.0
anthropic==0.7.0
google-generativeai==0.3.0

# Exchange APIs
ccxt==4.1.0  # Unified crypto exchange API
python-binance==1.0.17
coinbase==2.1.0

# Technical Indicators
pandas==2.1.3
numpy==1.24.3
ta-lib==0.4.28  # Technical Analysis Library

# Encryption
cryptography==41.0.7

# Blockchain/Web3
web3==6.11.3
eth-account==0.10.0

# Background Tasks (if not already added)
celery==5.3.4
redis==5.0.1

# Async HTTP clients
aiohttp==3.9.1
httpx==0.25.2

# Data validation
python-dateutil==2.8.2
```

---

## 🎨 CODE QUALITY STANDARDS (ENFORCED)

### **1. Type Hints Everywhere**
```python
# ✅ CORRECT
async def get_wallet(wallet_id: str, db: AsyncIOMotorDatabase) -> Wallet:
    pass

# ❌ INCORRECT
async def get_wallet(wallet_id, db):
    pass
```

### **2. Comprehensive Docstrings**
```python
# ✅ CORRECT
def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """
    Calculate Relative Strength Index.
    
    RSI is a momentum indicator that measures the speed and magnitude
    of recent price changes to evaluate overbought or oversold conditions.
    
    Args:
        prices: List of closing prices (most recent last)
        period: Number of periods for RSI calculation (default 14)
        
    Returns:
        float: RSI value between 0 and 100
        
    Raises:
        ValueError: If prices list is shorter than period
        
    Example:
        >>> prices = [100, 102, 101, 103, 105]
        >>> rsi = calculate_rsi(prices, period=14)
        >>> print(f"RSI: {rsi:.2f}")
    """
    pass

# ❌ INCORRECT
def calculate_rsi(prices, period=14):
    """Calculate RSI."""
    pass
```

### **3. Error Handling**
```python
# ✅ CORRECT
from app.core.exceptions import WalletNotFoundError, InvalidCredentialsError

async def validate_wallet_credentials(wallet_id: str, credentials: Dict):
    wallet = await get_wallet(wallet_id)
    if not wallet:
        raise WalletNotFoundError(f"Wallet {wallet_id} not found")
    
    provider = get_provider(wallet.provider)
    
    try:
        is_valid = await provider.validate_credentials(credentials)
        if not is_valid:
            raise InvalidCredentialsError("Invalid API credentials")
    except Exception as e:
        logger.error(f"Credential validation failed: {e}", exc_info=True)
        raise

# ❌ INCORRECT
async def validate_wallet_credentials(wallet_id, credentials):
    wallet = await get_wallet(wallet_id)
    if not wallet:
        raise Exception("Not found")  # Too generic!
    
    # No error handling for provider calls
    provider = get_provider(wallet.provider)
    return await provider.validate_credentials(credentials)
```

### **4. Logging Standards**
```python
# ✅ CORRECT
import logging
logger = logging.getLogger(__name__)

async def execute_trade(trade_data: Dict):
    logger.info(
        f"Executing trade: symbol={trade_data['symbol']}, "
        f"side={trade_data['side']}, amount={trade_data['amount']}"
    )
    
    try:
        result = await place_order(trade_data)
        logger.info(f"Trade executed successfully: order_id={result['order_id']}")
        return result
    except Exception as e:
        logger.error(
            f"Trade execution failed: {e}",
            extra={
                "trade_data": trade_data,
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        raise

# ❌ INCORRECT
async def execute_trade(trade_data):
    print("Executing trade")  # Don't use print!
    result = await place_order(trade_data)
    print("Done")  # No error handling, no context
    return result
```

### **5. Atomic Functions (Single Responsibility)**
```python
# ✅ CORRECT - Each function does ONE thing
async def fetch_market_data(symbol: str, timeframe: str) -> List[Dict]:
    """Fetch raw OHLC data from exchange."""
    pass

async def calculate_indicators(ohlc_data: List[Dict]) -> Dict:
    """Calculate technical indicators from OHLC data."""
    pass

async def store_market_data(symbol: str, data: List[Dict]):
    """Store market data in database."""
    pass

async def cache_market_data(symbol: str, data: List[Dict]):
    """Cache market data in Redis."""
    pass

# ❌ INCORRECT - Function does too many things
async def get_and_store_market_data(symbol: str, timeframe: str):
    """Fetch data, calculate indicators, store in DB, and cache."""
    # This should be split into multiple functions!
    data = await fetch_from_exchange(symbol, timeframe)
    indicators = calculate_indicators(data)
    await save_to_database(data, indicators)
    await cache_in_redis(data, indicators)
    return data
```

---

## 🚨 COMMON MISTAKES TO AVOID

### **DON'T:**
- ❌ Write implementation before tests
- ❌ Skip error handling
- ❌ Use generic exceptions
- ❌ Log sensitive data (passwords, API keys)
- ❌ Hardcode values
- ❌ Skip type hints
- ❌ Skip docstrings
- ❌ Ignore soft deletes
- ❌ Return database errors to users
- ❌ Skip validation
- ❌ Forget to cache expensive operations
- ❌ Ignore rate limiting
- ❌ Mix business logic with route handlers
- ❌ Store unencrypted credentials
- ❌ Skip permission checks

### **DO:**
- ✅ Write tests first (TDD)
- ✅ Handle all errors gracefully
- ✅ Use custom exceptions
- ✅ Log important events with context
- ✅ Use environment variables
- ✅ Add type hints everywhere
- ✅ Write comprehensive docstrings
- ✅ Check is_deleted flag
- ✅ Return standardized error responses
- ✅ Validate all inputs
- ✅ Cache aggressively (with TTL)
- ✅ Implement rate limiting
- ✅ Keep routes thin, logic in services
- ✅ Encrypt sensitive data
- ✅ Always check permissions

---

## ✅ SUCCESS CRITERIA

Phase 2 is complete when:

- [ ] All 12 modules implemented
- [ ] All tests pass (300+ tests total)
- [ ] Code coverage > 80%
- [ ] All endpoints documented in Swagger/ReDoc
- [ ] All database models created with proper indexes
- [ ] Provider abstraction layers working (wallets + agents)
- [ ] 2+ wallet providers implemented (Binance + Coinbase)
- [ ] 3+ AI providers implemented (OpenAI + Anthropic + Google)
- [ ] Market data ingestion working (OHLC + indicators)
- [ ] Whale monitoring service working
- [ ] User can create and configure flows (no execution yet)
- [ ] User can connect wallets (credentials encrypted)
- [ ] User can manually record trades
- [ ] Risk management calculations working
- [ ] User settings CRUD working
- [ ] All sensitive data encrypted
- [ ] Rate limiting implemented
- [ ] Caching implemented (Redis)
- [ ] Logging comprehensive
- [ ] No security vulnerabilities
- [ ] API documentation complete and accurate
- [ ] README files for all modules
- [ ] Manual testing completed

---

## 🎓 FINAL INSTRUCTIONS

You are now ready to build Phase 2! Remember:

1. **ALWAYS write tests BEFORE implementation**
2. **Follow the implementation order** (don't skip ahead)
3. **Test continuously** as you build
4. **Document everything** as you go
5. **Ask for help** if you're stuck on complex logic

**Start with Module 1 (Wallets). Build it completely before moving to Module 2.**

Good luck! 🚀

---

## 📞 NEED HELP?

If you encounter issues:

1. **Review the module specification** - Is everything clear?
2. **Check existing Phase 1 code** - Follow the same patterns
3. **Run tests frequently** - Catch issues early
4. **Read error messages carefully** - They usually tell you what's wrong
5. **Check the checklist** - Are you following all steps?

**Build methodically, test thoroughly, and Phase 2 will be complete in 3-4 weeks!**