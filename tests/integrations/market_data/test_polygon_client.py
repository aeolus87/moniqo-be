"""
Polygon.io Client Tests - REST + WebSocket

Comprehensive tests for both REST API and WebSocket clients.
All responses are mocked - no real API calls.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from decimal import Decimal
from datetime import datetime, timezone
import json

from app.integrations.market_data.polygon_client import (
    PolygonRestClient,
    PolygonWebSocketClient,
    MessageType,
    AssetClass,
    Timeframe,
    parse_crypto_trade,
    parse_crypto_quote,
    parse_crypto_aggregate
)


# ==================== REST CLIENT TESTS ====================

@pytest.fixture
def polygon_rest_client():
    """Create PolygonRestClient instance"""
    return PolygonRestClient(api_key="test_polygon_key_123")


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session"""
    session = AsyncMock()
    return session


# ==================== REST: INITIALIZATION TESTS ====================

def test_polygon_rest_init():
    """Test REST client initialization"""
    client = PolygonRestClient(api_key="test_key")
    
    assert client.api_key == "test_key"
    assert client.BASE_URL == "https://api.polygon.io"
    assert client.session is None


# ==================== REST: GET AGGREGATES TESTS ====================

@pytest.mark.asyncio
async def test_get_aggregates_success(polygon_rest_client):
    """Test successful aggregates retrieval"""
    mock_response = {
        "results": [
            {
                "t": 1700000000000,
                "o": 50000.0,
                "h": 52000.0,
                "l": 49500.0,
                "c": 51000.0,
                "v": 1234.5678,
                "vw": 50500.0,
                "n": 5000
            },
            {
                "t": 1700086400000,
                "o": 51000.0,
                "h": 51500.0,
                "l": 50000.0,
                "c": 50800.0,
                "v": 987.654,
                "vw": 50700.0,
                "n": 3000
            }
        ],
        "status": "OK"
    }
    
    with patch.object(polygon_rest_client, '_request', new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_response
        
        bars = await polygon_rest_client.get_aggregates(
            ticker="X:BTCUSD",
            multiplier=1,
            timespan="day",
            from_date="2025-01-01",
            to_date="2025-01-02"
        )
        
        assert len(bars) == 2
        
        # First bar
        assert bars[0]["open"] == Decimal("50000.0")
        assert bars[0]["high"] == Decimal("52000.0")
        assert bars[0]["low"] == Decimal("49500.0")
        assert bars[0]["close"] == Decimal("51000.0")
        assert bars[0]["volume"] == Decimal("1234.5678")
        assert bars[0]["vwap"] == Decimal("50500.0")
        assert bars[0]["transactions"] == 5000
        assert isinstance(bars[0]["timestamp"], datetime)
        
        # Second bar
        assert bars[1]["close"] == Decimal("50800.0")


@pytest.mark.asyncio
async def test_get_aggregates_empty_results(polygon_rest_client):
    """Test aggregates with no results"""
    mock_response = {
        "results": [],
        "status": "OK"
    }
    
    with patch.object(polygon_rest_client, '_request', new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_response
        
        bars = await polygon_rest_client.get_aggregates(
            ticker="X:BTCUSD",
            multiplier=1,
            timespan="day",
            from_date="2025-01-01",
            to_date="2025-01-02"
        )
        
        assert len(bars) == 0


@pytest.mark.asyncio
async def test_get_aggregates_different_timeframes(polygon_rest_client):
    """Test aggregates with different timeframes"""
    mock_response = {"results": [], "status": "OK"}
    
    with patch.object(polygon_rest_client, '_request', new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_response
        
        # Minute bars
        await polygon_rest_client.get_aggregates(
            ticker="X:BTCUSD",
            multiplier=5,
            timespan="minute",
            from_date="2025-01-01",
            to_date="2025-01-01"
        )
        
        # Hour bars
        await polygon_rest_client.get_aggregates(
            ticker="X:BTCUSD",
            multiplier=1,
            timespan="hour",
            from_date="2025-01-01",
            to_date="2025-01-02"
        )
        
        # Week bars
        await polygon_rest_client.get_aggregates(
            ticker="X:BTCUSD",
            multiplier=1,
            timespan="week",
            from_date="2025-01-01",
            to_date="2025-01-31"
        )
        
        assert mock_req.call_count == 3


# ==================== REST: GET PREVIOUS CLOSE TESTS ====================

@pytest.mark.asyncio
async def test_get_previous_close_success(polygon_rest_client):
    """Test get previous close"""
    mock_response = {
        "results": [
            {
                "T": "X:BTCUSD",
                "t": 1700000000000,
                "o": 50000.0,
                "h": 52000.0,
                "l": 49500.0,
                "c": 51000.0,
                "v": 1234.5678
            }
        ],
        "status": "OK"
    }
    
    with patch.object(polygon_rest_client, '_request', new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_response
        
        prev_close = await polygon_rest_client.get_previous_close("X:BTCUSD")
        
        assert prev_close is not None
        assert prev_close["ticker"] == "X:BTCUSD"
        assert prev_close["open"] == Decimal("50000.0")
        assert prev_close["high"] == Decimal("52000.0")
        assert prev_close["low"] == Decimal("49500.0")
        assert prev_close["close"] == Decimal("51000.0")
        assert prev_close["volume"] == Decimal("1234.5678")
        assert isinstance(prev_close["timestamp"], datetime)


@pytest.mark.asyncio
async def test_get_previous_close_no_data(polygon_rest_client):
    """Test get previous close with no data"""
    mock_response = {
        "results": [],
        "status": "OK"
    }
    
    with patch.object(polygon_rest_client, '_request', new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_response
        
        prev_close = await polygon_rest_client.get_previous_close("X:BTCUSD")
        
        assert prev_close is None


# ==================== REST: GET TICKER SNAPSHOT TESTS ====================

@pytest.mark.asyncio
async def test_get_ticker_snapshot_crypto(polygon_rest_client):
    """Test get crypto ticker snapshot"""
    mock_response = {
        "ticker": {
            "ticker": "X:BTCUSD",
            "lastTrade": {
                "p": 51234.56,
                "s": 0.123,
                "t": 1700000000000000000
            },
            "lastQuote": {
                "p": 51230.00,
                "s": 1.5,
                "P": 51235.00,
                "S": 2.0
            },
            "day": {
                "o": 50000.0,
                "h": 52000.0,
                "l": 49500.0,
                "c": 51234.56,
                "v": 12345.678
            }
        },
        "status": "OK"
    }
    
    with patch.object(polygon_rest_client, '_request', new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_response
        
        snapshot = await polygon_rest_client.get_ticker_snapshot("X:BTCUSD")
        
        assert snapshot is not None
        assert snapshot["ticker"] == "X:BTCUSD"
        
        # Last trade
        assert snapshot["last_trade"]["price"] == Decimal("51234.56")
        assert snapshot["last_trade"]["size"] == Decimal("0.123")
        
        # Last quote
        assert snapshot["last_quote"]["bid"] == Decimal("51230.00")
        assert snapshot["last_quote"]["ask"] == Decimal("51235.00")
        
        # Day data
        assert snapshot["day"]["open"] == Decimal("50000.0")
        assert snapshot["day"]["close"] == Decimal("51234.56")


# ==================== WEBSOCKET CLIENT TESTS ====================

@pytest.fixture
def polygon_ws_client():
    """Create PolygonWebSocketClient instance"""
    return PolygonWebSocketClient(api_key="test_ws_key_456", asset_class=AssetClass.CRYPTO)


# ==================== WS: INITIALIZATION TESTS ====================

def test_polygon_ws_init():
    """Test WebSocket client initialization"""
    client = PolygonWebSocketClient(api_key="test_key", asset_class=AssetClass.CRYPTO)
    
    assert client.api_key == "test_key"
    assert client.asset_class == AssetClass.CRYPTO
    assert client.ws_url == "wss://socket.polygon.io/crypto"
    assert client.is_connected is False
    assert client.is_authenticated is False
    assert client.is_running is False
    assert len(client.subscriptions) == 0


def test_polygon_ws_init_different_asset_classes():
    """Test initialization with different asset classes"""
    crypto_client = PolygonWebSocketClient(api_key="key", asset_class=AssetClass.CRYPTO)
    assert crypto_client.ws_url == "wss://socket.polygon.io/crypto"
    
    stocks_client = PolygonWebSocketClient(api_key="key", asset_class=AssetClass.STOCKS)
    assert stocks_client.ws_url == "wss://socket.polygon.io/stocks"
    
    forex_client = PolygonWebSocketClient(api_key="key", asset_class=AssetClass.FOREX)
    assert forex_client.ws_url == "wss://socket.polygon.io/forex"


# ==================== WS: MESSAGE HANDLER TESTS ====================

def test_set_message_handler(polygon_ws_client):
    """Test setting message handler"""
    async def mock_handler(message):
        pass
    
    polygon_ws_client.set_message_handler(mock_handler)
    
    assert polygon_ws_client.message_handler == mock_handler


# ==================== WS: CONNECTION TESTS ====================

@pytest.mark.asyncio
async def test_ws_connect_success(polygon_ws_client):
    """Test successful WebSocket connection"""
    mock_ws = AsyncMock()
    
    # Mock auth response
    auth_response = [{"status": "auth_success", "message": "authenticated"}]
    mock_ws.recv = AsyncMock(return_value=json.dumps(auth_response))
    mock_ws.send = AsyncMock()
    
    with patch('websockets.connect', new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = mock_ws
        
        await polygon_ws_client.connect()
        
        assert polygon_ws_client.is_connected is True
        assert polygon_ws_client.is_authenticated is True
        assert polygon_ws_client.reconnect_attempts == 0


@pytest.mark.asyncio
async def test_ws_connect_auth_failure(polygon_ws_client):
    """Test WebSocket authentication failure"""
    mock_ws = AsyncMock()
    
    # Mock failed auth response
    auth_response = [{"status": "auth_failed", "message": "invalid key"}]
    mock_ws.recv = AsyncMock(return_value=json.dumps(auth_response))
    mock_ws.send = AsyncMock()
    
    with patch('websockets.connect', new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = mock_ws
        
        with pytest.raises(ConnectionError, match="Authentication failed"):
            await polygon_ws_client.connect()
        
        assert polygon_ws_client.is_authenticated is False


# ==================== WS: SUBSCRIPTION TESTS ====================

@pytest.mark.asyncio
async def test_subscribe_crypto_trades(polygon_ws_client):
    """Test subscribing to crypto trades"""
    polygon_ws_client.is_authenticated = True
    polygon_ws_client.ws = AsyncMock()
    polygon_ws_client.ws.send = AsyncMock()
    
    await polygon_ws_client.subscribe_crypto_trades(["BTC-USD", "ETH-USD"])
    
    # Should have sent subscribe message
    polygon_ws_client.ws.send.assert_called_once()
    
    # Should have added to subscriptions
    assert "XT.BTC-USD" in polygon_ws_client.subscriptions
    assert "XT.ETH-USD" in polygon_ws_client.subscriptions


@pytest.mark.asyncio
async def test_subscribe_crypto_quotes(polygon_ws_client):
    """Test subscribing to crypto quotes"""
    polygon_ws_client.is_authenticated = True
    polygon_ws_client.ws = AsyncMock()
    polygon_ws_client.ws.send = AsyncMock()
    
    await polygon_ws_client.subscribe_crypto_quotes(["BTC-USD"])
    
    assert "XQ.BTC-USD" in polygon_ws_client.subscriptions


@pytest.mark.asyncio
async def test_subscribe_crypto_aggregates(polygon_ws_client):
    """Test subscribing to crypto aggregates"""
    polygon_ws_client.is_authenticated = True
    polygon_ws_client.ws = AsyncMock()
    polygon_ws_client.ws.send = AsyncMock()
    
    # Minute aggregates
    await polygon_ws_client.subscribe_crypto_aggregates(["BTC-USD"], interval="minute")
    assert "XA.BTC-USD" in polygon_ws_client.subscriptions
    
    # Second aggregates
    await polygon_ws_client.subscribe_crypto_aggregates(["ETH-USD"], interval="second")
    assert "XAS.ETH-USD" in polygon_ws_client.subscriptions


@pytest.mark.asyncio
async def test_subscribe_not_authenticated(polygon_ws_client):
    """Test subscribe fails when not authenticated"""
    polygon_ws_client.is_authenticated = False
    
    with pytest.raises(ConnectionError, match="Not authenticated"):
        await polygon_ws_client.subscribe_crypto_trades(["BTC-USD"])


# ==================== WS: UNSUBSCRIBE TESTS ====================

@pytest.mark.asyncio
async def test_unsubscribe(polygon_ws_client):
    """Test unsubscribing from channels"""
    polygon_ws_client.is_authenticated = True
    polygon_ws_client.ws = AsyncMock()
    polygon_ws_client.ws.send = AsyncMock()
    polygon_ws_client.subscriptions = {"XT.BTC-USD", "XT.ETH-USD"}
    
    await polygon_ws_client.unsubscribe(["XT.BTC-USD"])
    
    assert "XT.BTC-USD" not in polygon_ws_client.subscriptions
    assert "XT.ETH-USD" in polygon_ws_client.subscriptions


# ==================== MESSAGE PARSER TESTS ====================

def test_parse_crypto_trade():
    """Test parsing crypto trade message"""
    message = {
        "ev": "XT",
        "pair": "BTC-USD",
        "p": 51234.56,
        "s": 0.123,
        "t": 1700000000000,
        "x": 1
    }
    
    parsed = parse_crypto_trade(message)
    
    assert parsed["type"] == "trade"
    assert parsed["symbol"] == "BTC-USD"
    assert parsed["price"] == Decimal("51234.56")
    assert parsed["size"] == Decimal("0.123")
    assert isinstance(parsed["timestamp"], datetime)
    assert parsed["exchange"] == 1


def test_parse_crypto_quote():
    """Test parsing crypto quote message"""
    message = {
        "ev": "XQ",
        "pair": "BTC-USD",
        "bp": 51230.00,
        "bs": 1.5,
        "ap": 51235.00,
        "as": 2.0,
        "t": 1700000000000
    }
    
    parsed = parse_crypto_quote(message)
    
    assert parsed["type"] == "quote"
    assert parsed["symbol"] == "BTC-USD"
    assert parsed["bid_price"] == Decimal("51230.00")
    assert parsed["bid_size"] == Decimal("1.5")
    assert parsed["ask_price"] == Decimal("51235.00")
    assert parsed["ask_size"] == Decimal("2.0")
    assert isinstance(parsed["timestamp"], datetime)


def test_parse_crypto_aggregate():
    """Test parsing crypto aggregate message"""
    message = {
        "ev": "XA",
        "pair": "BTC-USD",
        "o": 51000.0,
        "h": 51500.0,
        "l": 50800.0,
        "c": 51200.0,
        "v": 123.456,
        "s": 1700000000000,
        "e": 1700000060000
    }
    
    parsed = parse_crypto_aggregate(message)
    
    assert parsed["type"] == "aggregate"
    assert parsed["symbol"] == "BTC-USD"
    assert parsed["open"] == Decimal("51000.0")
    assert parsed["high"] == Decimal("51500.0")
    assert parsed["low"] == Decimal("50800.0")
    assert parsed["close"] == Decimal("51200.0")
    assert parsed["volume"] == Decimal("123.456")
    assert isinstance(parsed["start_time"], datetime)
    assert isinstance(parsed["end_time"], datetime)


# ==================== WS: CLOSE TESTS ====================

@pytest.mark.asyncio
async def test_ws_close(polygon_ws_client):
    """Test closing WebSocket connection"""
    polygon_ws_client.is_running = True
    polygon_ws_client.is_connected = True
    polygon_ws_client.is_authenticated = True
    polygon_ws_client.ws = AsyncMock()
    polygon_ws_client.ws.close = AsyncMock()
    
    await polygon_ws_client.close()
    
    assert polygon_ws_client.is_running is False
    assert polygon_ws_client.is_connected is False
    assert polygon_ws_client.is_authenticated is False
    polygon_ws_client.ws.close.assert_called_once()


# ==================== EDGE CASES ====================

@pytest.mark.asyncio
async def test_get_aggregates_with_large_date_range(polygon_rest_client):
    """Test aggregates with very large date range"""
    mock_response = {"results": [], "status": "OK"}
    
    with patch.object(polygon_rest_client, '_request', new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_response
        
        bars = await polygon_rest_client.get_aggregates(
            ticker="X:BTCUSD",
            multiplier=1,
            timespan="day",
            from_date="2020-01-01",
            to_date="2025-11-22",
            limit=50000  # Max limit
        )
        
        assert isinstance(bars, list)


def test_parse_crypto_trade_missing_fields():
    """Test parsing trade with missing optional fields"""
    message = {
        "ev": "XT",
        "pair": "BTC-USD",
        "p": 51234.56,
        "s": 0.123,
        "t": 1700000000000
        # Missing 'x' (exchange)
    }
    
    parsed = parse_crypto_trade(message)
    
    assert parsed["exchange"] == "unknown"


# ==================== SUMMARY ====================

"""
Test Coverage Summary:

REST CLIENT:
✅ Initialization (1 test)
✅ Get aggregates (3 tests)
✅ Get previous close (2 tests)
✅ Get ticker snapshot (1 test)

WEBSOCKET CLIENT:
✅ Initialization (2 tests)
✅ Message handler (1 test)
✅ Connection (2 tests)
✅ Subscriptions (4 tests)
✅ Unsubscribe (1 test)
✅ Close (1 test)

MESSAGE PARSERS:
✅ Parse trade (2 tests)
✅ Parse quote (1 test)
✅ Parse aggregate (1 test)

EDGE CASES:
✅ Large date ranges (1 test)

TOTAL: 22 comprehensive tests
All using mocked responses - no real API calls!
"""

