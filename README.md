# Snapdeal Voice Bot — Priya

A voice-enabled AI customer support assistant for Snapdeal, powered by OpenAI's Realtime API. Users can speak directly to Priya, who handles order lookups, returns, refunds, product searches, and human escalation in real time.

## Features

- **Voice conversation** — click to start speaking, click again to stop
- **Real-time AI responses** — streamed audio and transcript via OpenAI `gpt-realtime-2`
- **Order management** — look up orders by ID or email, check status, initiate returns
- **Refunds** — process refunds to wallet or original payment method
- **Product search** — find products by name or category
- **Human escalation** — hand off to a human agent with queue position and wait time
- **Live transcript** — conversation displayed in real time on screen
- **Test data panel** — mock orders and accounts shown alongside the chat for easy testing

## Tech Stack

- **Backend** — Python / FastAPI, WebSocket proxy to OpenAI Realtime API
- **Frontend** — Vanilla JS, HTML, CSS (no framework, all JS inlined)
- **AI model** — `gpt-realtime-2` with `marin` voice
- **Server** — Gunicorn + Uvicorn workers (ASGI)

## Project Structure

```
main.py           # FastAPI app + WebSocket proxy to OpenAI
tools.py          # Tool schemas and dispatch logic for function calling
mock_data.py      # In-memory mock orders, accounts, and products
system_prompt.py  # System instructions for Priya's personality and behaviour
static/
  index.html      # Main UI (all JS inlined — no external script dependencies)
  app.js          # Standalone JS (kept for reference / tests)
  style.css       # Styling
tests/            # pytest test suite
requirements.txt  # Python dependencies
```

## Getting Started

### Prerequisites

- Python 3.10+
- An OpenAI API key with access to the Realtime API (`gpt-realtime-2`)

### Installation

```bash
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root:

```
OPENAI_API_KEY=your_openai_api_key_here
```

### Running

```bash
uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

Then open [http://localhost:5000](http://localhost:5000) in your browser.

## Usage

1. Click **Start Session** to connect to Priya
2. Click the microphone button to start speaking
3. Click it again when you're done — Priya will respond
4. Click **End Session** to disconnect

### Example things to say

- "Where is my order ORD001?"
- "I want to return my Nike shoes"
- "Can I get a refund for order ORD004?"
- "Show me smartphones under ₹20,000"
- "I want to speak to a human agent"

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Main app UI |
| `GET` | `/app` | Alternative entry point (cache-bypass URL) |
| `GET` | `/api/mock-data` | Returns mock orders and accounts as JSON |
| `WS` | `/ws` | WebSocket proxy to OpenAI Realtime API |

## Deployment

Configured as an **Autoscale** deployment — the server starts when a user opens the app and shuts down after they leave. You are only charged for actual usage time, not 24/7.

Production run command (Gunicorn + Uvicorn workers):
```bash
gunicorn --bind=0.0.0.0:5000 --reuse-port --worker-class=uvicorn.workers.UvicornWorker main:app
```

## OpenAI Realtime API Notes

This app uses the OpenAI Realtime GA API (`/v1/realtime`):

- **Model**: `gpt-realtime-2`
- **Session type**: `realtime`
- **Audio format**: `audio/pcm` at 24 kHz (input and output)
- **Turn detection**: disabled (manual — user clicks to start/stop)
- **Transcription**: `whisper-1` for user speech
- **No** `OpenAI-Beta` header required (GA API)

## Mock Data

The app ships with in-memory test data — no database required:

- **6 orders** across various statuses: delivered, in transit, delayed, cancelled, return initiated, refund processed
- **2 accounts** with associated orders and wallet balances
- **Sample products** across categories including electronics, footwear, and appliances

## License

MIT
