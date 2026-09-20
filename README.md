# eFootball AI Squad Doctor V2

V2 adds screenshot-based squad recognition using a vision model.

## New features

- 📸 Send an eFootball squad screenshot
- 🤖 Vision AI extracts visible formation, playstyle, player names/positions/playing styles
- 🧠 Tactical heuristic analyzes the extracted squad
- 👥 Shows recognized players and visibility notes
- Existing text analysis remains available

## Render

Use the existing Render Web Service.

Build:
pip install -r requirements.txt

Start:
uvicorn app:app --host 0.0.0.0 --port $PORT

Environment variables:

BOT_TOKEN = your Telegram BotFather token
OPENAI_API_KEY = your OpenAI API key
VISION_MODEL = gpt-5.6-luna
PUBLIC_URL = your Render service URL
WEBHOOK_SECRET = optional random secret

The screenshot module uses a vision-capable OpenAI model. OpenAI's current model documentation lists GPT-5.6 Luna as a cost-sensitive model with image input support. API usage can incur charges, so set usage limits/budget controls in your API account before testing at scale.

## Telegram

After deployment, use:
 /start
 /screenshot

Then send a clear full-squad screenshot.

## Important

Vision extraction can make mistakes when text is small, cropped, blurred, covered by UI elements, or otherwise unreadable. The bot is instructed not to invent unreadable player information.

SQLite is suitable for an MVP but is not durable storage for production. Move user/squad data to managed Postgres later.
