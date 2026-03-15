import os
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler,
    MessageHandler, ConversationHandler, filters, ContextTypes
)
from dotenv import load_dotenv
from database import Database

load_dotenv()
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

db = Database()
TARGET_SCORE = int(os.getenv("TARGET_SCORE", 2000))

# ── Stati ConversationHandler ──────────────────────────────────────────────────
MANO_SCORE = 0

# ── Helpers ────────────────────────────────────────────────────────────────────

def mention(player: dict) -> str:
    name = player.get("display_name") or player.get("players", {}).get("display_name", "?")
    return f"*{name}*"

def scoreboard_text(game_players: list, game: dict) -> str:
    lines = [f"📊 *Punteggi — partita #{game['id']}*\n"]
    for i, gp in enumerate(game_players, 1):
        name = gp["players"]["display_name"]
        score = gp["total_score"]
        bar = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else f"{i}."))
        lines.append(f"{bar} {name}: *{score}* pt")
    lines.append(f"\n🎯 Obiettivo: {game['target_score']} pt")
    return "\n".join(lines)

# ── /start ─────────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.register_player(user.id, user.username, user.first_name)
    await update.message.reply_text(
        f"🃏 *Bot Burraco* — Benvenuto, {user.first_name}!\n\n"
        "Comandi principali:\n"
        "• /nuovapartita — crea una partita in questo gruppo\n"
        "• /unisciti — entra nella partita in corso\n"
        "• /inizia — avvia la partita (almeno 2 giocatori)\n"
        "• /mano — registra i punteggi di una mano\n"
        "• /punteggi — mostra il tabellone\n"
        "• /classifica — classifica globale 🏆\n"
        "• /finegioco — termina e inchiona il vincitore\n",
        parse_mode="Markdown",
    )

# ── /nuovapartita ──────────────────────────────────────────────────────────────

async def cmd_nuova_partita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    db.register_player(user.id, user.username, user.first_name)

    existing = db.get_active_game(chat.id)
    if existing:
        await update.message.reply_text(
            "⚠️ C'è già una partita in corso in questo gruppo!\n"
            "Usa /finegioco per terminarla prima di crearne una nuova.",
            parse_mode="Markdown",
        )
        return

    game = db.create_game(chat.id, chat.title, user.id, TARGET_SCORE)
    db.add_player_to_game(game["id"], user.id)
    await update.message.reply_text(
        f"✅ Nuova partita creata da *{user.first_name}*!\n\n"
        f"🎯 Obiettivo: *{TARGET_SCORE}* punti\n\n"
        f"Gli altri giocatori usino /unisciti per entrare.\n"
        f"Quando siete tutti pronti, usa /inizia.",
        parse_mode="Markdown",
    )

# ── /unisciti ──────────────────────────────────────────────────────────────────

async def cmd_unisciti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    db.register_player(user.id, user.username, user.first_name)

    game = db.get_active_game(chat.id)
    if not game:
        await update.message.reply_text("❌ Nessuna partita in corso. Usa /nuovapartita per crearne una.")
        return
    if game["status"] == "active":
        await update.message.reply_text("⚠️ La partita è già iniziata, non puoi più unirti.")
        return

    added = db.add_player_to_game(game["id"], user.id)
    if not added:
        await update.message.reply_text(f"ℹ️ Sei già iscritto alla partita, {user.first_name}!")
        return

    players = db.get_game_players(game["id"])
    names = [p["players"]["display_name"] for p in players]
    await update.message.reply_text(
        f"👋 *{user.first_name}* si è unito/a!\n\n"
        f"Giocatori ({len(names)}): {', '.join(names)}\n"
        f"Usa /inizia quando siete tutti pronti.",
        parse_mode="Markdown",
    )

# ── /inizia ────────────────────────────────────────────────────────────────────

