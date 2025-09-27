import aiohttp
import asyncio
import json
import re
from typing import Any, Dict, Optional, Literal, Union
from dataclasses import dataclass
import logging

logging.getLogger("aiohttp").setLevel(logging.WARNING)

TraceType = Literal["dom", "action", "eval", "final", "tool", "thought"]
TraceResponse = Dict[str, Union[str, int]]


@dataclass
class Session:
    """Represents an API session"""

    id: str
    prompt: str
    model: str
    param: Optional[Dict[str, Any]] = None


class APIClient:
    """Client for interacting with the observability API at localhost:3000"""

    def __init__(self, api_key: str, skip_verification: bool = False):
        """
        Initialize the API client and optionally verify the API key.

        Args:
            api_key: The API key for authentication
            skip_verification: If True, skip API key verification during init

        Raises:
            Exception: If the API key is invalid (when skip_verification is False)
        """
        self.base_url = "http://localhost:3000"
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self.session_id: Optional[str] = None
        self._client_sessions: Dict[asyncio.AbstractEventLoop, aiohttp.ClientSession] = {}

        # Only verify if not skipping (to avoid event loop issues in sync context)
        if not skip_verification and not self._verify_api_key_sync():
            raise Exception(f"Invalid API key: {api_key}")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session for the current event loop"""
        loop = asyncio.get_event_loop()

        if loop not in self._client_sessions or self._client_sessions[loop].closed:
            self._client_sessions[loop] = aiohttp.ClientSession()

        return self._client_sessions[loop]

    async def close(self):
        """Close all aiohttp sessions"""
        for session in self._client_sessions.values():
            if not session.closed:
                await session.close()
        self._client_sessions.clear()

    async def verify_api_key(self) -> bool:
        """
        Verify that the API key is valid.

        Returns:
            True if the API key is valid, False otherwise
        """
        url = f"{self.base_url}/verify"

        try:
            client = await self._get_session()
            async with client.get(
                url, headers={"Authorization": f"Bearer {self.api_key}"}
            ) as response:
                return response.status == 200
        except Exception as e:
            print(f"[API] Error verifying API key: {e}")
            return False

    def _verify_api_key_sync(self) -> bool:
        """
        Synchronously verify the API key.

        Returns:
            True if the API key is valid, False otherwise
        """
        try:
            return asyncio.run(self.verify_api_key())
        except Exception:
            return False

    async def create_session(
        self, prompt: str, model: str, param: Optional[Dict[str, Any]] = None
    ) -> Session:
        """
        Create a new session.

        Args:
            prompt: The task/prompt for the AI model
            model: The AI model name/identifier
            param: Optional additional parameters

        Returns:
            Session object with the created session data
        """
        url = f"{self.base_url}/session"
        payload = {"prompt": prompt, "model": model, "param": param or {}}

        try:
            client = await self._get_session()
            async with client.post(url, headers=self.headers, json=payload) as response:
                if response.status == 200:
                    text = await response.text()
                    try:
                        if not text or text == "null":
                            raise ValueError("API returned null or empty response")
                        data = json.loads(text)
                        if not data or not isinstance(data, dict):
                            raise ValueError(f"Invalid response data type: {type(data)}")
                        self.session_id = data.get("id")
                        if not self.session_id:
                            raise ValueError(
                                f"Response missing 'id' field. Got keys: {list(data.keys())}"
                            )
                        print(f"[API] Created session: {self.session_id}")
                        return Session(id=self.session_id, prompt=prompt, model=model, param=param)
                    except (json.JSONDecodeError, ValueError) as e:
                        raise Exception(
                            f"Invalid JSON response from API. Status: 200, Body: {text[:200]}, Error: {e}"
                        )
                else:
                    error = await response.text()
                    raise Exception(f"Failed to create session: {response.status} - {error}")
        except aiohttp.ClientError as e:
            raise Exception(f"Failed to connect to API at {url}: {e}")

    async def end_session(self, session_id: Optional[str] = None) -> str:
        """
        End a session.

        Args:
            session_id: The session ID to end (uses current session if not provided)

        Returns:
            Response message
        """
        sid = session_id or self.session_id
        if not sid:
            raise ValueError("No session ID provided or set")

        url = f"{self.base_url}/session/{sid}/end"

        client = await self._get_session()
        async with client.post(
            url, headers={"Authorization": f"Bearer {self.api_key}"}
        ) as response:
            if response.status == 200:
                print(f"[API] Ended session: {sid}")
                return await response.text()
            else:
                error = await response.text()
                raise Exception(f"Failed to end session: {response.status} - {error}")

    async def upload_media(
        self, media_type: Literal["image", "video"], data: str, session_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Upload media (screenshot or video) to the API.

        Args:
            media_type: Type of media ("image" or "video")
            data: Data URI formatted media data (e.g., data:image/png;base64,...)
            session_id: The session ID (uses current session if not provided)

        Returns:
            URL of the uploaded media or None if failed
        """
        sid = session_id or self.session_id
        if not sid:
            raise ValueError("No session ID provided or set")

        url = f"{self.base_url}/session/{sid}/trace/media"

        form = aiohttp.FormData()
        form.add_field("type", media_type)
        form.add_field("data", data)

        try:
            client = await self._get_session()
            async with client.post(
                url, headers={"Authorization": f"Bearer {self.api_key}"}, data=form
            ) as response:
                if response.status == 200:
                    media_url = await response.json()
                    return media_url
                else:
                    error = await response.text()
                    print(f"[API] Failed to upload media: {response.status} - {error}")
                    return None
        except Exception as e:
            print(f"[API] Error uploading media: {e}")
            return None

    async def create_trace(
        self, trace_type: TraceType, content: str, session_id: Optional[str] = None
    ) -> TraceResponse:
        """
        Create a trace entry.

        Args:
            trace_type: Type of trace (dom, action, eval, final, tool, thought)
            content: The trace content
            session_id: The session ID (uses current session if not provided)

        Returns:
            Trace data from the API
        """
        sid = session_id or self.session_id
        if not sid:
            raise ValueError("No session ID provided or set")

        url = f"{self.base_url}/session/{sid}/trace"
        payload = {"type": trace_type, "content": content}

        client = await self._get_session()
        async with client.post(url, headers=self.headers, json=payload) as response:
            if response.status == 200:
                return await response.json()
            else:
                error = await response.text()
                print(f"[API] Failed to create trace: {response.status} - {error}")
                return {}

    def detect_trace_type(self, log_name: str, message: str) -> TraceType:
        """
        Detect the type of trace based on log name and message content.

        Args:
            log_name: The logger name (e.g., 'Agent', 'tools')
            message: The log message content

        Returns:
            The detected trace type
        """
        clean_msg = re.sub(r"^(INFO|WARNING|ERROR|DEBUG)\s+\[[\w.]+\]\s+", "", message).strip()

        if log_name == "tools":
            return "tool"

        if "Eval:" in clean_msg or "👍 Eval:" in clean_msg or "❔ Eval:" in clean_msg:
            return "eval"

        if "[ACTION" in clean_msg or "🦾" in clean_msg:
            return "action"

        if "Final Result:" in clean_msg or "📄  Final Result:" in clean_msg:
            return "final"

        if log_name == "Agent":
            return "thought"

        return "thought"
