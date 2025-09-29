"""
Screenshot Utility

Handles screenshot capture functionality using CDP Page.captureScreenshot.
"""

import asyncio
import logging
from typing import Any, Dict, Optional, TypedDict, cast

from .base_client import BaseCDPClient


logger = logging.getLogger(__name__)


class ClipParams(TypedDict, total=False):
    """Type definition for screenshot clip parameters."""

    type: str
    nodeId: str


class ScreenshotParams(TypedDict, total=False):
    """Type definition for screenshot capture parameters."""

    format: str
    quality: int
    clip: ClipParams


class ScreenshotUtil:
    """
    Utility for capturing screenshots from browser pages.
    """

    def __init__(self, client: BaseCDPClient) -> None:
        self.client = client

    async def capture_screenshot(self, session_id: Optional[str] = None) -> Optional[str]:
        """
        Capture a screenshot and return the base64 encoded image data as data URI.

        Args:
            session_id: Optional session ID for targeted screenshot

        Returns:
            Data URI formatted base64 image data (data:image/png;base64,...) or None if failed
        """
        max_retries = 2
        timeout_seconds = 2.0

        for attempt in range(max_retries + 1):
            try:
                params: ScreenshotParams = {
                    "format": "png",
                    "quality": 60,
                }

                fut = await self.client.send(
                    "Page.captureScreenshot",
                    params=cast(Dict[str, Any], params),
                    expect_result=True,
                    session_id=session_id,
                )
                assert fut is not None

                msg = await asyncio.wait_for(fut, timeout=timeout_seconds)
                result = msg.get("result", {})
                screenshot_data = result.get("data")
                if screenshot_data:
                    logger.debug(f"Screenshot captured successfully on attempt {attempt + 1}")
                    return f"data:image/png;base64,{screenshot_data}"

                logger.warning(f"Screenshot capture returned no data on attempt {attempt + 1}")

            except asyncio.TimeoutError:
                logger.warning(
                    f"Screenshot capture timed out on attempt {attempt + 1}/{max_retries + 1}"
                )
            except Exception as e:
                logger.warning(
                    f"Screenshot capture failed on attempt {attempt + 1}/{max_retries + 1}: {e}"
                )

            # Don't wait after the last attempt
            if attempt < max_retries:
                backoff_delay = min(1 + attempt * 0.5, 3)  # Much faster backoff: 1s, 1.5s, 2s max
                logger.debug(f"Waiting {backoff_delay}s before retry...")
                await asyncio.sleep(backoff_delay)

        logger.error(f"Failed to capture screenshot after {max_retries + 1} attempts")
        return None

    async def capture_screenshot_from_all_pages(self) -> Dict[str, Optional[str]]:
        """
        Capture screenshots from all attached page sessions.

        Returns:
            Dictionary mapping target_id to data URI formatted base64 image data
        """
        screenshots = {}
        for target_id, session_id in self.client.get_session_ids().items():
            screenshot_data = await self.capture_screenshot(session_id=session_id)
            screenshots[target_id] = screenshot_data
        return screenshots

    async def capture_element_screenshot(
        self, element_id: str, session_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Capture a screenshot of a specific DOM element.

        Args:
            element_id: The DOM element ID
            session_id: Optional session ID for targeted screenshot

        Returns:
            Data URI formatted base64 image data (data:image/png;base64,...) or None if failed
        """
        max_retries = 2
        timeout_seconds = 2.0
        for attempt in range(max_retries + 1):
            try:
                params: ScreenshotParams = {
                    "format": "png",
                    "quality": 60,
                    "clip": {"type": "node", "nodeId": element_id},
                }

                fut = await self.client.send(
                    "Page.captureScreenshot",
                    params=cast(Dict[str, Any], params),
                    expect_result=True,
                    session_id=session_id,
                )
                assert fut is not None

                # Add timeout to the future
                msg = await asyncio.wait_for(fut, timeout=timeout_seconds)
                result = msg.get("result", {})
                screenshot_data = result.get("data")
                if screenshot_data:
                    logger.debug(
                        f"Element screenshot captured successfully for element {element_id} on attempt {attempt + 1}"
                    )
                    return f"data:image/png;base64,{screenshot_data}"

                logger.warning(
                    f"Element screenshot capture returned no data on attempt {attempt + 1}"
                )

            except asyncio.TimeoutError:
                logger.warning(
                    f"Element screenshot capture timed out on attempt {attempt + 1}/{max_retries + 1}"
                )
            except Exception as e:
                logger.warning(
                    f"Element screenshot capture failed on attempt {attempt + 1}/{max_retries + 1}: {e}"
                )

            # Don't wait after the last attempt
            if attempt < max_retries:
                backoff_delay = min(1 + attempt * 0.5, 3)  # Much faster backoff: 1s, 1.5s, 2s max
                logger.debug(f"Waiting {backoff_delay}s before retry...")
                await asyncio.sleep(backoff_delay)

        logger.error(f"Failed to capture element screenshot after {max_retries + 1} attempts")
        return None
