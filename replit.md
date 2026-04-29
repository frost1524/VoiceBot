# Snapdeal Voice Bot (Priya)

A voice-enabled AI customer support bot for Snapdeal, powered by OpenAI's Realtime API.

## Architecture

- **Backend**: Python / FastAPI serving as a WebSocket proxy between the browser and OpenAI's Realtime API
- **Frontend**: Vanilla JS + HTML/CSS served as static files via FastAPI
- **AI**: OpenAI `gpt-4o-realtime-preview` model with `alloy` voice
- **Mock Data**: In-memory mock orders, accounts, and products (`mock_data.py`)
- **Tools**: Function calling for order lookup, returns, refunds, product search, and human escalation (`tools.py`)

## Project Structure

```
main.py          # FastAPI app + WebSocket proxy to OpenAI
tools.py         # Tool schemas and dispatch logic
mock_data.py     # Mock ACCOUNTS, ORDERS, PRODUCTS
system_prompt.py # System instructions for the AI
static/
  index.html     # Main UI with test data dashboard
  app.js         # Audio/WebSocket client logic
  style.css      # Styling
tests/           # pytest test suite
requirements.txt # Python dependencies
```

## Running

The app runs via uvicorn on port 5000:
```
uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

## Environment Variables

- `OPENAI_API_KEY` — Required. OpenAI API key with access to the Realtime API.

## Deployment

Configured as a `vm` deployment (always-running) since WebSocket connections require persistent processes.
Run command: `uvicorn main:app --host 0.0.0.0 --port 5000`
