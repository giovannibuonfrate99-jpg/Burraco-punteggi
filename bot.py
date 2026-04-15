import os
import logging
import sys
from datetime import datetime, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import re

from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    ContextTypes, PicklePersistence, filters,
)
from telegram.error import NetworkError, TimedOut
from dotenv import load_dotenv
from database import Database
from fastapi import FastAPI, Request
import uvicorn

load_dotenv()
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# ENVIRONMENT VALIDATION
# ══════════════════════════════════════════════════════════════════════════════
def _validate_environment():
    """Valida che tutte le variabili d'ambiente critiche siano presenti."""
    required_vars = ["TELEGRAM_TOKEN", "SUPABASE_URL", "SUPABASE_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        logger.error(
            f"❌ Variabili d'ambiente mancanti: {', '.join(missing)}\n"
            f"   Copia .env.example in .env e riempi i valori:\n"
            f"   cp .env.example .env"
        )
        sys.exit(1)
    
    logger.info("✅ Configurazione d'ambiente validata")

_validate_environment()

db = Database()
TARGET_SCORE = int(os.getenv("TARGET_SCORE", 2000))


# ══════════════════════════════════════════════════════════════════════════════
# RATE LIMITING (anti-spam)
# ══════════════════════════════════════════════════════════════════════════════
# Format: {(chat_id, user_id): timestamp_last_mano_command}
_rate_limits = {}
RATE_LIMIT_SECONDS = 5  # Max 1 /mano ogni 5 secondi per utente

def _check_rate_limit(chat_id: int, user_id: int) -> tuple[bool, str]:
    """
    Verifica se l'utente ha superato il rate limit su /mano.
    
    Returns:
        (is_allowed: bool, message: str)
        is_allowed=True se l'utente può procedere
        message=msg di errore se rate-limited
    """
    key = (chat_id, user_id)
    now = datetime.now(timezone.utc).timestamp()
    last_call = _rate_limits.get(key, 0)
    
    if now - last_call < RATE_LIMIT_SECONDS:
        remaining = int(RATE_LIMIT_SECONDS - (now - last_call)) + 1
        return False, f"⏳ Aspetta ancora {remaining}s prima del prossimo /mano"
    
    _rate_limits[key] = now
    return True, ""

