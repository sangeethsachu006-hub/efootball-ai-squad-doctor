# eFootball AI Squad Doctor — Free Render Web Service

This version uses a Telegram webhook + FastAPI so it can run as a Render Web Service instead of a paid Background Worker.

## Render settings

Service type: Web Service
Plan: Free

Build command:
pip install -r requirements.txt

Start command:
uvicorn app:app --host 0.0.0.0 --port $PORT

Environment variables:
- BOT_TOKEN = your Telegram BotFather token
- PUBLIC_URL = your Render service URL, e.g. https://efootball-ai-squad-doctor.onrender.com
- WEBHOOK_SECRET = a random secret string (recommended)

## Important

The current MVP is still text-based tactical analysis. Screenshot recognition, player database, AI vision, squad builder, pack analyzer and other advanced modules can be added next.

Render's free web services are intended for testing/hobby use and can spin down when idle. SQLite data on a free service is not durable across every restart/redeploy, so use a managed database later if saved data becomes important.
