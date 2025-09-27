import asyncio
import os
import threading
from typing import Any, Dict, Optional, List, Tuple

from .utils.base_client import BaseCDPClient
from .utils.target_manager import TargetManager
from .utils.screenshot import ScreenshotUtil
from .utils.screencast import ScreencastUtil
from .utils.dom import DOMUtil
from ..utils.vlm_evaluator import VLMEvaluator, RunData, EvaluationResult

SnapshotData = Dict[int, Any]
CDPMessage = Dict[str, Any]


class CDPObserver:
    """
    Chrome DevTools Protocol (CDP) observer that connects to a browser-level CDP WebSocket
    (e.g., Browserbase session.connectUrl or a local Chrome remote-debugging URL),
    attaches to ALL page targets, monitors for new pages, enables relevant domains,
    captures periodic DOM snapshots and basic page info, and exposes callbacks for downstream processing.
    """

    def __init__(
        self,
        cdp_url: str,
        task: str,
    ) -> None:
        if not cdp_url or not isinstance(cdp_url, str):
            raise ValueError("cdp_url must be a non-empty string")

        self.cdp_url = cdp_url
        self.task = task

        self.client = BaseCDPClient(cdp_url)
        self.target_manager = TargetManager(self.client)
        self.screenshot_util = ScreenshotUtil(self.client)
        self.screencast_util = ScreencastUtil(self.client)
        self.dom_util = DOMUtil(self.client)

        self._bg_thread: Optional[threading.Thread] = None

        self.collected_screenshots: List[str] = []
        self.collected_logs: List[Tuple[str, str]] = []
        self.final_result: Optional[str] = None

    async def start(self) -> None:
        """Connect and start receiving events. Also schedules periodic tasks."""
        if self.client._ws is not None:
            return

        await self.client.connect()
        await self.target_manager.attach_to_all_page_targets()

        session_count = len(self.client.get_session_ids())
        if session_count == 0:
            await self.client.send("Target.setDiscoverTargets", params={"discover": True})
            await self.client.send(
                "Target.createTarget", params={"url": "https://www.google.com"}, expect_result=False
            )

            await asyncio.sleep(0.5)
            await self.target_manager.attach_to_all_page_targets()
            session_count = len(self.client.get_session_ids())
            if session_count > 0 and self.screencast_util._screencast_recording:
                for target_id, session_id in self.client.get_session_ids().items():
                    if self.screencast_util._screencast_params:
                        await self.client.send(
                            "Page.startScreencast",
                            params=self.screencast_util._screencast_params,
                            session_id=session_id,
                        )

        await self.target_manager.enable_domains_on_all_sessions()
        self.client._event_handler = self._handle_event

    async def stop(self) -> None:
        """Stop tasks and close the WebSocket."""
        await self.client.disconnect()

    def start_background(self) -> None:
        """Start the observer in a background thread with its own event loop."""
        if self._bg_thread and self._bg_thread.is_alive():
            return

        def _runner() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.start())
                assert self.client._stop_event is not None
                loop.run_until_complete(self.client._stop_event.wait())
            except Exception as e:
                print(f"[DEBUG] Error in background thread: {e}")
            finally:
                try:
                    pending = asyncio.all_tasks(loop)
                    for t in pending:
                        t.cancel()
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                except Exception:
                    pass
                loop.close()

        self._bg_thread = threading.Thread(target=_runner, daemon=True)
        self._bg_thread.start()

    def stop_background(self, timeout_s: float = 5.0) -> None:
        """Signal stop and wait briefly for background to exit."""
        if (
            self.client._loop
            and not self.client._loop.is_closed()
            and self.client._stop_event
            and not self.client._stop_event.is_set()
        ):
            try:
                asyncio.run_coroutine_threadsafe(self.stop(), self.client._loop)
            except Exception:
                pass
        if self._bg_thread:
            self._bg_thread.join(timeout=timeout_s)

    async def snapshot(self) -> SnapshotData:
        """Capture a DOM snapshot and return the enhanced result with ALL elements."""
        try:
            session_ids = self.client.get_session_ids()
            if not session_ids:
                print("[ERROR] No page sessions available for DOM snapshot")
                return {}

            session_id = next(iter(session_ids.values()))
            result = await self.dom_util.capture_snapshot(session_id=session_id)
            return result
        except Exception as e:
            print(f"[ERROR] Failed to capture snapshot: {e}")
            return {}

    async def screenshot(self) -> Optional[str]:
        """Capture a screenshot and return the base64 encoded image data."""
        try:
            session_ids = self.client.get_session_ids()
            if not session_ids:
                print("[ERROR] No page sessions available for screenshot")
                return None

            session_id = next(iter(session_ids.values()))
            screenshot_data = await self.screenshot_util.capture_screenshot(session_id=session_id)

            if screenshot_data:
                self.collected_screenshots.append(screenshot_data)

            return screenshot_data
        except Exception as e:
            print(f"[ERROR] Failed to capture screenshot: {e}")
            return None

    async def start_screencast(self) -> None:
        """Start screencast recording."""
        await self.screencast_util.start_screencast()

    async def end_screencast(self) -> Optional[str]:
        """Stop screencast recording and create video.

        Returns:
            Path to the created video file, or None if no video was created
        """
        return await self.screencast_util.end_screencast()

    async def _handle_event(self, msg: CDPMessage) -> None:
        """
        Handle CDP events.
        Manages screencast events to pass into handler
        and target creation events to create new page and allow for inspection.
        """
        if isinstance(msg, dict):
            method = msg.get("method")

            if method == "Page.screencastFrame":
                try:
                    frame_data = msg.get("params", {})
                    session_id = msg.get("sessionId")
                    if isinstance(frame_data, dict):
                        await self.screencast_util.handle_screencast_frame(frame_data, session_id)
                except Exception as e:
                    print(f"[DEBUG] Error handling screencast frame: {e}")

            if method == "Target.targetCreated":
                try:
                    params = msg.get("params", {})
                    if isinstance(params, dict):
                        target_info = params.get("targetInfo", {})
                    new_page_attached = await self.target_manager.handle_target_created(target_info)
                    if new_page_attached:
                        target_id = target_info.get("targetId")
                        if target_id in self.client.get_session_ids():
                            session_id = self.client.get_session_ids()[target_id]
                            await self.target_manager.enable_domains_on_all_sessions()

                            if (
                                self.screencast_util._screencast_recording
                                and self.screencast_util._screencast_params
                            ):
                                await self.client.send(
                                    "Page.startScreencast",
                                    params=self.screencast_util._screencast_params,
                                    session_id=session_id,
                                )
                except Exception as e:
                    print(f"[DEBUG] Error handling target creation: {e}")

    def add_log_entry(self, log_entry: str, log_type: str) -> None:
        """Add a log entry for VLM evaluation.

        Args:
            log_entry: The log message to collect
            log_type: Type of log (e.g., 'action', 'eval', 'tool', 'thought', 'final')
        """
        if not log_entry:
            return

        if not log_type:
            raise ValueError("log_type must be provided")

        self.collected_logs.append((log_entry, log_type))

        if log_type == "final":
            self.final_result = log_entry

    async def run_vlm_evaluation(self) -> EvaluationResult | None:
        """Run VLM evaluation on collected data."""
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            print("[VLM] Skipping evaluation - OPENAI_API_KEY not found in environment")
            return None

        if not self.task:
            print("[VLM] No task specified for evaluation")
            return None

        if not self.collected_screenshots and not self.collected_logs:
            print("[VLM] No data collected for evaluation")
            return None

        try:
            evaluator = VLMEvaluator(api_key=openai_api_key)

            run_data = RunData(
                task=self.task,
                screenshots=self.collected_screenshots,
                logs=self.collected_logs,
                final_result=self.final_result,
            )

            result = await evaluator.evaluate_run(run_data)
            return result

        except Exception as e:
            print(f"[VLM] Error during evaluation: {e}")
            import traceback

            traceback.print_exc()
            return None
