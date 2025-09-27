"""
Network Capture Utility

Handles network request/response capture and analysis using Chrome DevTools Protocol.
Collects network traffic data including requests, responses, headers, timing, etc.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .base_client import BaseCDPClient

logger = logging.getLogger(__name__)


class NetworkEvent:
    """Represents a network event with request and response data."""

    def __init__(self, request_id: str, timestamp: float):
        self.request_id = request_id
        self.timestamp = timestamp
        self.request_time = datetime.fromtimestamp(timestamp).isoformat()

        self.method: Optional[str] = None
        self.url: Optional[str] = None
        self.request_headers: Dict[str, str] = {}
        self.request_body: Optional[str] = None
        self.resource_type: Optional[str] = None

        self.status_code: Optional[int] = None
        self.status_text: Optional[str] = None
        self.response_headers: Dict[str, str] = {}
        self.response_body: Optional[str] = None
        self.mime_type: Optional[str] = None

        self.response_time: Optional[float] = None
        self.duration_ms: Optional[float] = None
        self.encoded_data_length: Optional[int] = None
        self.decoded_body_length: Optional[int] = None

        self.failed: bool = False
        self.failure_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert network event to dictionary for serialization."""
        data = {
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "request_time": self.request_time,
            "method": self.method,
            "url": self.url,
            "resource_type": self.resource_type,
            "status_code": self.status_code,
            "status_text": self.status_text,
            "mime_type": self.mime_type,
            "duration_ms": self.duration_ms,
            "encoded_data_length": self.encoded_data_length,
            "decoded_body_length": self.decoded_body_length,
            "failed": self.failed,
            "failure_reason": self.failure_reason,
        }

        if self.request_headers:
            data["request_headers"] = self.request_headers
        if self.response_headers:
            data["response_headers"] = self.response_headers

        if self.request_body:
            data["request_body"] = self.request_body
        if self.response_body:
            data["response_body"] = self.response_body

        return {k: v for k, v in data.items() if v is not None}


