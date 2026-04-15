"""
Messaggi standard del bot Burraco — consistent con emoji e tono.
"""

# ═══════════════════════════════════════════════════════════════════════════════
# MESSAGGI DI ERRORE
# ═══════════════════════════════════════════════════════════════════════════════

ERROR_NO_ACTIVE_GAME = "❌ Nessuna partita attiva. Usa /nuovapartita per crearne una."
ERROR_GAME_NOT_WAITING = "⚠️ La partita non is in waiting status. Usa /finegioco prima di crearne una nuova."
ERROR_GAME_ALREADY_ACTIVE = "⚠️ La partita è già iniziata, non puoi più unirti."
ERROR_GAME_IN_PAUSE = "⏸ La partita è in pausa. Usa /riprendi per continuare."
ERROR_NOT_AUTHORIZED = "❌ Solo chi ha creato la partita può fare questa azione."
ERROR_NOT_ENOUGH_PLAYERS = "⚠️ Servono almeno 2 giocatori per iniziare!"
ERROR_INVALID_TARGET_SCORE = "❌ Il punteggio obiettivo deve essere tra 1 e 99.999."
ERROR_INVALID_SCORE_FORMAT = "⚠️ Inserisci un numero intero (es. 150, -50)."
ERROR_SCORE_TOO_HIGH = "⚠️ Punteggio troppo alto! Max ±500.000"
ERROR_ALREADY_IN_SESSION = "⚠️ C'è già una mano in corso! Completala o annullala prima."
ERROR_MALFORMED_DATA = "❌ Dati malformati. Riprova con il comando."
ERROR_DB_SAVE = "❌ Errore nel salvataggio. I dati potrebbero essere incompleti. Contatta un admin."
ERROR_RATE_LIMITED = "⏳ Aspetta ancora {remaining}s prima del prossimo /mano"
ERROR_SESSION_TIMEOUT = "⏰ La sessione di input è scaduta dopo 30 minuti. Usa /mano per ricominciare."

# ═══════════════════════════════════════════════════════════════════════════════
# MESSAGGI DI SUCCESSO
# ═══════════════════════════════════════════════════════════════════════════════

SUCCESS_GAME_CREATED = "✅ Nuova partita creata da {creator}!\n\n🎯 Obiettivo: {target} punti\n\nGli altri giocatori usino /unisciti per entrare."
SUCCESS_PLAYER_JOINED = "👋 {player} si è unito/a!\n\nGiocatori ({count}): {names}\nUsa /inizia quando siete pronti."
SUCCESS_PLAYER_ALREADY_JOINED = "ℹ️ Sei già iscritto alla partita, {player}!"
SUCCESS_GAME_STARTED = "🎴 *La partita è iniziata!*\n\nGiocatori: {names}\n🎯 Obiettivo: {target} punti\n\nUsa /mano per registrare i punteggi."
SUCCESS_HAND_SAVED = "✅ Mano #{hand_num} salvata con successo!"
SUCCESS_HAND_UNDONE = "↩️ Mano annullata. Lo stato precedente è stato ripristinato."
SUCCESS_HAND_CANCELLED = "❌ Mano annullata. I punteggi *non* sono stati salvati."
SUCCESS_GAME_PAUSED = "⏸ Partita messa in pausa."
SUCCESS_GAME_RESUMED = "▶️ Partita ripresa!"
SUCCESS_WINNER = "🏆 *{winner} ha raggiunto {target} punti e vince la partita!*"

# ═══════════════════════════════════════════════════════════════════════════════
# MESSAGGI INFORMATIVI
# ═══════════════════════════════════════════════════════════════════════════════

INFO_SCOREBOARD_TITLE = "📊 *Punteggi — partita #{game_id}*"
INFO_HISTORY_TITLE = "📜 *Storico mani*"
INFO_NO_HISTORY = "📜 *Storico mani*\n\n_Nessuna mano registrata ancora._"
INFO_FINAL_STATS = "\n📈 *Statistiche partita*"
INFO_NEXT_HAND = "\n\nUsa /mano per la prossima mano."

# ═══════════════════════════════════════════════════════════════════════════════
# MESSAGGI /START
# ═══════════════════════════════════════════════════════════════════════════════

START_WELCOME = """🃏 *Bot Burraco* — Benvenuto, {user}!

Comandi principali:
• /nuovapartita [punti] — crea una partita (es. /nuovapartita 3000)
• /unisciti — entra nella partita in corso
• /inizia — avvia la partita (almeno 2 giocatori)
• /mano — registra i punteggi di una mano
• /punteggi — mostra il tabellone
• /storico — storico delle ultime 20 mani
• /annullamano — annulla l'ultima mano
• /pausa / /riprendi — pausa la partita
• /classifica — classifica globale 🏆
• /finegioco — termina la partita

Usa /help per dettagli completi!"""