async def cmd_inizia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    game = db.get_active_game(chat.id)
    if not game:
        await update.message.reply_text("❌ Nessuna partita in attesa. Usa /nuovapartita.")
        return
    if game["status"] == "active":
        await update.message.reply_text("⚠️ La partita è già in corso!")
        return
    if game["created_by"] != user.id:
        await update.message.reply_text("❌ Solo chi ha creato la partita può avviarla.")
        return

    players = db.get_game_players(game["id"])
    if len(players) < 2:
        await update.message.reply_text("⚠️ Servono almeno *2 giocatori* per iniziare!", parse_mode="Markdown")
        return

    db.start_game(game["id"])
    names = [p["players"]["display_name"] for p in players]
    await update.message.reply_text(
        f"🎴 *La partita è iniziata!*\n\n"
        f"Giocatori: {', '.join(names)}\n"
        f"🎯 Obiettivo: *{game['target_score']}* punti\n\n"
        f"Al termine di ogni mano usa /mano per registrare i punteggi.",
        parse_mode="Markdown",
    )

# ── /mano (ConversationHandler) ────────────────────────────────────────────────

async def cmd_mano_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    game = db.get_active_game(chat.id)
    if not game or game["status"] != "active":
        await update.message.reply_text("❌ Nessuna partita attiva. Usa /nuovapartita.")
        return ConversationHandler.END

    players = db.get_game_players(game["id"])
    if not players:
        await update.message.reply_text("❌ Nessun giocatore in questa partita.")
        return ConversationHandler.END

    hand = db.create_hand(game["id"])
    context.chat_data["current_hand"] = hand
    context.chat_data["game"] = game
    context.chat_data["players_to_score"] = [p["player_id"] for p in players]
    context.chat_data["players_info"] = {p["player_id"]: p["players"]["display_name"] for p in players}
    context.chat_data["scored"] = {}
    context.chat_data["current_idx"] = 0

    await _ask_score(update.message, context)
    return MANO_SCORE

async def _ask_score(msg, context: ContextTypes.DEFAULT_TYPE):
    idx = context.chat_data["current_idx"]
    players_to_score = context.chat_data["players_to_score"]
    players_info = context.chat_data["players_info"]
    hand = context.chat_data["current_hand"]
    total = len(players_to_score)

    pid = players_to_score[idx]
    name = players_info[pid]
    context.chat_data["current_player_id"] = pid

    await msg.reply_text(
        f"🃏 *Mano #{hand['hand_number']}* — {idx+1}/{total}\n\n"
        f"👤 *{name}* — punteggio della mano? (può essere negativo, es. -50)",
        parse_mode="Markdown",
    )

async def mano_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        punteggio = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("⚠️ Inserisci un numero intero (es. 250 oppure -50).")
        return MANO_SCORE

    pid   = context.chat_data["current_player_id"]
    hand  = context.chat_data["current_hand"]
    game  = context.chat_data["game"]
    name  = context.chat_data["players_info"][pid]

    db.save_hand_score(hand["id"], pid, {"punteggio_mano": punteggio})
    new_total = db.update_player_score(game["id"], pid, punteggio)
    context.chat_data["scored"][pid] = punteggio

    sign = "+" if punteggio >= 0 else ""
    await update.message.reply_text(
        f"✅ *{name}*: {sign}{punteggio} pt → totale *{new_total}* pt",
        parse_mode="Markdown",
    )

    context.chat_data["current_idx"] += 1
    if context.chat_data["current_idx"] < len(context.chat_data["players_to_score"]):
        await _ask_score(update.message, context)
        return MANO_SCORE
    else:
        await _finish_hand(update.message, context)
        return ConversationHandler.END