class NetworkUtil:
    """
    Utility for capturing and managing network traffic via CDP.
    """

    def __init__(self, client: BaseCDPClient, capture_bodies: bool = False):
        """
        Initialize NetworkUtil.

        Args:
            client: The base CDP client for communication
            capture_bodies: Whether to capture request/response bodies (can be memory intensive)
        """
        self.client = client
        self.capture_bodies = capture_bodies

        self._events: Dict[str, NetworkEvent] = {}
        self._completed_events: List[NetworkEvent] = []

        self._lock = asyncio.Lock()

    async def enable_network_capture(self, session_id: str) -> None:
        """Enable network capture for a specific session."""
        try:
            await self.client.send(
                "Network.enable",
                params={"maxTotalBufferSize": 100000000, "maxResourceBufferSize": 50000000},
                session_id=session_id,
            )

            if self.capture_bodies:
                await self.client.send(
                    "Network.setRequestInterception",
                    params={"patterns": [{"urlPattern": "*"}]},
                    session_id=session_id,
                )

            logger.debug(f"Network capture enabled for session {session_id}")

        except Exception as e:
            logger.error(f"Failed to enable network capture: {e}")

    async def handle_network_event(self, method: str, params: Dict[str, Any]) -> None:
        """
        Handle network-related CDP events.

        Args:
            method: The CDP event method name
            params: The event parameters
        """
        async with self._lock:
            try:
                if method == "Network.requestWillBeSent":
                    await self._handle_request_will_be_sent(params)
                elif method == "Network.responseReceived":
                    await self._handle_response_received(params)
                elif method == "Network.loadingFinished":
                    await self._handle_loading_finished(params)
                elif method == "Network.loadingFailed":
                    await self._handle_loading_failed(params)
                elif method == "Network.requestServedFromCache":
                    await self._handle_served_from_cache(params)

            except Exception as e:
                logger.debug(f"Error handling network event {method}: {e}")

    async def _handle_request_will_be_sent(self, params: Dict[str, Any]) -> None:
        """Handle the start of a network request."""
        request_id = params.get("requestId")
        if not request_id:
            return

        if request_id not in self._events:
            timestamp = params.get("timestamp", 0)
            event = NetworkEvent(request_id, timestamp)
            self._events[request_id] = event
        else:
            event = self._events[request_id]

        request = params.get("request", {})
        event.method = request.get("method")
        event.url = request.get("url")
        event.request_headers = request.get("headers", {})
        event.request_body = request.get("postData")

        event.resource_type = params.get("type")

    async def _handle_response_received(self, params: Dict[str, Any]) -> None:
        """Handle receipt of a network response."""
        request_id = params.get("requestId")
        if not request_id or request_id not in self._events:
            return

        event = self._events[request_id]
        response = params.get("response", {})

        event.status_code = response.get("status")
        event.status_text = response.get("statusText")
        event.response_headers = response.get("headers", {})
        event.mime_type = response.get("mimeType")
        event.encoded_data_length = response.get("encodedDataLength")

        timestamp = params.get("timestamp", 0)
        if timestamp and event.timestamp:
            event.response_time = timestamp
            event.duration_ms = (timestamp - event.timestamp) * 1000

    async def _handle_loading_finished(self, params: Dict[str, Any]) -> None:
        """Handle completion of network loading."""
        request_id = params.get("requestId")
        if not request_id or request_id not in self._events:
            return

        event = self._events[request_id]

        if "encodedDataLength" in params:
            event.encoded_data_length = params["encodedDataLength"]

        self._completed_events.append(event)
        del self._events[request_id]

        logger.debug(f"Network request completed: {event.method} {event.url} - {event.status_code}")

    async def _handle_loading_failed(self, params: Dict[str, Any]) -> None:
        """Handle failed network loading."""
        request_id = params.get("requestId")
        if not request_id or request_id not in self._events:
            return

        event = self._events[request_id]
        event.failed = True
        event.failure_reason = params.get("errorText", "Unknown error")

        self._completed_events.append(event)
        del self._events[request_id]

        logger.debug(f"Network request failed: {event.url} - {event.failure_reason}")

    async def _handle_served_from_cache(self, params: Dict[str, Any]) -> None:
        """Handle requests served from cache."""
        request_id = params.get("requestId")
        if not request_id or request_id not in self._events:
            return

        event = self._events[request_id]
        event.status_code = 304
        return None

    async def get_response_body(self, request_id: str, session_id: str) -> Optional[str]:
        """
        Fetch the response body for a specific request.

        Args:
            request_id: The network request ID
            session_id: The CDP session ID

        Returns:
            The response body as a string, or None if unavailable
        """
        if not self.capture_bodies:
            return None

        try:
            fut = await self.client.send(
                "Network.getResponseBody",
                params={"requestId": request_id},
                session_id=session_id,
                expect_result=True,
            )
            if fut:
                result = await fut
                body = result.get("result", {}).get("body")
                return body
            return None
        except Exception as e:
            logger.debug(f"Failed to get response body for {request_id}: {e}")
            return None

    def get_completed_events(self) -> List[NetworkEvent]:
        """Get all completed network events."""
        return self._completed_events.copy()

    def get_pending_events(self) -> List[NetworkEvent]:
        """Get all pending network events."""
        return list(self._events.values())

    def get_all_events(self) -> List[NetworkEvent]:
        """Get all network events (completed and pending)."""
        all_events = self._completed_events.copy()
        all_events.extend(self._events.values())
        return all_events

    def clear_events(self) -> None:
        """Clear all stored network events."""
        self._events.clear()
        self._completed_events.clear()

    def get_events_summary(self) -> Dict[str, Any]:
        """Get a summary of network activity."""
        all_events = self.get_all_events()

        # Initialize typed dictionaries for request counts
        requests_by_type: Dict[str, int] = {}
        requests_by_status: Dict[str, int] = {}

        summary: Dict[str, Any] = {
            "total_requests": len(all_events),
            "completed_requests": len(self._completed_events),
            "pending_requests": len(self._events),
            "failed_requests": sum(1 for e in all_events if e.failed),
            "total_data_transferred": sum(e.encoded_data_length or 0 for e in all_events),
            "average_duration_ms": 0,
            "requests_by_type": requests_by_type,
            "requests_by_status": requests_by_status,
        }

        durations = [e.duration_ms for e in all_events if e.duration_ms]
        if durations:
            summary["average_duration_ms"] = sum(durations) / len(durations)

        for event in all_events:
            if event.resource_type:
                requests_by_type[event.resource_type] = (
                    requests_by_type.get(event.resource_type, 0) + 1
                )

        for event in all_events:
            if event.status_code:
                status_group = f"{event.status_code // 100}xx"
                requests_by_status[status_group] = requests_by_status.get(status_group, 0) + 1

        return summary

    def format_network_log(self, event: NetworkEvent) -> str:
        """Format a network event as a log entry."""
        status = f"{event.status_code}" if event.status_code else "PENDING"
        if event.failed:
            status = f"FAILED: {event.failure_reason}"

        duration = f"{event.duration_ms:.2f}ms" if event.duration_ms else "N/A"
        size = f"{event.encoded_data_length} bytes" if event.encoded_data_length else "N/A"

        return f"[Network] {event.method} {event.url} - Status: {status}, Duration: {duration}, Size: {size}"