def _check_session_timeout(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> bool:
    """
    Verifica se una sessione di input è scaduta (>30 minuti).
    Se sì, la cancella.
    
    Returns:
        True se la sessione è valida, False se è scaduta
    """
    session = _get_session(context, chat_id)
    if not session:
        return True  # Nessuna sessione, non scaduta
    
    # Verifica se la sessione ha un timestamp
    if "created_at" not in session:
        session["created_at"] = datetime.now(timezone.utc).timestamp()
        _set_session(context, chat_id, session)
        return True
    
    now = datetime.now(timezone.utc).timestamp()
    age = now - session["created_at"]
    
    if age > 30 * 60:  # 30 minuti
        _clear_session(context, chat_id)
        return False
    
    return True


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS UI
# ══════════════════════════════════════════════════════════════════════════════

def _progress_bar(score: int, target: int, width: int = 10) -> str:
    """Barra di progresso testuale. Gestisce score negativo e target = 0."""
    if target <= 0:
        return "░" * width
    pct    = max(0.0, min(1.0, score / target))
    filled = round(pct * width)
    return "█" * filled + "░" * (width - filled)

def scoreboard_text(game_players: list, game: dict, title: str | None = None) -> str:
    header = title or f"📊 *Punteggi — partita #{game['id']}*"
    lines  = [header + "\n"]
    target = game["target_score"]
    medals = ["🥇", "🥈", "🥉"]
    for i, gp in enumerate(game_players, 1):
        name  = gp["players"]["display_name"]
        score = gp["total_score"]
        medal = medals[i - 1] if i <= 3 else f"{i}."
        bar   = _progress_bar(score, target)
        pct   = max(0, min(100, round(score / target * 100))) if target > 0 else 0
        lines.append(f"{medal} {name}: *{score}* pt\n   `{bar}` {pct}%")
    lines.append(f"\n🎯 Obiettivo: {target} pt")
    if game.get("status") == "paused":
        lines.append("⏸ _Partita in pausa_")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# VALIDAZIONE DATI
# ══════════════════════════════════════════════════════════════════════════════

async def _validate_player_in_game(chat_id: int, player_id: int, game_id: int) -> bool:
    """Verifica che un giocatore sia effettivamente in una partita."""
    is_in = await db.is_in_game(game_id, player_id)
    if not is_in:
        logger.warning(f"Tentativo di accesso non autorizzato: player {player_id} non in game {game_id}")
        return False
    return True

def _validate_score_input(raw_input: str) -> tuple[bool, int | None, str]:
    """
    Valida l'input del punteggio.
    
    Returns:
        (is_valid: bool, score: int | None, error_message: str)
    """
    raw_input = raw_input.strip()
    
    # Regex: numeri, opzionalmente preceduti da segno + o -
    if not re.fullmatch(r"^[+-]?\d{1,6}$", raw_input):
        return False, None, "⚠️ Inserisci un numero intero (es. 150, -50)"
    
    try:
        score = int(raw_input)
        
        # Validazione limiti ragionevoli
        if abs(score) > 500000:
            return False, None, "⚠️ Punteggio troppo alto! Max ±500.000"
        
        return True, score, ""
        
    except ValueError:
        return False, None, "❌ Errore nel parsing del numero. Riprova."

def _parse_callback_safe(callback_data: str, prefix: str) -> tuple[bool, str]:
    """
    Parse safe di callback_data, con protezione da IndexError.
    
    Args:
        callback_data: es. "mp:score_123"
        prefix: es. "mp:"
    
    Returns:
        (success: bool, action: str)
    """
    try:
        if not callback_data.startswith(prefix):
            return False, ""
        
        action = callback_data[len(prefix):]
        if not action:
            return False, ""
        
        return True, action
    except (IndexError, AttributeError) as e:
        logger.warning(f"Malformed callback data: {callback_data} — {e}")
        return False, ""


# ══════════════════════════════════════════════════════════════════════════════
# SESSIONE MANO  (vive in context.chat_data, persistita su disco)
# ══════════════════════════════════════════════════════════════════════════════

def _get_session(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> dict | None:
    return context.chat_data.get(f"mano_{chat_id}")

def _set_session(context: ContextTypes.DEFAULT_TYPE, chat_id: int, session: dict):
    context.chat_data[f"mano_{chat_id}"] = session

def _clear_session(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    context.chat_data.pop(f"mano_{chat_id}", None)

# Chiave per l'undo in attesa di conferma
def _undo_key(chat_id: int) -> str:
    return f"undo_pending_{chat_id}"


# ══════════════════════════════════════════════════════════════════════════════
# PANNELLO INSERIMENTO PUNTEGGI
# ══════════════════════════════════════════════════════════════════════════════

def _panel_text(session: dict) -> str:
    lines = ["🃏 *Inserimento punteggi mano*\n"]
    for pid in session["players"]:
        name  = session["players_info"][pid]
        score = session["scored"].get(pid)
        if score is None:
            lines.append(f"• {name}: _da inserire_")
        else:
            sign = "+" if score >= 0 else ""
            lines.append(f"• {name}: `{sign}{score}` ✓")
    all_done = all(v is not None for v in session["scored"].values())
    if all_done:
        lines.append("\n✅ Tutti inseriti! Premi *Conferma e salva*.")
    else:
        lines.append("\nPremi ✏️ accanto al tuo nome per inserire il punteggio.")
    return "\n".join(lines)

def _panel_keyboard(session: dict) -> InlineKeyboardMarkup:
    rows = []
    for pid in session["players"]:
        name  = session["players_info"][pid]
        score = session["scored"].get(pid)
        sign  = "+" if (score is not None and score >= 0) else ""
        label = f"✏️ {name}" if score is None else f"✏️ {name}: {sign}{score}"
        rows.append([InlineKeyboardButton(label, callback_data=f"mp:edit:{pid}")])

    all_done = all(v is not None for v in session["scored"].values())
    if all_done:
        rows.append([InlineKeyboardButton("✅ Conferma e salva", callback_data="mp:save_all")])

    rows.append([
        InlineKeyboardButton("📜 Storico",    callback_data="mp:history"),
        InlineKeyboardButton("❌ Annulla mano", callback_data="mp:cancel_all"),
    ])
    return InlineKeyboardMarkup(rows)


# ══════════════════════════════════════════════════════════════════════════════
# INSERIMENTO PUNTEGGIO  (testo libero via tastiera reale)
# ══════════════════════════════════════════════════════════════════════════════

def _input_text(session: dict) -> str:
    pid      = session["editing_pid"]
    name     = session["players_info"][pid]
    existing = session["scored"].get(pid)
    hint     = f"\nValore attuale: `{existing:+}`" if existing is not None else ""
    return (
        f"🃏 *Punteggio per {name}*{hint}\n\n"
        f"✏️ Scrivi il punteggio con la tastiera e invialo\n"
        f"_(numero intero, es. `300` oppure `-150`)_"
    )

def _input_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("↩ Indietro",    callback_data="mp:back_panel"),
        InlineKeyboardButton("❌ Annulla mano", callback_data="mp:cancel_all"),
    ]])


# ══════════════════════════════════════════════════════════════════════════════
# STORICO MANI  (async: fa query al DB)
# ══════════════════════════════════════════════════════════════════════════════

