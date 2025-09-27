import asyncio
import logging
import time

from browser_use.agent.service import Agent
from browser_use.llm import BaseChatModel

from ..cdp.observer import CDPObserver


class BrowserUseAgent:
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
        **agent_kwargs,
    ) -> None:
        """
        Initialize the BrowserUseAgent with both browser-use Agent and CDP observation capabilities.

        Args:
            task: The task description for the browser-use agent
            llm: The language model to use for the agent
            cdp_url: The CDP WebSocket URL to connect to
            **agent_kwargs: Additional arguments passed to the browser-use Agent
        """
        if not task or not isinstance(task, str):
            raise ValueError("task must be a non-empty string")
        if not cdp_url or not isinstance(cdp_url, str):
            raise ValueError("cdp_url must be a non-empty string")
        if not llm or not isinstance(llm, BaseChatModel):
            raise ValueError("llm must be a non-empty BrowserUse BaseChatModel")

        self.cdp_url = cdp_url

        self._setup_log_capture()

        self.observer = CDPObserver(cdp_url=cdp_url)

        self.agent = Agent(
            task=task,
            llm=llm,
            cdp_url=cdp_url,
            **agent_kwargs,
        )

    def _setup_log_capture(self) -> None:
        """Setup log capture for browser-use agent logs."""

        class LogCaptureHandler(logging.Handler):
            def __init__(self, agent_instance):
                super().__init__()
                self.agent = agent_instance

            def emit(self, record):
                log_message = self.format(record)
                print(f"[DEBUG] Log message: {log_message}")

                if hasattr(self.agent, "_capture_step_data"):
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(self.agent._capture_step_data())
                        else:
                            loop.run_until_complete(self.agent._capture_step_data())
                    except Exception as e:
                        print(f"[DEBUG] Error capturing step data: {e}")

        agent_logger = logging.getLogger("Agent")
        agent_logger.addHandler(LogCaptureHandler(self))
        agent_logger.setLevel(logging.INFO)

        tools_logger = logging.getLogger("tools")
        tools_logger.addHandler(LogCaptureHandler(self))
        tools_logger.setLevel(logging.INFO)

        service_logger = logging.getLogger("service")
        service_logger.addHandler(LogCaptureHandler(self))
        service_logger.setLevel(logging.INFO)

        browsersession_logger = logging.getLogger("BrowserSession")
        browsersession_logger.addHandler(LogCaptureHandler(self))
        browsersession_logger.setLevel(logging.INFO)

    async def _capture_step_data(self) -> None:
        """Capture snapshot and screenshot data for the current step."""
        try:
            await self.observer.snapshot()
            await self.observer.screenshot()

            print("[DEBUG] Captured step data")
        except Exception as e:
            print(f"[DEBUG] Failed to capture step data: {e}")

    def _start_screencast_sync(self) -> None:
        """Start screencast synchronously."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.observer.start_screencast())
            else:
                loop.run_until_complete(self.observer.start_screencast())
        except Exception as e:
            print(f"[DEBUG] Failed to start screencast synchronously: {e}")

    def _end_screencast_sync(self) -> None:
        """End screencast synchronously."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.observer.end_screencast())
            else:
                loop.run_until_complete(self.observer.end_screencast())
        except Exception as e:
            print(f"[DEBUG] Failed to end screencast synchronously: {e}")

    def run_sync(self) -> None:
        """
        Run the agent synchronously with CDP observation.
        Starts the observer in the background, runs the agent, then stops the observer.
        """
        self.observer.start_background()

        try:
            self._start_screencast_sync()
            self.agent.run_sync()
        finally:
            self._end_screencast_sync()
            time.sleep(1.0)
            self.observer.stop_background()

    async def run_async(self) -> None:
        """
        Run the agent asynchronously with CDP observation.
        Starts the observer, runs the agent, then stops the observer.
        """
        await self.observer.start()

        try:
            await self.observer.start_screencast()
            await self.agent.run_async()
        finally:
            await self.observer.end_screencast()
            await self.observer.stop()
