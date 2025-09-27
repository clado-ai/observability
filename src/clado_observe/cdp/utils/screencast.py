"""
Screencast Utility

Handles screencast recording functionality including frame capture and video creation.
"""

import base64
import logging
import os
import subprocess
import tempfile
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

from .base_client import BaseCDPClient


class ScreencastParams(TypedDict, total=False):
    format: str
    quality: int
    everyNthFrame: int
    maxWidth: int
    maxHeight: int


class FrameData(TypedDict, total=False):
    data: str
    sessionId: Optional[str]
    metadata: dict
    timestamp: float


logger = logging.getLogger(__name__)


class ScreencastUtil:
    """
    Utility for recording browser screencasts and creating videos.
    """

    def __init__(self, client: BaseCDPClient) -> None:
        self.client = client
        self._screencast_frames: List[dict] = []  # Use dict instead of FrameData
        self._screencast_recording = False
        self._temp_dir: Optional[str] = None
        self._screencast_params: dict = {}  # Use dict instead of ScreencastParams

    async def start_screencast(self) -> None:
        """Start screencast recording."""
        try:
            self._temp_dir = tempfile.mkdtemp(prefix="screencast_")
            logger.debug(f"Created temporary directory: {self._temp_dir}")

            self._screencast_frames.clear()
            self._screencast_recording = True

            viewport_size = await self._get_viewport_size()

            screencast_params: Dict[str, Any] = {
                "format": "png",
                "quality": 90,
                "everyNthFrame": 1,
            }

            if viewport_size:
                screencast_params.update(
                    {
                        "maxWidth": min(viewport_size["width"], 1920),
                        "maxHeight": min(viewport_size["height"], 1080),
                    }
                )
            self._screencast_params = screencast_params

            sessions = self.client.get_session_ids()

            if not sessions:
                logger.warning(
                    "No sessions available yet. Screencast will start when a page is created."
                )
            else:
                for target_id, session_id in sessions.items():
                    await self.client.send(
                        "Page.startScreencast",
                        params=screencast_params,
                        session_id=session_id,
                    )
                    logger.debug(
                        f"Screencast started on session {session_id} with params: {screencast_params}"
                    )
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

    async def handle_screencast_frame(self, frame_data: dict, session_id: Optional[str]) -> None:
        """Handle incoming screencast frame data."""
        if not self._screencast_recording:
            return

        try:
            metadata = frame_data.get("metadata", {})
            cdp_timestamp = metadata.get("timestamp", time.time())

            self._screencast_frames.append(
                {
                    "data": frame_data.get("data", ""),
                    "timestamp": cdp_timestamp,
                    "metadata": metadata,
                    "sessionId": session_id,
                }
            )

            frame_session_id = frame_data.get("sessionId", "")
            if frame_session_id and session_id:
                await self._ack_screencast_frame(frame_session_id, session_id)

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

            sorted_frames = sorted(
                self._screencast_frames, key=lambda x: float(x.get("timestamp", 0))
            )

            frame_files = []
            timestamps = []
            for i, frame_data in enumerate(sorted_frames):
                ext = "png"
                frame_path = os.path.join(frames_dir, f"frame_{i:06d}.{ext}")
                try:
                    image_data = base64.b64decode(frame_data.get("data", ""))
                    with open(frame_path, "wb") as f:
                        f.write(image_data)
                    frame_files.append(frame_path)
                    timestamps.append(float(frame_data.get("timestamp", 0)))
                except Exception as e:
                    logger.debug(f"Failed to save frame {i}: {e}")
                    continue

            if not frame_files:
                logger.error("No frames were successfully saved")
                return None

            success = await self._create_video_with_ffmpeg(frame_files, timestamps, video_path)

            if success:
                logger.debug(f"Video created: {video_path}")
                return video_path
            else:
                return None

        except Exception as e:
            logger.error(f"Failed to create video from frames: {e}")
            return None

    async def _create_video_with_ffmpeg(
        self, frame_files: List[str], timestamps: List[float], output_path: str
    ) -> bool:
        """Create video using ffmpeg from frame images with timestamp-based durations.

        Args:
            frame_files: List of paths to frame image files
            timestamps: List of timestamps for each frame
            output_path: Path where the video should be saved

        Returns:
            True if video was created successfully, False otherwise
        """
        try:
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
            if result.returncode != 0:
                logger.debug("ffmpeg not available, skipping video creation")
                return False

            if not frame_files:
                logger.debug("No frame files provided")
                return False

            concat_file = os.path.join(os.path.dirname(frame_files[0]), "concat.txt")
            with open(concat_file, "w") as f:
                for i, frame_path in enumerate(frame_files):
                    if i < len(frame_files) - 1:
                        duration = timestamps[i + 1] - timestamps[i]
                    else:
                        if len(timestamps) > 1:
                            avg_duration = (timestamps[-1] - timestamps[0]) / (len(timestamps) - 1)
                            duration = min(avg_duration, 0.5)
                        else:
                            duration = 0.1

                    duration = max(duration, 0.03)

                    f.write(f"file '{frame_path}'\n")
                    f.write(f"duration {duration:.3f}\n")

                if frame_files:
                    f.write(f"file '{frame_files[-1]}'\n")

            if len(timestamps) > 1:
                total_duration = timestamps[-1] - timestamps[0]
                if len(frame_files) > 1:
                    avg_duration = (timestamps[-1] - timestamps[0]) / (len(timestamps) - 1)
                    total_duration += avg_duration
            else:
                total_duration = 0.1

            cmd = [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                concat_file,
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                "-vf",
                "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                "-movflags",
                "+faststart",
                output_path,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0 and os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                if file_size > 0:
                    return True
                else:
                    logger.error("Video file created but is empty")
                    return False
            else:
                logger.error(f"ffmpeg failed with return code {result.returncode}")
                logger.error(f"ffmpeg stderr: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error creating video with ffmpeg: {e}")
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