async def _build_history_text(game_id: int, pids: list, players_info: dict) -> str:
    hands = await db.get_hands_history(game_id)
    if not hands:
        return "📜 *Storico mani*\n\n_Nessuna mano registrata ancora._"

    lines   = ["📜 *Storico mani*\n"]
    display = hands

    if len(hands) > 20:
        lines.append(f"_(ultime 20 di {len(hands)} mani)_\n")
        display = hands[-20:]

    for hand in display:
        scores_map = {hs["player_id"]: hs["punteggio_mano"] for hs in hand["hand_scores"]}
        parts = []
        for pid in pids:
            s    = scores_map.get(pid, 0)
            sign = "+" if s >= 0 else ""
            parts.append(f"{players_info[pid][:6]}: {sign}{s}")
        lines.append(f"*#{hand['hand_number']}* — " + " | ".join(parts))

    return "\n".join(lines)

def _history_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("↩ Torna al pannello", callback_data="mp:back_panel")
    ]])


# ══════════════════════════════════════════════════════════════════════════════
# STATISTICHE FINALI
# ══════════════════════════════════════════════════════════════════════════════

async def _build_final_stats(game: dict, players_info: dict) -> str:
    """
    Genera il blocco statistiche da appendere al riepilogo finale.
    Gestisce il caso 'nessuna mano' (partita terminata manualmente prima di giocare).
    """
    hands = await db.get_hands_history(game["id"])
    if not hands:
        return ""

    total_hands   = len(hands)
    player_scores: dict[int, list[int]] = {}
    best_score:  int | None = None
    best_player: str = ""
    worst_score: int | None = None
    worst_player: str = ""

    for hand in hands:
        for hs in hand["hand_scores"]:
            pid   = hs["player_id"]
            score = hs["punteggio_mano"]
            player_scores.setdefault(pid, []).append(score)
            if best_score is None or score > best_score:
                best_score  = score
                best_player = players_info.get(pid, "?")
            if worst_score is None or score < worst_score:
                worst_score  = score
                worst_player = players_info.get(pid, "?")

    # Durata partita
    try:
        created = datetime.fromisoformat(str(game["created_at"]).replace("Z", "+00:00"))
        now     = datetime.now(timezone.utc)
        delta   = now - created
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes = remainder // 60
        duration_str = f"{hours}h {minutes}m" if hours else f"{minutes}m"
    except Exception:
        duration_str = "N/D"

    lines = [
        "\n📈 *Statistiche partita*",
        f"⏱ Durata: *{duration_str}*  |  Mani totali: *{total_hands}*\n",
        "*Media punti per mano:*",
    ]
    for pid, scores in player_scores.items():
        name = players_info.get(pid, "?")
        avg  = sum(scores) / len(scores)
        sign = "+" if avg >= 0 else ""
        lines.append(f"  • {name}: {sign}{avg:.1f} pt/mano")

    if best_score is not None:
        sign = "+" if best_score >= 0 else ""
        lines.append(f"\n🔥 Mano migliore: *{best_player}* ({sign}{best_score} pt)")
    if worst_score is not None:
        lines.append(f"💀 Mano peggiore: *{worst_player}* ({worst_score:+} pt)")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# /start
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.register_player(user.id, user.username, user.first_name)
    await update.message.reply_text(
        f"🃏 *Bot Burraco* — Benvenuto, {user.first_name}!\n\n"
        "Comandi:\n"
        "• /nuovapartita [punti] — crea una partita (es. /nuovapartita 3000)\n"
        "• /unisciti — entra nella partita in corso\n"
        "• /inizia — avvia la partita (almeno 2 giocatori)\n"
        "• /mano — registra i punteggi di una mano\n"
        "• /punteggi — mostra il tabellone\n"
        "• /storico — storico di tutte le mani\n"
        "• /annullamano — annulla l'ultima mano registrata\n"
        "• /pausa — metti la partita in pausa\n"
        "• /riprendi — riprendi una partita in pausa\n"
        "• /classifica — classifica globale 🏆\n"
        "• /finegioco — termina e incorona il vincitore\n",
        parse_mode="Markdown",
    )


# ══════════════════════════════════════════════════════════════════════════════
# /nuovapartita [target_score]
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_nuova_partita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    await db.register_player(user.id, user.username, user.first_name)

    # Parsing argomento opzionale per il target
    target = TARGET_SCORE
    if context.args:
        try:
            target = int(context.args[0])
            if target <= 0 or target > 99_999:
                await update.message.reply_text(
                    "❌ Il punteggio obiettivo deve essere tra 1 e 99.999.\n"
                    "Esempio: /nuovapartita 3000"
                )
                return
        except ValueError:
            await update.message.reply_text(
                "❌ Argomento non valido. Usa un numero intero.\n"
                "Esempio: /nuovapartita 3000"
            )
            return

    existing = await db.get_active_game(chat.id)
    if existing:
        status_label = {"waiting": "in attesa", "active": "in corso", "paused": "in pausa"}.get(
            existing["status"], existing["status"]
        )
        await update.message.reply_text(
            f"⚠️ C'è già una partita *{status_label}* in questo gruppo!\n"
            "Usa /finegioco per terminarla prima di crearne una nuova.",
            parse_mode="Markdown",
        )
        return

    game = await db.create_game(chat.id, chat.title, user.id, target)
    await db.add_player_to_game(game["id"], user.id)
    await update.message.reply_text(
        f"✅ Nuova partita creata da *{user.first_name}*!\n\n"
        f"🎯 Obiettivo: *{target}* punti\n\n"
        f"Gli altri giocatori usino /unisciti per entrare.\n"
        f"Quando siete tutti pronti, usa /inizia.",
        parse_mode="Markdown",
    )


