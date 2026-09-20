import os, logging, sqlite3, re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN=os.getenv("BOT_TOKEN")
if not TOKEN: raise RuntimeError("Set BOT_TOKEN first")

logging.basicConfig(level=logging.INFO)
DB="bot.db"

def db():
    c=sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY, username TEXT, analyses INTEGER DEFAULT 0)""")
    c.commit(); return c

def touch(u):
    c=db(); c.execute("INSERT OR IGNORE INTO users(id,username) VALUES(?,?)",(u.id,u.username)); c.commit(); c.close()

def parse(t):
    d={}
    for line in t.splitlines():
        if ":" in line:
            k,v=line.split(":",1); d[k.strip().lower()]=v.strip()
    return d

def analyze(d):
    p=" ".join(d.values()).lower()
    score=70
    issues=[]; fixes=[]
    if "anchor man" not in p:
        issues.append("No Anchor Man detected in the supplied squad.")
        fixes.append("Consider an Anchor Man if you need central defensive protection.")
    else: score+=8
    if "build up" not in p:
        issues.append("No Build Up CB detected.")
        fixes.append("Consider a Build Up CB for safer first-phase progression.")
    else: score+=7
    if "goal poacher" not in p and "fox in the box" not in p:
        issues.append("No obvious penalty-box finisher detected.")
        fixes.append("Consider a Goal Poacher/Fox in the Box.")
    else: score+=6
    if "defensive fullback" in p: score+=3
    if "possession" in p and "offensive fullback" not in p:
        fixes.append("One attacking fullback could provide additional width, if midfield cover is adequate.")
    if "quick counter" in p:
        fixes.append("Prioritize pace, direct passing and runners behind the defensive line.")
    score=min(100,score)
    return f"""⚽ *eFOOTBALL AI SQUAD DOCTOR*

📐 Formation: *{d.get('formation','Unknown')}*
🎮 Playstyle: *{d.get('playstyle','Unknown')}*
⭐ Structural score: *{score}/100*

🔴 *Potential issues*
""" + "\n".join("• "+x for x in issues) + """

🔧 *Recommendations*
""" + "\n".join("• "+x for x in fixes) + """

ℹ️ This is a tactical heuristic, not an official Konami rating."""

HELP="""⚽ *eFootball AI Squad Doctor*

Commands:
/start — dashboard
/analyze — analyze a squad
/example — sample input
/compare — compare two players (text mode)
/saved — saved analysis count
/help — help

For the current MVP, send squad details as text after /analyze.
Screenshot recognition, player database and AI vision are designed as the next modules.
"""

async def start(update,ctx):
    touch(update.effective_user)
    kb=[[InlineKeyboardButton("🩺 Analyze Squad",callback_data="analyze"),
         InlineKeyboardButton("📋 Example",callback_data="example")],
        [InlineKeyboardButton("ℹ️ Help",callback_data="help")]]
    await update.message.reply_text(HELP,parse_mode="Markdown",reply_markup=InlineKeyboardMarkup(kb))

async def analyze_cmd(update,ctx):
    touch(update.effective_user); ctx.user_data["mode"]="analyze"
    await update.message.reply_text("Send your squad details. Use /example for the format.")

async def example(update,ctx):
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

async def compare(update,ctx):
    ctx.user_data["mode"]="compare"
    await update.message.reply_text("Send: Player A vs Player B\nExample: Mbappe vs Haaland")

async def saved(update,ctx):
    c=db(); row=c.execute("SELECT analyses FROM users WHERE id=?",(update.effective_user.id,)).fetchone(); c.close()
    await update.message.reply_text(f"📊 Analyses used: {row[0] if row else 0}")

async def buttons(update,ctx):
    q=update.callback_query; await q.answer()
    if q.data=="analyze":
        ctx.user_data["mode"]="analyze"; await q.message.reply_text("Send your squad details.")
    elif q.data=="example": await q.message.reply_text("Use /example.")
    else: await q.message.reply_text(HELP,parse_mode="Markdown")

async def text(update,ctx):
    if not update.message or not update.message.text:return
    mode=ctx.user_data.get("mode")
    if mode=="analyze":
        d=parse(update.message.text)
        if "formation" not in d:
            await update.message.reply_text("Please include Formation: ...\nUse /example.")
            return
        result=analyze(d)
        c=db(); c.execute("UPDATE users SET analyses=analyses+1 WHERE id=?",(update.effective_user.id,)); c.commit(); c.close()
        await update.message.reply_text(result,parse_mode="Markdown")
        ctx.user_data["mode"]=None
    elif mode=="compare":
        s=update.message.text
        await update.message.reply_text(f"🆚 *Player comparison placeholder*\n\n{s}\n\nNext module: connect a verified eFootball player database for real stats.",parse_mode="Markdown")
        ctx.user_data["mode"]=None
    else:
        await update.message.reply_text("Use /analyze to start.")

def main():
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("analyze",analyze_cmd))
    app.add_handler(CommandHandler("example",example))
    app.add_handler(CommandHandler("compare",compare))
    app.add_handler(CommandHandler("saved",saved))
    app.add_handler(CommandHandler("help",lambda u,c:u.message.reply_text(HELP,parse_mode="Markdown")))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,text))
    app.run_polling()

if __name__=="__main__": main()