async def _finish_hand(msg, context: ContextTypes.DEFAULT_TYPE):
    game         = context.chat_data["game"]
    hand         = context.chat_data["current_hand"]
    scored       = context.chat_data["scored"]
    players_info = context.chat_data["players_info"]

    players = db.get_game_players(game["id"])
    lines = [f"🏁 *Riepilogo Mano #{hand['hand_number']}*\n"]
    for p in players:
        pid   = p["player_id"]
        name  = players_info.get(pid, "?")
        delta = scored.get(pid, 0)
        total = p["total_score"]
        sign  = "+" if delta >= 0 else ""
        lines.append(f"• {name}: {sign}{delta} pt → *{total}* pt totali")

    winner = next((p for p in players if p["total_score"] >= game["target_score"]), None)
    text = "\n".join(lines)

    if winner:
        wname = winner["players"]["display_name"]
        text += f"\n\n🏆 *{wname} ha raggiunto {game['target_score']} punti e vince la partita!*"
        db.finish_game(game["id"], winner["player_id"])
        text += "\n\nUsa /nuovapartita per una nuova sfida!"
    else:
        text += "\n\nUsa /mano per la prossima mano."

    await msg.reply_text(text, parse_mode="Markdown")

async def mano_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Inserimento punteggi annullato.")
    return ConversationHandler.END

# ── /punteggi ──────────────────────────────────────────────────────────────────

async def cmd_punteggi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    game = db.get_active_game(chat.id)
    if not game or game["status"] != "active":
        await update.message.reply_text("❌ Nessuna partita attiva.")
        return
    players = db.get_game_players(game["id"])
    if not players:
        await update.message.reply_text("Nessun giocatore nella partita.")
        return
    await update.message.reply_text(scoreboard_text(players, game), parse_mode="Markdown")

# ── /classifica ────────────────────────────────────────────────────────────────

async def cmd_classifica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = db.get_classifica_globale()
    if not rows:
        await update.message.reply_text("Nessuna partita conclusa ancora! 🃏")
        return
    lines = ["🏆 *Classifica Globale*\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, row in enumerate(rows):
        medal = medals[i] if i < 3 else f"{i+1}."
        lines.append(
            f"{medal} *{row['display_name']}*  "
            f"— {row['vittorie']}V / {row['partite_giocate']}P  "
            f"(media {row['media_punti']} pt)"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

# ── /finegioco ─────────────────────────────────────────────────────────────────

async def cmd_finegioco(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    game = db.get_active_game(chat.id)
    if not game:
        await update.message.reply_text("❌ Nessuna partita attiva da terminare.")
        return
    if game["created_by"] != user.id:
        await update.message.reply_text("❌ Solo chi ha creato la partita può terminarla.")
        return

    players = db.get_game_players(game["id"])
    if not players:
        db.finish_game(game["id"], user.id)
        await update.message.reply_text("Partita terminata.")
        return

    winner = max(players, key=lambda p: p["total_score"])
    db.finish_game(game["id"], winner["player_id"])

    lines = [f"🏁 *Partita #{game['id']} terminata!*\n"]
    for i, p in enumerate(players, 1):
        lines.append(f"{i}. {p['players']['display_name']}: *{p['total_score']}* pt")
    lines.append(f"\n🏆 Vincitore: *{winner['players']['display_name']}*!")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    token = os.environ["TELEGRAM_TOKEN"]
    app = Application.builder().token(token).build()

    mano_conv = ConversationHandler(
        entry_points=[CommandHandler("mano", cmd_mano_start)],
        states={
            MANO_SCORE: [MessageHandler(filters.TEXT & ~filters.COMMAND, mano_score)],
        },
        fallbacks=[CommandHandler("annulla", mano_cancel)],
        per_chat=True,
    )

    app.add_handler(CommandHandler("start",         cmd_start))
    app.add_handler(CommandHandler("nuovapartita",  cmd_nuova_partita))
    app.add_handler(CommandHandler("unisciti",      cmd_unisciti))
    app.add_handler(CommandHandler("inizia",        cmd_inizia))
    app.add_handler(mano_conv)
    app.add_handler(CommandHandler("punteggi",      cmd_punteggi))
    app.add_handler(CommandHandler("classifica",    cmd_classifica))
    app.add_handler(CommandHandler("finegioco",     cmd_finegioco))

    logger.info("🃏 Bot Burraco avviato!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
