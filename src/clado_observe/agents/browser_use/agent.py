import asyncio
import base64
import logging
import os
import time
import re
import threading
from queue import Queue
from typing import Optional, Tuple

from browser_use.agent.service import Agent as BrowserUseAgent
from browser_use.browser.session import BrowserSession
from browser_use.llm import BaseChatModel

from ...cdp.observer import CDPObserver
from ...utils.api_client import APIClient


class Agent:
    """
    An agent wrapper that combines browser-use's Agent with CDP observation capabilities.
    This allows you to run browser automation tasks while simultaneously observing
    the browser's behavior through Chrome DevTools Protocol.
    """

    def __init__(
        self,
        task: str,
        llm: BaseChatModel,
        cdp_url: str,
        api_key: str,
        **agent_kwargs,
    ) -> None:
        """
        Initialize the BrowserUseAgent with both browser-use Agent and CDP observation capabilities.

        Args:
            task: The task description for the browser-use agent
            llm: The language model to use for the agent
            cdp_url: The CDP WebSocket URL to connect to
            api_key: API key for the observability API (localhost:3000)
            **agent_kwargs: Additional arguments passed to the browser-use Agent
        """
        if not task or not isinstance(task, str):
            raise ValueError("task must be a non-empty string")
        if not cdp_url or not isinstance(cdp_url, str):
            raise ValueError("cdp_url must be a non-empty string")
        if not llm or not isinstance(llm, BaseChatModel):
            raise ValueError("llm must be a non-empty BrowserUse BaseChatModel")
        if not api_key or not isinstance(api_key, str):
            raise ValueError("api_key must be a non-empty string")

        self.task = task
        self.cdp_url = cdp_url
        self.api_key = api_key
        self.agent_kwargs = agent_kwargs

        self.api_client = APIClient(api_key=api_key)

        self.model_name = str(llm.model) if hasattr(llm, "model") else "unknown"

        self._trace_loop: Optional[asyncio.AbstractEventLoop] = None
        self._trace_thread: Optional[threading.Thread] = None
        self._trace_queue: Queue[Tuple[str, str, bool]] = Queue()

        self._setup_log_capture()

        self.observer = CDPObserver(cdp_url=cdp_url, task=task)

        self.browser_session = BrowserSession(
            cdp_url=cdp_url,
            headless=False,
            is_local=False,
        )

        self.agent = BrowserUseAgent(
            task=task,
            llm=llm,
            browser=self.browser_session,
            **agent_kwargs,
        )

    def _setup_log_capture(self) -> None:
        """Setup log capture for browser-use agent logs using Python logging handlers."""

        class LogCaptureHandler(logging.Handler):
            def __init__(self, agent_instance):
                super().__init__()
                self.agent = agent_instance
                self.setFormatter(logging.Formatter("%(levelname)-8s [%(name)s] %(message)s"))

            def emit(self, record):
                try:
                    msg = self.format(record)

                    if (
                        record.levelno == logging.INFO
                        and record.name
                        and record.name in ["Agent", "tools", "BrowserSession", "service"]
                    ):
                        clean_msg = re.sub(r"^(INFO|WARNING|ERROR|DEBUG)\s+\[[\w.]+\]\s*", "", msg)
                        clean_msg = re.sub(r"\x1b\[[0-9;]*m", "", clean_msg)
                        clean_msg = clean_msg.strip()

                        if clean_msg and not clean_msg.isspace():
                            if len(clean_msg) > 2000:
                                return

                            if record.name == "BrowserSession":
                                trace_type = "tool"
                            elif self.agent.api_client:
                                trace_type = self.agent.api_client.detect_trace_type(
                                    record.name, msg
                                )
                            else:
                                trace_type = "thought"

                            if self.agent.observer:
                                self.agent.observer.add_log_entry(clean_msg, trace_type)

                            if self.agent.api_client and self.agent.api_client.session_id:
                                need_browser_data = trace_type == "tool" or trace_type == "final"
                                try:
                                    asyncio.get_running_loop()
                                except RuntimeError:
                                    pass

                                self.agent._trace_queue.put(
                                    (trace_type, clean_msg, need_browser_data)
                                )

                except Exception as e:
                    print(f"[DEBUG CAPTURE ERROR] {e}")

        self._log_handler = LogCaptureHandler(self)
        browser_use_logger = logging.getLogger("browser_use")
        browser_use_logger.addHandler(self._log_handler)

    def _start_trace_thread(self):
        """Start a background thread with its own event loop for sending traces."""

        def run_trace_loop():
            self._trace_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._trace_loop)
            self._trace_loop.create_task(self._process_trace_queue())
            self._trace_loop.run_forever()

        self._trace_thread = threading.Thread(target=run_trace_loop, daemon=True)
        self._trace_thread.start()
        time.sleep(0.1)

    async def _process_trace_queue(self):
        """Process traces from the queue in order."""
        while True:
            try:
                if not self._trace_queue.empty():
                    trace_type, content, need_browser_data = self._trace_queue.get()

                    try:
                        if need_browser_data:
                            dom_data = None

                            try:
                                screenshot_future = asyncio.run_coroutine_threadsafe(
                                    self.observer.screenshot(), self.observer.client._loop
                                )
                                screenshot = screenshot_future.result(timeout=5.0)

                                if screenshot:
                                    await self.api_client.upload_media(
                                        media_type="image", data=screenshot
                                    )

                                dom_future = asyncio.run_coroutine_threadsafe(
                                    self.observer.snapshot(), self.observer.client._loop
                                )
                                dom_data = dom_future.result(timeout=5.0)

                                await self.api_client.create_trace("dom", content=str(dom_data))
                                await self.api_client.create_trace("tool", content=content)

                            except Exception as e:
                                print(f"[DEBUG] Failed to capture screenshot/DOM: {e}")
                                import traceback

                                traceback.print_exc()
                        else:
                            await self.api_client.create_trace(trace_type, content)

                    except Exception as e:
                        print(f"[DEBUG] Failed to send trace: {e}")
                        import traceback

                        traceback.print_exc()
                else:
                    await asyncio.sleep(0.1)
            except Exception as e:
                print(f"[DEBUG] Queue processor error: {e}")
                await asyncio.sleep(0.1)

    async def _send_trace_async(self, trace_type, message):
        """Async wrapper to send a trace."""
        try:
            await self.api_client.create_trace(trace_type, message)
        except Exception as e:
            print(f"[DEBUG] Failed to send trace: {e}")

    def _stop_trace_thread(self):
        """Stop the background trace thread and clean up properly."""
        if self._trace_loop and self._trace_loop.is_running():

            async def cleanup_and_stop():
                for _ in range(20):
                    if self._trace_queue.empty():
                        break
                    await asyncio.sleep(0.1)

                tasks = [
                    t for t in asyncio.all_tasks(self._trace_loop) if t != asyncio.current_task()
                ]
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                await self.api_client.close()
                self._trace_loop.stop()

            asyncio.run_coroutine_threadsafe(cleanup_and_stop(), self._trace_loop)

        if self._trace_thread:
            self._trace_thread.join(timeout=3)

    def run_sync(self) -> None:
        """
        Run the agent synchronously with CDP observation.
        Starts the observer in the background, runs the agent, then stops the observer.
        """
        self._start_trace_thread()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._sync_loop = loop

        try:
            try:
                loop.run_until_complete(
                    self.api_client.create_session(
                        prompt=self.task,
                        model=self.model_name,
                        param={"cdp_url": self.cdp_url, "agent_kwargs": self.agent_kwargs},
                    )
                )
            except Exception as e:
                print(f"[API] Failed to create session: {e}")

            self.observer.start_background()

            try:
                loop.run_until_complete(self.observer.start_screencast())

                self.agent.run_sync()

            except Exception as e:
                print(f"[DEBUG] Error during agent execution: {e}")
            finally:
                try:
                    video_path = loop.run_until_complete(self.observer.end_screencast())
                    if video_path and os.path.exists(video_path):
                        try:
                            with open(video_path, "rb") as video_file:
                                video_data = video_file.read()
                                video_base64 = base64.b64encode(video_data).decode("utf-8")
                                video_data_uri = f"data:video/mp4;base64,{video_base64}"

                            loop.run_until_complete(
                                self.api_client.upload_media(
                                    media_type="video", data=video_data_uri
                                )
                            )

                            try:
                                self.observer.screencast_util.cleanup_temp_files()
                            except Exception as e:
                                print(f"[DEBUG] Failed to cleanup temp files: {e}")

                        except Exception as e:
                            print(f"[DEBUG] Failed to upload video: {e}")
                except Exception as e:
                    print(f"[DEBUG] Failed to end screencast: {e}")

                try:
                    vlm_result = loop.run_until_complete(self.observer.run_vlm_evaluation())
                    print(f"[VLM] Evaluation result: {vlm_result}")
                except Exception as e:
                    print(f"[VLM] Failed to run evaluation: {e}")

                self.observer.stop_background()
                if self.api_client.session_id:
                    try:
                        loop.run_until_complete(self.api_client.end_session())
                    except Exception as e:
                        print(f"[API] Failed to end session: {e}")

                try:
                    loop.run_until_complete(self.api_client.close())
                except Exception:
                    pass

                if hasattr(self, "_log_handler"):
                    logging.getLogger("browser_use").removeHandler(self._log_handler)

        finally:
            self._stop_trace_thread()

            loop.close()
            if hasattr(self, "_sync_loop"):
                delattr(self, "_sync_loop")