# ══════════════════════════════════════════════════════════════════════════════
# /unisciti
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_unisciti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    await db.register_player(user.id, user.username, user.first_name)

    game = await db.get_active_game(chat.id)
    if not game:
        await update.message.reply_text("❌ Nessuna partita in corso. Usa /nuovapartita per crearne una.")
        return
    if game["status"] == "active":
        await update.message.reply_text("⚠️ La partita è già iniziata, non puoi più unirti.")
        return
    if game["status"] == "paused":
        await update.message.reply_text("⚠️ La partita è in pausa e già iniziata, non puoi unirti.")
        return

    added = await db.add_player_to_game(game["id"], user.id)
    if not added:
        await update.message.reply_text(f"ℹ️ Sei già iscritto alla partita, {user.first_name}!")
        return

    players = await db.get_game_players(game["id"])
    names   = [p["players"]["display_name"] for p in players]
    await update.message.reply_text(
        f"👋 *{user.first_name}* si è unito/a!\n\n"
        f"Giocatori ({len(names)}): {', '.join(names)}\n"
        f"Usa /inizia quando siete tutti pronti.",
        parse_mode="Markdown",
    )


# ══════════════════════════════════════════════════════════════════════════════
# /inizia
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_inizia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    game = await db.get_active_game(chat.id)
    if not game:
        await update.message.reply_text("❌ Nessuna partita in attesa. Usa /nuovapartita.")
        return
    if game["status"] == "active":
        await update.message.reply_text("⚠️ La partita è già in corso!")
        return
    if game["status"] == "paused":
        await update.message.reply_text("⚠️ La partita è in pausa. Usa /riprendi per continuare.")
        return
    if game["created_by"] != user.id:
        await update.message.reply_text("❌ Solo chi ha creato la partita può avviarla.")
        return

    players = await db.get_game_players(game["id"])
    if len(players) < 2:
        await update.message.reply_text(
            "⚠️ Servono almeno *2 giocatori* per iniziare!", parse_mode="Markdown"
        )
        return

    await db.start_game(game["id"])
    names = [p["players"]["display_name"] for p in players]
    await update.message.reply_text(
        f"🎴 *La partita è iniziata!*\n\n"
        f"Giocatori: {', '.join(names)}\n"
        f"🎯 Obiettivo: *{game['target_score']}* punti\n\n"
        f"Al termine di ogni mano usa /mano per registrare i punteggi.",
        parse_mode="Markdown",
    )


