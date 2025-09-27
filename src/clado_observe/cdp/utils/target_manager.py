"""
Target Management Utility

Handles CDP target discovery, attachment, and session management.
Manages multiple page targets and monitors for new ones.
"""

import logging
from typing import TypedDict

from .base_client import BaseCDPClient


class TargetInfo(TypedDict, total=False):
    targetId: str
    type: str
    title: str
    url: str
    attached: bool
    browserContextId: str


logger = logging.getLogger(__name__)


class TargetManager:
    """
    Manages CDP targets and sessions for multi-page browser automation.
    """

    def __init__(self, client: BaseCDPClient) -> None:
        self.client = client

    async def attach_to_all_page_targets(self) -> None:
        """Attach to all existing page targets."""
        try:
            fut = await self.client.send("Target.getTargets", expect_result=True)
            assert fut is not None
            msg = await fut  # type: ignore
            target_infos = msg.get("result", {}).get("targetInfos", [])

            page_targets = []
            for info in target_infos:
                target_type = info.get("type")
                target_id = info.get("targetId")
                target_url = info.get("url", "unknown")

                if target_type == "page" and not target_url.startswith("chrome://"):
                    page_targets.append(target_id)

            for target_id in page_targets:
                await self.attach_to_target(target_id)

        except Exception as e:
            logger.debug(f"Failed to attach to targets: {e}")

    async def attach_to_target(self, target_id: str) -> None:
        """Attach to a specific target and store the session ID."""
        try:
            fut = await self.client.send(
                "Target.attachToTarget",
                params={"targetId": target_id, "flatten": True},
                expect_result=True,
            )
            assert fut is not None
            msg = await fut  # type: ignore
            session_id = msg.get("result", {}).get("sessionId")
            if session_id:
                self.client.add_session(target_id, session_id)
            else:
                logger.debug(f"Failed to get session ID for target {target_id}")
        except Exception as e:
            logger.debug(f"Failed to attach to target {target_id}: {e}")

    async def handle_target_created(self, target_info: TargetInfo) -> bool:
        """Handle new target creation events."""
        target_type = target_info.get("type")
        target_id = target_info.get("targetId")
        target_url = target_info.get("url", "unknown")

        if target_type == "page" and not target_url.startswith("chrome://") and target_id:
            await self.attach_to_target(target_id)
            return True

        return False

    async def enable_domains_on_all_sessions(self) -> None:
        """Enable CDP domains on all attached sessions."""
        domains = [
            "Page.enable",
            "DOM.enable",
            "Runtime.enable",
            "Network.enable",
            "DOMSnapshot.enable",
        ]

        for target_id, session_id in self.client.get_session_ids().items():
            for domain in domains:
                await self.client.send(domain, session_id=session_id)
