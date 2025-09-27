import os

from browser_use.llm import ChatAnthropic
from dotenv import load_dotenv

from clado_observe import BrowserUseAgent

load_dotenv()


def main() -> None:
    cdp_url = os.getenv("WEBSOCKET_DEBUGGER_URL")
    if not cdp_url:
        raise RuntimeError("WEBSOCKET_DEBUGGER_URL not set in environment")

    agent = BrowserUseAgent(
        task="Find the number of stars of the browser-use repo",
        llm=ChatAnthropic(model="claude-sonnet-4-0"),
        cdp_url=cdp_url,
    )

    agent.run_sync()


if __name__ == "__main__":
    main()
