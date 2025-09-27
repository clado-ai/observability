# Clado Observe

A Python SDK for browser automation and observability using Chrome DevTools Protocol (CDP).

## Features

- Browser automation through Chrome DevTools Protocol
- Integration with Browser Use agents
- WebSocket-based communication with Chrome instances
- Screenshot and screencast capabilities
- DOM manipulation and observation
- Vision-Language Model (VLM) evaluation support

## Installation

```bash
pip install clado-observe
```

## Quick Start

```python
import os

from browser_use.llm import ChatAnthropic
from dotenv import load_dotenv

from clado_observe.agents.browser_use import Agent

load_dotenv()


def main() -> None:
    agent = Agent(
        task="Find the number of stars of the browser-use repo",
        llm=ChatAnthropic(model="claude-sonnet-4-0"),
        cdp_url=cdp_url,
        api_key=os.getenv("CLADO_API_KEY", ""),
    )

    agent.run_sync()

if __name__ == "__main__":
    main()
```

## Local Development

### Testing with Chrome DevTools

To test locally, you need a Chrome DevTools WebSocket debugger URL.

#### 1) Start Chrome with remote debugging enabled

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-debug
```

Keep this Chrome instance running while you test.

#### 2) Verify and copy the WebSocket URL

Open `http://localhost:9222/json/version` in your browser. Find the `webSocketDebuggerUrl` field and copy its value. It will look like:

```
ws://localhost:9222/devtools/browser/<some-guid>
```

#### 3) Set your `.env`

Create or update `.env` with your keys and the copied URL:

```bash
ANTHROPIC_API_KEY=sk-...
WEBSOCKET_DEBUGGER_URL=ws://localhost:9222/devtools/browser/<some-guid>
```

## Documentation

For more detailed documentation, please visit [https://github.com/clado-ai/observability](https://github.com/clado-ai/observability)

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and feature requests, please use the [GitHub issue tracker](https://github.com/clado-ai/observability/issues).