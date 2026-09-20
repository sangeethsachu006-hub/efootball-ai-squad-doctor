import os
import logging
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
PUBLIC_URL = os.getenv("PUBLIC_URL") or os.getenv("RENDER_EXTERNAL_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is required.")
if not PUBLIC_URL:
    raise RuntimeError("PUBLIC_URL (or Render's RENDER_EXTERNAL_URL) is required.")

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
            analyses INTEGER DEFAULT 0
        )
    """)
    c.commit()
    return c

def touch(u):
    c = db()
    c.execute(
        "INSERT OR IGNORE INTO users(id,username) VALUES(?,?)",
        (u.id, u.username)
    )
    c.commit()
    c.close()

def parse(t):
    d = {}
    for line in t.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            d[k.strip().lower()] = v.strip()
    return d

def analyze(d):
    p = " ".join(d.values()).lower()
    score = 70
    issues, fixes = [], []

    if "anchor man" not in p:
        issues.append("No Anchor Man detected in the supplied squad.")
        fixes.append("Consider an Anchor Man if you need central defensive protection.")
    else:
        score += 8

    if "build up" not in p:
        issues.append("No Build Up CB detected.")
        fixes.append("Consider a Build Up CB for safer first-phase progression.")
    else:
        score += 7

    if "goal poacher" not in p and "fox in the box" not in p:
        issues.append("No obvious penalty-box finisher detected.")
        fixes.append("Consider a Goal Poacher/Fox in the Box.")
    else:
        score += 6

    if "defensive fullback" in p:
        score += 3

    if "possession" in p and "offensive fullback" not in p:
        fixes.append("One attacking fullback could provide additional width, if midfield cover is adequate.")

    if "quick counter" in p:
        fixes.append("Prioritize pace, direct passing and runners behind the defensive line.")

    score = min(100, score)

    return f"""⚽ *eFOOTBALL AI SQUAD DOCTOR*

📐 Formation: *{d.get('formation','Unknown')}*
🎮 Playstyle: *{d.get('playstyle','Unknown')}*
⭐ Structural score: *{score}/100*

🔴 *Potential issues*
""" + "\n".join("• " + x for x in issues) + """

🔧 *Recommendations*
""" + "\n".join("• " + x for x in fixes) + """

ℹ️ This is a tactical heuristic, not an official Konami rating."""

HELP = """⚽ *eFootball AI Squad Doctor*

Commands:
/start — dashboard
/analyze — analyze a squad
/example — sample input
/compare — compare two players (text mode)
/saved — saved analysis count
/help — help

Current MVP: text-based tactical analysis.
Next modules: screenshot recognition, player database, AI vision, squad builder and pack/value tools.
"""

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    touch(update.effective_user)
    kb = [
        [
            InlineKeyboardButton("🩺 Analyze Squad", callback_data="analyze"),
            InlineKeyboardButton("📋 Example", callback_data="example")
        ],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ]
    await update.message.reply_text(
        HELP,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def analyze_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    touch(update.effective_user)
    ctx.user_data["mode"] = "analyze"
    await update.message.reply_text("Send your squad details. Use /example for the format.")

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
    await update.message.reply_text("Send: Player A vs Player B\nExample: Mbappe vs Haaland")

async def saved(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    c = db()
    row = c.execute(
        "SELECT analyses FROM users WHERE id=?",
        (update.effective_user.id,)
    ).fetchone()
    c.close()
    await update.message.reply_text(f"📊 Analyses used: {row[0] if row else 0}")

async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP, parse_mode="Markdown")

async def buttons(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "analyze":
        ctx.user_data["mode"] = "analyze"
        await q.message.reply_text("Send your squad details.")
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

        result = analyze(d)
        c = db()
        c.execute(
            "UPDATE users SET analyses=analyses+1 WHERE id=?",
            (update.effective_user.id,)
        )
        c.commit()
        c.close()

        await update.message.reply_text(result, parse_mode="Markdown")
        ctx.user_data["mode"] = None

    elif mode == "compare":
        s = update.message.text
        await update.message.reply_text(
            f"🆚 *Player comparison placeholder*\n\n{s}\n\n"
            "Next module: connect a verified eFootball player database for real stats.",
            parse_mode="Markdown"
        )
        ctx.user_data["mode"] = None

    else:
        await update.message.reply_text("Use /analyze to start.")

telegram_app = Application.builder().token(TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("analyze", analyze_cmd))
telegram_app.add_handler(CommandHandler("example", example))
telegram_app.add_handler(CommandHandler("compare", compare))
telegram_app.add_handler(CommandHandler("saved", saved))
telegram_app.add_handler(CommandHandler("help", help_cmd))
telegram_app.add_handler(CallbackQueryHandler(buttons))
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
    logger.info("Telegram webhook configured at %s%s", PUBLIC_URL, WEBHOOK_PATH)

    yield

    try:
        await telegram_app.bot.delete_webhook()
    finally:
        await telegram_app.stop()
        await telegram_app.shutdown()

app = FastAPI(
    title="eFootball AI Squad Doctor",
    version="1.0.0",
    lifespan=lifespan,
)

@app.get("/")
async def root():
    return {"status": "ok", "service": "efootball-ai-squad-doctor"}

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
