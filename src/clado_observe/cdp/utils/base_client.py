"""
Base CDP Client Utility

Provides the core WebSocket connection and message handling functionality
for Chrome DevTools Protocol communication.
"""

import asyncio
import json
import logging
from typing import Awaitable, Callable, Dict, Optional, Union

import websockets

CDPParams = Dict[str, Union[str, int, bool, dict, list]]
CDPMessage = Dict[str, Union[int, str, CDPParams]]


logger = logging.getLogger(__name__)


class BaseCDPClient:
    """
    Base CDP client that handles WebSocket connection and message routing.
    Provides the foundation for all CDP utility modules.
    """

    def __init__(self, cdp_url: str) -> None:
        if not cdp_url or not isinstance(cdp_url, str):
            raise ValueError("cdp_url must be a non-empty string")

        self.cdp_url = cdp_url
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._id_counter: int = 0
        self._pending: Dict[int, asyncio.Future] = {}
        self._session_ids: Dict[str, str] = {}
        self._recv_task: Optional[asyncio.Task] = None
        self._stop_event: Optional[asyncio.Event] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._event_handler: Optional[Callable[[CDPMessage], Awaitable[None]]] = None

    async def connect(self) -> None:
        """Connect to the CDP WebSocket."""
        if self._ws is not None:
            return

        self._stop_event = asyncio.Event()
        self._loop = asyncio.get_running_loop()

        try:
            self._ws = await websockets.connect(
                self.cdp_url,
                max_size=None,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10,
            )
        except Exception as e:
            logger.error(f"Failed to connect to CDP URL: {e}")
            raise

        self._recv_task = asyncio.create_task(self._recv_loop())

    async def disconnect(self) -> None:
        """Disconnect from the CDP WebSocket."""
        if self._stop_event is not None:
            self._stop_event.set()

        if self._recv_task and not self._recv_task.done():
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                pass

        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception as e:
                logger.debug(f"Error closing WebSocket: {e}")
            finally:
                self._ws = None

    async def send(
        self,
        method: str,
        params: Optional[CDPParams] = None,
        *,
        expect_result: bool = False,
        session_id: Optional[str] = None,
    ) -> Optional[asyncio.Future]:
        """
        Send a CDP message and optionally wait for a response.

        Args:
            method: The CDP method name (e.g., "Page.enable")
            params: Optional parameters for the method
            expect_result: Whether to wait for a response
            session_id: Optional session ID for targeted messages

        Returns:
            Future that resolves to the response if expect_result=True, None otherwise
        """
        assert self._ws is not None
        self._id_counter += 1
        msg: CDPMessage = {"id": self._id_counter, "method": method}
        if params:
            msg["params"] = params
        if session_id:
            msg["sessionId"] = session_id

        fut: Optional[asyncio.Future] = None
        if expect_result:
            assert self._loop is not None
            fut = self._loop.create_future()
            self._pending[self._id_counter] = fut

        await self._ws.send(json.dumps(msg))
        return fut

    async def _recv_loop(self) -> None:
        """Main message receiving loop."""
        assert self._ws is not None
        ws = self._ws

        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError as e:
                    logger.debug(f"Failed to parse JSON message: {e}")
                    continue
                except Exception as e:
                    logger.debug(f"Error processing message: {e}")
                    continue

                if "id" in msg and msg["id"] in self._pending:
                    fut = self._pending.pop(msg["id"])
                    if not fut.done():
                        fut.set_result(msg)
                    continue

                if hasattr(self, "_event_handler") and self._event_handler:
                    await self._event_handler(msg)
                else:
                    await self._handle_event(msg)

        except asyncio.CancelledError:
            logger.debug("Receive loop cancelled")
            return
        except websockets.exceptions.ConnectionClosed as e:
            logger.debug(f"WebSocket connection closed: {e}")
            return
        except Exception as e:
            logger.debug(f"Unexpected error in receive loop: {e}")
            return

    async def _handle_event(self, msg: CDPMessage) -> None:
        """Handle CDP events. Override in subclasses for specific event handling."""
        pass

    def get_session_ids(self) -> Dict[str, str]:
        """Get the current session ID mapping."""
        return self._session_ids.copy()

    def add_session(self, target_id: str, session_id: str) -> None:
        """Add a session mapping."""
        self._session_ids[target_id] = session_id

    def remove_session(self, target_id: str) -> None:
        """Remove a session mapping."""
        self._session_ids.pop(target_id, None)
