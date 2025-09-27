"""
Screenshot Utility

Handles screenshot capture functionality using CDP Page.captureScreenshot.
"""

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
            msg = await fut  # type: ignore
            result = msg.get("result", {})
            screenshot_data = result.get("data")
            if screenshot_data:
                logger.debug("Screenshot captured successfully")
                return f"data:image/png;base64,{screenshot_data}"
            return None
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
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
        self,
        element_id: str,
        session_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Capture a screenshot of a specific DOM element.

        Args:
            element_id: The DOM element ID
            session_id: Optional session ID for targeted screenshot

        Returns:
            Data URI formatted base64 image data (data:image/png;base64,...) or None if failed
        """
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
            msg = await fut  # type: ignore
            result = msg.get("result", {})
            screenshot_data = result.get("data")
            if screenshot_data:
                logger.debug(f"Element screenshot captured successfully for element {element_id}")
                return f"data:image/png;base64,{screenshot_data}"
            return None
        except Exception as e:
            logger.error(f"Failed to capture element screenshot: {e}")
            return None
