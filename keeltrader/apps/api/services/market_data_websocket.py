"""
WebSocket service for real-time market data streaming
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Set

import websockets
from fastapi import WebSocket

from config import get_settings

logger = logging.getLogger(__name__)


class MarketDataWebSocketService:
    """Service for managing WebSocket connections for real-time market data"""

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.twelve_data_api_key
        self.ws_url = "wss://ws.twelvedata.com/v1/quotes/price"

        # Track active connections
        self.active_connections: Set[WebSocket] = set()

        # Track subscriptions by symbol
        self.subscriptions: Dict[str, Set[WebSocket]] = {}

        # WebSocket connection to Twelve Data
        self.twelve_data_ws: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False

        logger.info("Market data WebSocket service initialized")

    async def connect_to_twelve_data(self):
        """Connect to Twelve Data WebSocket"""
        if not self.api_key:
            logger.warning("No Twelve Data API key - WebSocket not available")
            return False

        try:
            self.twelve_data_ws = await websockets.connect(self.ws_url)
            self.is_connected = True

            # Authenticate
            auth_message = {
                "action": "subscribe",
                "params": {
                    "apikey": self.api_key
                }
            }
            await self.twelve_data_ws.send(json.dumps(auth_message))

            logger.info("Connected to Twelve Data WebSocket")

            # Start listening for messages
            asyncio.create_task(self._listen_twelve_data())

            return True

        except Exception as e:
            logger.error(f"Failed to connect to Twelve Data WebSocket: {e}")
            self.is_connected = False
            return False

    async def _listen_twelve_data(self):
        """Listen for messages from Twelve Data WebSocket"""
        try:
            async for message in self.twelve_data_ws:
                try:
                    data = json.loads(message)

                    # Handle different message types
                    if data.get("event") == "price":
                        await self._broadcast_price_update(data)
                    elif data.get("event") == "heartbeat":
                        logger.debug("Heartbeat received")
                    elif data.get("status") == "error":
                        logger.error(f"Twelve Data error: {data.get('message')}")

                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received: {message}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.warning("Twelve Data WebSocket connection closed")
            self.is_connected = False
            # Attempt to reconnect after delay
            await asyncio.sleep(5)
            await self.connect_to_twelve_data()
        except Exception as e:
            logger.error(f"Error in Twelve Data listener: {e}")
            self.is_connected = False

    async def _broadcast_price_update(self, data: Dict[str, Any]):
        """Broadcast price update to subscribed clients"""
        symbol = data.get("symbol")
        if not symbol or symbol not in self.subscriptions:
            return

        # Format the data for clients
        update = {
            "type": "price_update",
            "symbol": symbol,
            "price": data.get("price"),
            "timestamp": data.get("timestamp", datetime.now().isoformat()),
        }

        # Send to all clients subscribed to this symbol
        disconnected = set()
        for client in self.subscriptions[symbol]:
            try:
                await client.send_json(update)
            except Exception as e:
                logger.error(f"Error sending to client: {e}")
                disconnected.add(client)

        # Clean up disconnected clients
        for client in disconnected:
            await self.unsubscribe(client, symbol)

    async def subscribe(self, websocket: WebSocket, symbol: str):
        """Subscribe a client to a symbol"""
        # Add to subscriptions
        if symbol not in self.subscriptions:
            self.subscriptions[symbol] = set()
        self.subscriptions[symbol].add(websocket)

        # Add to active connections
        self.active_connections.add(websocket)

        # If we have Twelve Data API key, subscribe to the symbol
        if self.is_connected and self.twelve_data_ws:
            try:
                subscribe_message = {
                    "action": "subscribe",
                    "params": {
                        "symbols": symbol
                    }
                }
                await self.twelve_data_ws.send(json.dumps(subscribe_message))
                logger.info(f"Subscribed to {symbol} on Twelve Data")
            except Exception as e:
                logger.error(f"Error subscribing to {symbol}: {e}")
        else:
            # If no API key, start mock data stream
            asyncio.create_task(self._mock_price_stream(websocket, symbol))

        logger.info(f"Client subscribed to {symbol}")

    async def unsubscribe(self, websocket: WebSocket, symbol: str):
        """Unsubscribe a client from a symbol"""
        if symbol in self.subscriptions and websocket in self.subscriptions[symbol]:
            self.subscriptions[symbol].remove(websocket)

            # If no more clients for this symbol, unsubscribe from Twelve Data
            if not self.subscriptions[symbol]:
                del self.subscriptions[symbol]

                if self.is_connected and self.twelve_data_ws:
                    try:
                        unsubscribe_message = {
                            "action": "unsubscribe",
                            "params": {
                                "symbols": symbol
                            }
                        }
                        await self.twelve_data_ws.send(json.dumps(unsubscribe_message))
                        logger.info(f"Unsubscribed from {symbol} on Twelve Data")
                    except Exception as e:
                        logger.error(f"Error unsubscribing from {symbol}: {e}")

        logger.info(f"Client unsubscribed from {symbol}")

    async def disconnect(self, websocket: WebSocket):
        """Disconnect a client"""
        # Remove from all subscriptions
        for symbol in list(self.subscriptions.keys()):
            if websocket in self.subscriptions[symbol]:
                await self.unsubscribe(websocket, symbol)

        # Remove from active connections
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        logger.info("Client disconnected")

    async def _mock_price_stream(self, websocket: WebSocket, symbol: str):
        """Generate mock price updates when no API key is available"""
        import random

        # Base price
        base_prices = {
            "SPY": 450.0,
            "AAPL": 180.0,
            "TSLA": 250.0,
        }
        base_price = base_prices.get(symbol, 100.0)
        current_price = base_price

        try:
            while websocket in self.active_connections and symbol in self.subscriptions:
                # Generate random price movement
                change = current_price * (random.random() * 0.004 - 0.002)  # ±0.2%
                current_price = max(0.01, current_price + change)

                update = {
                    "type": "price_update",
                    "symbol": symbol,
                    "price": round(current_price, 2),
                    "timestamp": datetime.now().isoformat(),
                }

                try:
                    await websocket.send_json(update)
                except Exception:
                    break

                # Update every 2 seconds
                await asyncio.sleep(2)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in mock price stream: {e}")

    async def close(self):
        """Close all connections"""
        if self.twelve_data_ws:
            await self.twelve_data_ws.close()

        for websocket in list(self.active_connections):
            try:
                await websocket.close()
            except Exception:
                pass

        self.active_connections.clear()
        self.subscriptions.clear()
        self.is_connected = False

        logger.info("Market data WebSocket service closed")


# Global instance
market_data_ws_service = MarketDataWebSocketService()
