from browser_use.agent.service import Agent
from browser_use.llm import ChatAnthropic
from dotenv import load_dotenv
import os
load_dotenv()

agent = Agent(
    task="Find the number of stars of the browser-use repo",
    llm=ChatAnthropic(model="claude-sonnet-4-0"),
    cdp_url=os.getenv("WEBSOCKET_DEBUGGER_URL")
)
agent.run_sync()