# ══════════════════════════════════════════════════════════════════════════════
# /mano
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_mano(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    
    # ── Rate limiting: max 1 /mano ogni 5 secondi
    allowed, error_msg = _check_rate_limit(chat.id, user.id)
    if not allowed:
        await update.message.reply_text(f"⏳ {error_msg}")
        return
    
    # ── Session timeout: cancella sessioni vecchie (>30 min)
    if not _check_session_timeout(context, chat.id):
        await update.message.reply_text(
            "⏰ La sessione di input è scaduta dopo 30 minuti.\n"
            "Usa nuovamente /mano per ricominciare."
        )
        return

    if _get_session(context, chat.id):
        await update.message.reply_text(
            "⚠️ C'è già una mano in corso! Completala o annullala prima."
        )
        return

    game = await db.get_active_game(chat.id)
    if not game:
        await update.message.reply_text("❌ Nessuna partita attiva. Usa /nuovapartita.")
        return
    if game["status"] == "paused":
        await update.message.reply_text("⏸ La partita è in pausa. Usa /riprendi per continuare.")
        return
    if game["status"] != "active":
        await update.message.reply_text("❌ Nessuna partita attiva. Usa /nuovapartita.")
        return

    players = await db.get_game_players(game["id"])
    if not players:
        await update.message.reply_text("❌ Nessun giocatore nella partita.")
        return

    pids    = [p["player_id"] for p in players]
    session = {
        "game":         game,
        "players":      pids,
        "players_info": {p["player_id"]: p["players"]["display_name"] for p in players},
        "scored":       {pid: None for pid in pids},
        "state":        "panel",
        "editing_pid":  None,
        "input":        "",
        "msg_id":       None,
        "created_at":   datetime.now(timezone.utc).timestamp(),  # Per timeout tracking
    }
    _set_session(context, chat.id, session)

    msg = await update.message.reply_text(
        _panel_text(session),
        reply_markup=_panel_keyboard(session),
        parse_mode="Markdown",
    )
    session["msg_id"] = msg.message_id
    _set_session(context, chat.id, session)


# ══════════════════════════════════════════════════════════════════════════════
# CALLBACK TASTIERA MANO  (pattern "^mp:")
# ══════════════════════════════════════════════════════════════════════════════

async def numpad_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    chat_id = query.message.chat_id
    session = _get_session(context, chat_id)

    if not session or query.message.message_id != session.get("msg_id"):
        await query.answer("Questa tastiera non è più attiva.", show_alert=True)
        return

    await query.answer()
    action = query.data[len("mp:"):]
    state  = session.get("state", "panel")

    # ── Azioni disponibili in qualunque stato ─────────────────────────────

    if action == "cancel_all":
        _clear_session(context, chat_id)
        await query.edit_message_text(
            "❌ Mano annullata. I punteggi *non* sono stati salvati.\n"
            "Usa /mano quando siete pronti.",
            parse_mode="Markdown",
        )
        return

    if action == "back_panel":
        # Funziona sia da 'editing' che da 'history'
        session["state"]       = "panel"
        session["editing_pid"] = None
        session["input"]       = ""
        _set_session(context, chat_id, session)
        await query.edit_message_text(
            _panel_text(session),
            reply_markup=_panel_keyboard(session),
            parse_mode="Markdown",
        )
        return

    # ── Stato PANEL ───────────────────────────────────────────────────────

    if state == "panel":

        if action.startswith("edit:"):
            pid = int(action[len("edit:"):])
            session["state"]       = "editing"
            session["editing_pid"] = pid
            session["input"]       = ""
            _set_session(context, chat_id, session)
            await query.edit_message_text(
                _input_text(session),
                reply_markup=_input_keyboard(),
                parse_mode="Markdown",
            )
            return

        if action == "save_all":
            if not all(v is not None for v in session["scored"].values()):
                await query.answer("Non tutti i punteggi sono stati inseriti!", show_alert=True)
                return
            
            recap, success = await _commit_hand_and_recap(session, session["game"])
            _clear_session(context, chat_id)
            
            if not success:
                # Errore nel salvataggio — notifica l'utente chiaramente
                await query.edit_message_text(recap, parse_mode="Markdown")
                logger.error(f"Salvataggio della mano fallito nel gruppo {chat_id}")
            else:
                # Successo — mostra il riepilogo
                await query.edit_message_text(recap, parse_mode="Markdown")
            return

        if action == "history":
            session["state"] = "history"
            _set_session(context, chat_id, session)
            text = await _build_history_text(
                session["game"]["id"],
                session["players"],
                session["players_info"],
            )
            await query.edit_message_text(
                text,
                reply_markup=_history_keyboard(),
                parse_mode="Markdown",
            )
            return

    # ── Stato EDITING ─────────────────────────────────────────────────────
    # L'input viene gestito da text_score_handler (MessageHandler).
    # Qui arrivano solo back_panel e cancel_all, già gestiti sopra.


# ══════════════════════════════════════════════════════════════════════════════
# HANDLER TESTO  — raccoglie il numero digitato dall'utente
# ══════════════════════════════════════════════════════════════════════════════

async def text_score_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Intercetta i messaggi di testo quando una sessione è in stato 'editing'."""
    chat_id = update.effective_chat.id
    session = _get_session(context, chat_id)

    # Ignora se non c'è una sessione attiva in fase di editing
    if not session or session.get("state") != "editing":
        return

    raw = update.message.text.strip()

    # Prova a cancellare il messaggio dell'utente per tenere la chat pulita
    try:
        await update.message.delete()
    except Exception:
        pass

    # Validazione usando la nuova funzione safe
    is_valid, score, error_msg = _validate_score_input(raw)
    
    if not is_valid:
        # Manda un alert temporaneo rispondendo e poi eliminando subito
        err = await context.bot.send_message(
            chat_id=chat_id,
            text=error_msg,
            parse_mode="Markdown",
        )
        context.job_queue.run_once(
            lambda ctx: ctx.bot.delete_message(chat_id, err.message_id),
            when=3,
        )
        return

    pid   = session["editing_pid"]
    session["scored"][pid] = score
    session["state"]       = "panel"
    session["editing_pid"] = None
    session["input"]       = ""
    _set_session(context, chat_id, session)

    # Aggiorna il messaggio del pannello principale
    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=session["msg_id"],
            text=_panel_text(session),
            reply_markup=_panel_keyboard(session),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.warning(f"Impossibile aggiornare il pannello: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# COMMIT MANO + RIEPILOGO
# ══════════════════════════════════════════════════════════════════════════════

async def _commit_hand_and_recap(session: dict, game: dict) -> tuple[str, bool]:
    """
    Salva la mano nel database e genera il riepilogo.
    
    Returns:
        (recap_text: str, success: bool)
        success=True se tutto è andato bene
        success=False + errore in recap_text se qualcosa è fallito
    """
    scored       = session["scored"]
    players_info = session["players_info"]

    try:
        # Salva la mano (RPC atomico garantisce consistency)
        hand    = await db.save_full_hand(game["id"], scored)
        
        # Aggiorna i punteggi (usando RPC atomico in update_player_score)
        for pid, punteggio in scored.items():
            await db.update_player_score(game["id"], pid, punteggio)

        players = await db.get_game_players(game["id"])
        target  = game["target_score"]
        lines   = [f"🏁 *Riepilogo Mano #{hand['hand_number']}*\n"]

        for p in players:
            pid   = p["player_id"]
            name  = players_info.get(pid, "?")
            delta = scored.get(pid, 0)
            total = p["total_score"]
            sign  = "+" if delta >= 0 else ""
            bar   = _progress_bar(total, target)
            pct   = max(0, min(100, round(total / target * 100))) if target > 0 else 0
            lines.append(f"• {name}: {sign}{delta} pt → *{total}* pt\n  `{bar}` {pct}%")

        winner = next((p for p in players if p["total_score"] >= target), None)
        text   = "\n".join(lines)

        if winner:
            wname        = winner["players"]["display_name"]
            winfo        = {p["player_id"]: p["players"]["display_name"] for p in players}
            final_stats  = await _build_final_stats(game, winfo)
            text += (
                f"\n\n🏆 *{wname} ha raggiunto {target} punti e vince la partita!*"
                f"{final_stats}"
                f"\n\nUsa /nuovapartita per una nuova sfida!"
            )
            await db.finish_game(game["id"], winner["player_id"])
        else:
            text += "\n\nUsa /mano per la prossima mano."

        return text, True
        
    except RuntimeError as e:
        error_text = (
            f"❌ *Errore: non è stato possibile salvare la mano.*\n\n"
            f"Dettagli: {str(e)}\n\n"
            f"I dati potrebbero essere incompleti. "
            f"Chiedi a un amministratore di controllare l'ultima mano."
        )
        logger.error(f"Errore critico nel salvataggio della mano: {e}", exc_info=True)
        return error_text, False
        
    except Exception as e:
        error_text = (
            f"❌ *Errore imprevisto durante il salvataggio.*\n\n"
            f"Riprova con /mano.\n"
            f"Se il problema persiste, avvicinati a un amministratore."
        )
        logger.error(f"Errore non gestito nel commit della mano: {e}", exc_info=True)
        return error_text, False


# ══════════════════════════════════════════════════════════════════════════════
# /storico  (comando standalone)
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_storico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    game = await db.get_active_game(chat.id)
    if not game or game["status"] not in ("active", "paused"):
        await update.message.reply_text("❌ Nessuna partita attiva o in pausa.")
        return

    players = await db.get_game_players(game["id"])
    if not players:
        await update.message.reply_text("❌ Nessun giocatore nella partita.")
        return

    pids         = [p["player_id"] for p in players]
    players_info = {p["player_id"]: p["players"]["display_name"] for p in players}
    text         = await _build_history_text(game["id"], pids, players_info)
    await update.message.reply_text(text, parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# /annullamano  — mostra anteprima + conferma
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_annulla_mano(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    # Non si può annullare mentre una sessione di inserimento è aperta
    if _get_session(context, chat.id):
        await update.message.reply_text(
            "⚠️ C'è una mano in corso.\n"
            "Prima completa o annulla la mano attiva con ❌."
        )
        return

    game = await db.get_active_game(chat.id)
    # Permettiamo l'undo anche su partite 'finished' (es. undo dopo vittoria accidentale)
    # ma non su 'waiting' (non ha senso) — in quel caso get_active_game ritorna il gioco
    # in waiting, quindi lo blocchiamo esplicitamente.
    if not game:
        await update.message.reply_text("❌ Nessuna partita attiva.")
        return
    if game["status"] == "waiting":
        await update.message.reply_text("❌ La partita non è ancora iniziata, nessuna mano da annullare.")
        return

    hand, scores = await db.get_last_hand(game["id"])
    if not hand:
        await update.message.reply_text("❌ Nessuna mano da annullare in questa partita.")
        return

    # Recupera i nomi dei giocatori per l'anteprima
    players      = await db.get_game_players(game["id"])
    players_info = {p["player_id"]: p["players"]["display_name"] for p in players}

    lines = [f"⚠️ Vuoi annullare la *Mano #{hand['hand_number']}*?\n"]
    for s in scores:
        name = players_info.get(s["player_id"], "?")
        sign = "+" if s["punteggio_mano"] >= 0 else ""
        lines.append(f"• {name}: {sign}{s['punteggio_mano']} pt (verrà sottratto)")

    if game["status"] == "finished":
        lines.append("\n_Nota: la partita risulta conclusa. L'undo la riporterà in corso._")

    # Salva l'hand_id atteso per evitare race condition (doppio clic, annullo concorrente)
    context.chat_data[_undo_key(chat.id)] = hand["id"]

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Sì, annulla mano", callback_data="undo:confirm"),
        InlineKeyboardButton("❌ No",               callback_data="undo:cancel"),
    ]])
    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


# CALLBACK UNDO  (pattern "^undo:")
async def undo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    chat_id = query.message.chat_id
    await query.answer()

    action = query.data[len("undo:"):]

    if action == "cancel":
        context.chat_data.pop(_undo_key(chat_id), None)
        await query.edit_message_text("↩ Annullamento annullato. La mano rimane.")
        return

    if action == "confirm":
        expected_hand_id = context.chat_data.pop(_undo_key(chat_id), None)
        if expected_hand_id is None:
            # La richiesta è scaduta (ad es. il bot è stato riavviato nel mezzo)
            await query.edit_message_text(
                "❌ Richiesta scaduta. Riprova con /annullamano."
            )
            return

        game = await db.get_active_game(chat_id)
        # Recuperiamo anche partite 'finished' (undo può riattivare una partita conclusa)
        if not game:
            # Cerca tra le partite finished del gruppo
            await query.edit_message_text("❌ Nessuna partita trovata. Riprova con /annullamano.")
            return

        success = await db.undo_last_hand(game["id"], expected_hand_id)
        if not success:
            await query.edit_message_text(
                "⚠️ La situazione è cambiata (mano già annullata o nuova mano aggiunta).\n"
                "Riprova con /annullamano."
            )
            return

        # Mostra il tabellone aggiornato
        players = await db.get_game_players(game["id"])
        # Rilegge il gioco per avere lo status aggiornato (potrebbe essere tornato 'active')
        game = await db.get_active_game(chat_id)
        text = "✅ *Ultima mano annullata!*\n\n"
        if players and game:
            text += scoreboard_text(players, game)
        await query.edit_message_text(text, parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# /pausa  e  /riprendi
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_pausa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    game = await db.get_active_game(chat.id)
    if not game:
        await update.message.reply_text("❌ Nessuna partita attiva.")
        return
    if game["status"] == "waiting":
        await update.message.reply_text("⚠️ La partita non è ancora iniziata.")
        return
    if game["status"] == "paused":
        await update.message.reply_text("⏸ La partita è già in pausa. Usa /riprendi per continuare.")
        return
    if game["created_by"] != user.id:
        await update.message.reply_text("❌ Solo chi ha creato la partita può metterla in pausa.")
        return

    # Blocca se c'è una sessione di inserimento aperta
    if _get_session(context, chat.id):
        await update.message.reply_text(
            "⚠️ C'è una mano in corso.\n"
            "Completa o annulla la mano attiva prima di mettere in pausa."
        )
        return

    await db.pause_game(game["id"])
    await update.message.reply_text(
        "⏸ *Partita messa in pausa.*\n\n"
        "I punteggi sono al sicuro. Usa /riprendi quando siete pronti.",
        parse_mode="Markdown",
    )


async def cmd_riprendi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    game = await db.get_active_game(chat.id)
    if not game:
        await update.message.reply_text("❌ Nessuna partita trovata.")
        return
    if game["status"] != "paused":
        status_label = {"waiting": "in attesa", "active": "già in corso"}.get(
            game["status"], game["status"]
        )
        await update.message.reply_text(f"⚠️ La partita è {status_label}, non in pausa.")
        return
    if game["created_by"] != user.id:
        await update.message.reply_text("❌ Solo chi ha creato la partita può riprenderla.")
        return

    await db.resume_game(game["id"])
    players  = await db.get_game_players(game["id"])
    # Aggiorna lo status nel dict locale per scoreboard_text
    game_resumed = {**game, "status": "active"}
    text = "▶️ *Partita ripresa!*\n\n" + scoreboard_text(players, game_resumed)
    await update.message.reply_text(text, parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# /punteggi
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_punteggi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    game = await db.get_active_game(chat.id)
    if not game or game["status"] not in ("active", "paused"):
        await update.message.reply_text("❌ Nessuna partita attiva.")
        return
    players = await db.get_game_players(game["id"])
    if not players:
        await update.message.reply_text("Nessun giocatore nella partita.")
        return
    await update.message.reply_text(scoreboard_text(players, game), parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# /classifica
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_classifica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = await db.get_classifica_globale()
    if not rows:
        await update.message.reply_text("Nessuna partita conclusa ancora! 🃏")
        return
    lines  = ["🏆 *Classifica Globale*\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, row in enumerate(rows):
        medal = medals[i] if i < 3 else f"{i+1}."
        lines.append(
            f"{medal} *{row['display_name']}*  "
            f"— {row['vittorie']}V / {row['partite_giocate']}P  "
            f"(media {row['media_punti']} pt)"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# /finegioco
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_finegioco(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    game = await db.get_active_game(chat.id)
    if not game:
        await update.message.reply_text("❌ Nessuna partita attiva da terminare.")
        return
    if game["created_by"] != user.id:
        await update.message.reply_text("❌ Solo chi ha creato la partita può terminarla.")
        return

    _clear_session(context, chat.id)
    context.chat_data.pop(_undo_key(chat.id), None)  # pulisce eventuale undo pending

    players = await db.get_game_players(game["id"])
    if not players:
        await db.finish_game(game["id"], user.id)
        await update.message.reply_text("Partita terminata.")
        return

    winner       = max(players, key=lambda p: p["total_score"])
    players_info = {p["player_id"]: p["players"]["display_name"] for p in players}
    await db.finish_game(game["id"], winner["player_id"])

    lines = [f"🏁 *Partita #{game['id']} terminata!*\n"]
    for i, p in enumerate(players, 1):
        name  = p["players"]["display_name"]
        score = p["total_score"]
        bar   = _progress_bar(score, game["target_score"])
        lines.append(f"{i}. {name}: *{score}* pt  `{bar}`")
    lines.append(f"\n🏆 Vincitore: *{winner['players']['display_name']}*!")

    final_stats = await _build_final_stats(game, players_info)
    text = "\n".join(lines) + final_stats + "\n\nUsa /nuovapartita per una nuova sfida!"
    await update.message.reply_text(text, parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# ERROR HANDLER
# ══════════════════════════════════════════════════════════════════════════════

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    if isinstance(context.error, (NetworkError, TimedOut)):
        logger.warning(f"Errore di rete transitorio (ignorato): {context.error}")
        return
    logger.error("Eccezione non gestita:", exc_info=context.error)


# ══════════════════════════════════════════════════════════════════════════════
# POST-INIT  (connessione Supabase prima del polling)
# ══════════════════════════════════════════════════════════════════════════════

async def post_init(application: Application) -> None:
    await db.connect()
    logger.info("Database Supabase inizializzato.")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    token = os.environ["TELEGRAM_TOKEN"]
    port = int(os.getenv("PORT", 8000))
    base_url = os.getenv("BASE_URL", f"http://localhost:{port}")

    persistence = PicklePersistence(filepath="burraco_bot_data.pkl")

    tg_app = (
        Application.builder()
        .token(token)
        .persistence(persistence)
        .post_init(post_init)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(15)
        .pool_timeout(30)
        .build()
    )

    tg_app.add_handler(CommandHandler("start",        cmd_start))
    tg_app.add_handler(CommandHandler("nuovapartita", cmd_nuova_partita))
    tg_app.add_handler(CommandHandler("unisciti",     cmd_unisciti))
    tg_app.add_handler(CommandHandler("inizia",       cmd_inizia))
    tg_app.add_handler(CommandHandler("mano",         cmd_mano))
    tg_app.add_handler(CommandHandler("punteggi",     cmd_punteggi))
    tg_app.add_handler(CommandHandler("storico",      cmd_storico))
    tg_app.add_handler(CommandHandler("annullamano",  cmd_annulla_mano))
    tg_app.add_handler(CommandHandler("pausa",        cmd_pausa))
    tg_app.add_handler(CommandHandler("riprendi",     cmd_riprendi))
    tg_app.add_handler(CommandHandler("classifica",   cmd_classifica))
    tg_app.add_handler(CommandHandler("finegioco",    cmd_finegioco))
    tg_app.add_handler(CallbackQueryHandler(numpad_callback, pattern="^mp:"))
    tg_app.add_handler(CallbackQueryHandler(undo_callback,   pattern="^undo:"))
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_score_handler))
    tg_app.add_error_handler(error_handler)

    # ══════════════════════════════════════════════════════════════════════════════
    # WEBHOOK MODE - FastAPI server
    # ══════════════════════════════════════════════════════════════════════════════
    web_app = FastAPI(title="Burraco Bot Webhook")

    @web_app.post("/webhook")
    async def webhook(request: Request):
        """Riceve gli aggiornamenti da Telegram via webhook."""
        data = await request.json()
        update = Update.de_json(data, tg_app.bot)
        await tg_app.process_update(update)
        return {"ok": True}

    @web_app.get("/health")
    async def health():
        """Health check per Render."""
        return {"status": "ok", "bot": "running"}

    logger.info(f"🃏 Bot Burraco avviato in webhook mode")
    logger.info(f"   Porta: {port}")
    logger.info(f"   Webhook URL: {base_url}/webhook (sarà configurato automaticamente)")
    
    # Avvia il server avec uvicorn
    uvicorn.run(web_app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()