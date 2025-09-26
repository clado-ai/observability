## Local testing: WebSocket debugger URL (macOS)

To test locally, you need a Chrome DevTools WebSocket debugger URL.

### 1) Start Chrome with remote debugging enabled

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-debug
```

Keep this Chrome instance running while you test.

### 2) Verify and copy the WebSocket URL

Open `http://localhost:9222/json/version` in your browser. Find the `webSocketDebuggerUrl` field and copy its value. It will look like:

```
ws://localhost:9222/devtools/browser/<some-guid>
```

### 3) Set your `.env`

Create or update `sdk/.env` with your keys and the copied URL:

```bash
ANTHROPIC_API_KEY=sk-...
WEBSOCKET_DEBUGGER_URL=ws://localhost:9222/devtools/browser/<some-guid>
```