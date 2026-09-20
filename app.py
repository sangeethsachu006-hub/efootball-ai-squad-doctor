import os
import logging
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

from vision import analyze_squad_image
from squad_analyzer import analyze_squad_data

TOKEN = os.getenv("BOT_TOKEN")
PUBLIC_URL = os.getenv("PUBLIC_URL") or os.getenv("RENDER_EXTERNAL_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is required.")
if not PUBLIC_URL:
    raise RuntimeError("PUBLIC_URL (or RENDER_EXTERNAL_URL) is required.")

PUBLIC_URL = PUBLIC_URL.rstrip("/")
WEBHOOK_PATH = "/telegram/webhook"
DB = "bot.db"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def db():
    c = sqlite3.connect(DB)
    c.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY,
            username TEXT,
            analyses INTEGER DEFAULT 0,
            screenshots INTEGER DEFAULT 0
        )
    """)
    c.commit()
    return c


def touch(u):
    c = db()
    c.execute(
        "INSERT OR IGNORE INTO users(id,username) VALUES(?,?,?)",
        (u.id, u.username)
    )
    c.commit()
    c.close()


def increment(user_id, field):
    if field not in {"analyses", "screenshots"}:
        return
    c = db()
    c.execute(f"UPDATE users SET {field}={field}+1 WHERE id=?", (user_id,))
    c.commit()
    c.close()


def parse(t):
    d = {}
    for line in t.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            d[k.strip().lower()] = v.strip()
    return d


def text_analyze(d):
    return analyze_squad_data(d)


HELP = """⚽ *eFootball AI Squad Doctor V2*

/start — dashboard
/analyze — analyze a squad by text
/screenshot — analyze an eFootball screenshot
/example — sample text input
/compare — compare two players (text mode)
/saved — usage stats
/help — help

📸 *New V2 feature:* send an eFootball squad screenshot and the bot will use Gemini vision AI to identify the visible squad structure and generate tactical recommendations.

⚠️ Screenshot recognition requires an `GEMINI_API_KEY` on the Render service.
"""


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    touch(update.effective_user)
    kb = [
        [
            InlineKeyboardButton("🩺 Text Analyze", callback_data="analyze"),
            InlineKeyboardButton("📸 Screenshot", callback_data="screenshot")
        ],
        [
            InlineKeyboardButton("📋 Example", callback_data="example"),
            InlineKeyboardButton("ℹ️ Help", callback_data="help")
        ]
    ]
    await update.message.reply_text(
        HELP, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def analyze_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    touch(update.effective_user)
    ctx.user_data["mode"] = "analyze"
    await update.message.reply_text(
        "Send squad details. Use /example for the format."
    )


async def screenshot_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    touch(update.effective_user)
    ctx.user_data["mode"] = "screenshot"
    if not os.getenv("GEMINI_API_KEY"):
        await update.message.reply_text(
            "📸 Screenshot Analyzer is installed, but the Gemini vision API key is not configured yet.\n\n"
            "Add GEMINI_API_KEY to Render Environment Variables, then try again."
        )
        return
    await update.message.reply_text(
        "📸 Send your eFootball squad screenshot now.\n\n"
        "For best results, send the clearest screenshot showing the full formation and player cards."
    )


async def example(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""Formation: 4-2-1-3
Playstyle: Possession
GK: Offensive GK
CB1: Build Up
CB2: Destroyer
LB: Offensive Fullback
RB: Defensive Fullback
DMF1: Anchor Man
DMF2: Box-to-Box
AMF: Creative Playmaker
LWF: Roaming Flank
RWF: Prolific Winger
CF: Goal Poacher""")


