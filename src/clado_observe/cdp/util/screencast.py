"""
Screencast Utility

Handles screencast recording functionality including frame capture and video creation.
"""

import asyncio
import base64
import logging
import os
import subprocess
import tempfile
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base_client import BaseCDPClient


logger = logging.getLogger(__name__)


class ScreencastUtil:
    """
    Utility for recording browser screencasts and creating videos.
    """

    def __init__(self, client: BaseCDPClient) -> None:
        self.client = client
        self._screencast_frames: List[Dict[str, Any]] = []
        self._screencast_recording = False
        self._temp_dir: Optional[str] = None

    async def start_screencast(self) -> None:
        """Start screencast recording."""
        try:
            self._temp_dir = tempfile.mkdtemp(prefix="screencast_")
            logger.debug(f"Created temporary directory: {self._temp_dir}")

            self._screencast_frames.clear()
            self._screencast_recording = True

            viewport_size = await self._get_viewport_size()

            screencast_params = {
                "format": "png",
                "quality": 60,
                "everyNthFrame": 1,
            }

            if viewport_size:
                screencast_params.update(
                    {
                        "maxWidth": viewport_size["width"],
                        "maxHeight": viewport_size["height"],
                    }
                )

            for target_id, session_id in self.client.get_session_ids().items():
                await self.client.send(
                    "Page.startScreencast",
                    params=screencast_params,
                    session_id=session_id,
                )
                logger.debug(f"Screencast started on session {session_id}")
        except Exception as e:
            logger.error(f"Failed to start screencast: {e}")

    async def end_screencast(self) -> Optional[str]:
        """Stop screencast recording and create video.

        Returns:
            Path to the created video file, or None if no video was created
        """
        try:
            for target_id, session_id in self.client.get_session_ids().items():
                await self.client.send(
                    "Page.stopScreencast",
                    session_id=session_id,
                )
                logger.debug(f"Screencast stopped on session {session_id}")

            self._screencast_recording = False

            if self._screencast_frames:
                video_path = await self._create_video_from_frames()
                return video_path

            return None

        except Exception as e:
            logger.error(f"Failed to end screencast: {e}")
            return None

    async def _get_viewport_size(self) -> Optional[Dict[str, int]]:
        """Get the current viewport size from the first available session."""
        try:
            if not self.client.get_session_ids():
                return None

            first_session_id = next(iter(self.client.get_session_ids().values()))

            fut = await self.client.send(
                "Page.getLayoutMetrics",
                expect_result=True,
                session_id=first_session_id,
            )
            assert fut is not None
            msg = await fut  # type: ignore
            metrics = msg.get("result", {})

            viewport = metrics.get("cssVisualViewport", {})
            width = viewport.get("clientWidth")
            height = viewport.get("clientHeight")

            if width and height:
                return {"width": int(width), "height": int(height)}
        except Exception as e:
            logger.debug(f"Failed to get viewport size: {e}")

        return None

    async def _ack_screencast_frame(self, frame_session_id: str, session_id: Optional[str]) -> None:
        """Acknowledge a screencast frame to prevent buffer overflow."""
        try:
            await self.client.send(
                "Page.screencastFrameAck",
                params={"sessionId": frame_session_id},
                session_id=session_id,
            )
        except Exception as e:
            logger.debug(f"Failed to acknowledge screencast frame: {e}")

    def handle_screencast_frame(
        self, frame_data: Dict[str, Any], session_id: Optional[str]
    ) -> None:
        """Handle incoming screencast frame data."""
        if not self._screencast_recording:
            return

        try:
            self._screencast_frames.append(
                {
                    "data": frame_data.get("data", ""),
                    "timestamp": time.time(),
                    "metadata": frame_data.get("metadata", {}),
                    "sessionId": session_id,
                }
            )
            logger.debug(f"Captured screencast frame {len(self._screencast_frames)}")

            asyncio.create_task(
                self._ack_screencast_frame(frame_data.get("sessionId", ""), session_id)
            )

        except Exception as e:
            logger.debug(f"Error capturing screencast frame: {e}")

    async def _create_video_from_frames(self) -> Optional[str]:
        """Create a video file from captured screencast frames.

        Returns:
            Path to the created video file, or None if creation failed
        """
        try:
            if not self._screencast_frames:
                logger.debug("No screencast frames to create video from")
                return None

            if not self._temp_dir:
                logger.error("No temporary directory available")
                return None

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_path = os.path.join(self._temp_dir, f"screencast_{timestamp}.mp4")

            frames_dir = os.path.join(self._temp_dir, f"frames_{timestamp}")
            os.makedirs(frames_dir, exist_ok=True)

            for i, frame_data in enumerate(self._screencast_frames):
                frame_path = os.path.join(frames_dir, f"frame_{i:06d}.png")
                try:
                    image_data = base64.b64decode(frame_data.get("data", ""))
                    with open(frame_path, "wb") as f:
                        f.write(image_data)
                except Exception as e:
                    logger.debug(f"Failed to save frame {i}: {e}")
                    continue

            success = await self._create_video_with_ffmpeg(frames_dir, video_path)

            if success:
                logger.debug(f"Video created: {video_path}")
                return video_path
            else:
                return None

        except Exception as e:
            logger.error(f"Failed to create video from frames: {e}")
            return None

    async def _create_video_with_ffmpeg(self, frames_dir: str, output_path: str) -> bool:
        """Create video using ffmpeg from frame images.

        Returns:
            True if video was created successfully, False otherwise
        """
        try:
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
            if result.returncode != 0:
                logger.debug("ffmpeg not available, skipping video creation")
                return False

            cmd = [
                "ffmpeg",
                "-y",
                "-framerate",
                "15",
                "-i",
                os.path.join(frames_dir, "frame_%06d.png"),
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                output_path,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.debug(f"Video created successfully: {output_path}")
                return True
            else:
                logger.debug(f"ffmpeg error: {result.stderr}")
                return False

        except Exception as e:
            logger.debug(f"Error creating video with ffmpeg: {e}")
            return False

    def cleanup_temp_files(self) -> None:
        """Clean up temporary files and directories created during screencast."""
        try:
            if self._temp_dir and os.path.exists(self._temp_dir):
                import shutil

                shutil.rmtree(self._temp_dir)
                logger.debug(f"Cleaned up temporary directory: {self._temp_dir}")
                self._temp_dir = None
        except Exception as e:
            logger.debug(f"Error cleaning up temporary files: {e}")
