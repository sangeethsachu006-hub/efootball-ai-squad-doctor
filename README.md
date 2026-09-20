# eFootball AI Squad Doctor — Gemini Free Vision

Telegram bot for eFootball squad analysis.

## Features
- Text squad analysis
- Screenshot-based squad recognition
- Formation/playstyle/position extraction
- Tactical recommendations
- SQLite usage tracking

## Free vision setup
This version uses the Google Gemini API instead of OpenAI. The default model is `gemini-2.5-flash-lite`.

Create a Gemini API key in Google AI Studio and add it to Render as:
- `GEMINI_API_KEY`

Do not commit API keys to GitHub.

## Render
Build:
`pip install -r requirements.txt`

Start:
`uvicorn app:app --host 0.0.0.0 --port $PORT`

Required environment variables:
- `BOT_TOKEN`
- `GEMINI_API_KEY`
- `PUBLIC_URL` (or Render's `RENDER_EXTERNAL_URL`)
- optional `VISION_MODEL`
- optional `WEBHOOK_SECRET`

## Notes
The Gemini Free Tier has rate limits. Free availability can change, so do not assume unlimited requests.
Render Free Web Services can spin down when idle.
