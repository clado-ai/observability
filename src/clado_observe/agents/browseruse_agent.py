import asyncio
import logging
import time

from browser_use.agent.service import Agent
from browser_use.browser.session import BrowserSession
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

        self.browser_session = BrowserSession(
            cdp_url=cdp_url,
            headless=False,
            is_local=False,
        )

        self.agent = Agent(
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

                    if record.name and (record.name in ["Agent", "tools"]):
                        print(msg)

                except Exception as e:
                    print(f"[DEBUG CAPTURE ERROR] {e}")

        self._log_handler = LogCaptureHandler(self)
        browser_use_logger = logging.getLogger("browser_use")
        browser_use_logger.addHandler(self._log_handler)

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

        except Exception as e:
            print(f"[DEBUG] Error during agent execution: {e}")
        finally:
            self._end_screencast_sync()
            time.sleep(1.0)
            self.observer.stop_background()
            if hasattr(self, "_log_handler"):
                logging.getLogger().removeHandler(self._log_handler)
                logging.getLogger("browser_use").removeHandler(self._log_handler)

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