async def compare(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["mode"] = "compare"
    await update.message.reply_text(
        "Send: Player A vs Player B\nExample: Mbappe vs Haaland"
    )


async def saved(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    c = db()
    row = c.execute(
        "SELECT analyses, screenshots FROM users WHERE id=?",
        (update.effective_user.id,)
    ).fetchone()
    c.close()
    analyses, screenshots = row if row else (0, 0)
    await update.message.reply_text(
        f"📊 Text analyses: {analyses}\n📸 Screenshot analyses: {screenshots}"
    )


async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP, parse_mode="Markdown")


async def buttons(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "analyze":
        ctx.user_data["mode"] = "analyze"
        await q.message.reply_text("Send your squad details.")
    elif q.data == "screenshot":
        ctx.user_data["mode"] = "screenshot"
        if not os.getenv("GEMINI_API_KEY"):
            await q.message.reply_text(
                "📸 Add GEMINI_API_KEY to Render Environment Variables first."
            )
        else:
            await q.message.reply_text(
                "📸 Send your eFootball squad screenshot now."
            )
    elif q.data == "example":
        await q.message.reply_text("Use /example.")
    else:
        await q.message.reply_text(HELP, parse_mode="Markdown")


async def text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    mode = ctx.user_data.get("mode")

    if mode == "analyze":
        d = parse(update.message.text)
        if "formation" not in d:
            await update.message.reply_text(
                "Please include Formation: ...\nUse /example."
            )
            return

        result = text_analyze(d)
        increment(update.effective_user.id, "analyses")
        await update.message.reply_text(result, parse_mode="Markdown")
        ctx.user_data["mode"] = None

    elif mode == "compare":
        s = update.message.text
        await update.message.reply_text(
            f"🆚 *Player comparison placeholder*\n\n{s}\n\n"
            "Player database comparison will be added as the next data module.",
            parse_mode="Markdown"
        )
        ctx.user_data["mode"] = None

    else:
        await update.message.reply_text(
            "Use /analyze or /screenshot to start."
        )


async def photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.photo:
        return

    touch(update.effective_user)

    if not os.getenv("GEMINI_API_KEY"):
        await update.message.reply_text(
            "📸 I received your screenshot, but screenshot AI is not configured yet.\n\n"
            "Add GEMINI_API_KEY in Render → Environment Variables."
        )
        return

    status = await update.message.reply_text("🔍 Reading your squad screenshot...")

    try:
        tg_file = await update.message.photo[-1].get_file()
        image_bytes = bytes(await tg_file.download_as_bytearray())

        data = await analyze_squad_image(image_bytes)
        result = analyze_squad_data(data, from_vision=True)

        increment(update.effective_user.id, "screenshots")
        await status.edit_text(result, parse_mode="Markdown")
        ctx.user_data["mode"] = None

    except Exception:
        logger.exception("Screenshot analysis failed")
        await status.edit_text(
            "❌ I couldn't analyze that screenshot.\n\n"
            "Try a clearer full-squad screenshot. If it keeps failing, check the Render logs."
        )


telegram_app = Application.builder().token(TOKEN).build()

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("analyze", analyze_cmd))
telegram_app.add_handler(CommandHandler("screenshot", screenshot_cmd))
telegram_app.add_handler(CommandHandler("example", example))
telegram_app.add_handler(CommandHandler("compare", compare))
telegram_app.add_handler(CommandHandler("saved", saved))
telegram_app.add_handler(CommandHandler("help", help_cmd))
telegram_app.add_handler(CallbackQueryHandler(buttons))
telegram_app.add_handler(MessageHandler(filters.PHOTO, photo))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await telegram_app.initialize()
    await telegram_app.start()

    await telegram_app.bot.set_webhook(
        url=f"{PUBLIC_URL}{WEBHOOK_PATH}",
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        secret_token=WEBHOOK_SECRET or None,
    )
    logger.info("Telegram webhook configured: %s%s", PUBLIC_URL, WEBHOOK_PATH)

    yield

    try:
        await telegram_app.bot.delete_webhook()
    finally:
        await telegram_app.stop()
        await telegram_app.shutdown()


app = FastAPI(
    title="eFootball AI Squad Doctor V2",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {"status": "ok", "service": "efootball-ai-squad-doctor", "version": "2.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    if WEBHOOK_SECRET:
        incoming = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if incoming != WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="Invalid webhook secret")

    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.update_queue.put(update)
    return {"ok": True}
