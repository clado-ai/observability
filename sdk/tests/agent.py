from browser_use.agent.service import Agent
from browser_use.llm import ChatAnthropic
from dotenv import load_dotenv
load_dotenv()

agent = Agent(
    task="Find the number of stars of the browser-use repo",
    llm=ChatAnthropic(model="claude-sonnet-4-0")
)
agent.run_sync()