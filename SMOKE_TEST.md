# 🧪 Smoke Test Checklist

Esegui manualmente questi test PRIMA di lanciare su Render.
Costo stimato: 30-45 minuti.

---

## Setup Pre-Test

- [ ] `.env` configurato con credenziali TELEGRAM_TOKEN, SUPABASE_URL, SUPABASE_KEY
- [ ] `schema.sql` eseguito su Supabase (DB inizializzato)
- [ ] Bot avviato: `python bot.py` → stampa "✅ Configurazione d'ambiente validata e Bot Burraco avviato!"
- [ ] Aggiungi il bot a un gruppo Telegram di test

---

## Test Fase 1: Registrazione e Comandi Base

| Test | Comando | Expected | Status |
|------|---------|----------|--------|
| 1.1 | /start | Mostra "🃏 Bot Burraco — Benvenuto, [Nome]!" + lista comandi | ☐ |
| 1.2 | /help | (Se implementato) Mostra help esteso | ☐ |

---

## Test Fase 2: Creazione Partita

| Test | Comando | Expected | Status |
|------|---------|----------|--------|
| 2.1 | /nuovapartita | Crea partita con score default 2000 | ☐ |
| 2.2 | /nuovapartita 3000 | Crea partita con score 3000 | ☐ |
| 2.3 | /nuovapartita 99999 | Crea partita con score massimo (edge case) | ☐ |
| 2.4 | /nuovapartita 100000 | ❌ "Punteggio non valido" | ☐ |
| 2.5 | /nuovapartita abc | ❌ "Argomento non valido" | ☐ |
| 2.6 | /nuovapartita (due volte) | ❌ "C'è già una partita in attesa" | ☐ |

---

## Test Fase 3: Join Partita

| Test | Comando | Expected | Status |
|------|---------|----------|--------|
| 3.1 | (User B) /unisciti | ✅ "User B si è unito! Giocatori (2): User A, User B" | ☐ |
| 3.2 | (User B) /unisciti (2 volte) | ℹ️ "Sei già iscritto" | ☐ |
| 3.3 | (User C) /unisciti | ✅ "User C si è unito! Giocatori (3): ..." | ☐ |

---

## Test Fase 4: Avvio Partita

| Test | Comando | Expected | Status |
|------|---------|----------|--------|
| 4.1 | /inizia (creator, solo 1 giocatore) | ❌ "Servono almeno 2 giocatori" | ☐ |
| 4.2 | (Aggiungi User B) /inizia | ✅ "La partita è iniziata! Giocatori: ..." | ☐ |
| 4.3 | (Non-creator) /inizia | ❌ "Solo creatore può avviare" | ☐ |

---

## Test Fase 5: Inserimento Punteggi (/mano)

| Test | Comando | Expected | Status |
|------|---------|----------|--------|
| 5.1 | /mano | ✅ UI con pannello "Inserimento punteggi mano" + tastiera inline | ☐ |
| 5.2 | (Click button accanto a nome) | ✅ Entra in modalità editing, attende input | ☐ |
| 5.3 | Digita "150" | ✅ Aggiorna pannello, "User: 150 ✓" | ☐ |
| 5.4 | Digita "abc" | ❌ "Inserisci un numero intero" | ☐ |
| 5.5 | Digita "+50" | ✅ Accetta (formato positivo) | ☐ |
| 5.6 | Digita "-30" | ✅ Accetta (formato negativo) | ☐ |
| 5.7 | Digita "9999999" | ❌ "Punteggio troppo alto" | ☐ |
| 5.8 | Completa tutti i punteggi | ✅ Bottone "Conferma e salva" appare | ☐ |
| 5.9 | Click "Conferma e salva" | ✅ "Riepilogo Mano #1" con totali aggiornati + barra progresso | ☐ |

---

## Test Fase 6: Tabellone e Storico

| Test | Comando | Expected | Status |
|------|---------|----------|--------|
| 6.1 | /punteggi | ✅ Mostra tabellone con barre progresso e % completion | ☐ |
| 6.2 | /storico | ✅ Mostra "Storico mani" con ultima mano registrata | ☐ |
| 6.3 | /storico (dopo 20+ mani) | ✅ Mostra "ultime 20 di X mani" | ☐ |

---

## Test Fase 7: Annullamento Mano

| Test | Comando | Expected | Status |
|------|---------|----------|--------|
| 7.1 | /annullamano | ✅ Mostra anteprima ultima mano + button "Conferma undo" | ☐ |
| 7.2 | Click "Conferma undo" | ✅ "Mano annullata" + punteggi ripristinati | ☐ |
| 7.3 | /punteggi (dopo undo) | ✅ Punteggi ridotti di nuovo | ☐ |
| 7.4 | /annullamano (nessuna mano) | ❌ "Nessuna mano da annullare" | ☐ |

---

## Test Fase 8: Pausa/Riprendi

| Test | Comando | Expected | Status |
|------|---------|----------|--------|
| 8.1 | /pausa | ⏸ "Partita in pausa" | ☐ |
| 8.2 | /riprendi | ▶️ "Partita ripresa" | ☐ |
| 8.3 | /mano (in pausa) | ❌ "Partita è in pausa" | ☐ |

---

## Test Fase 9: Fine Partita

| Test | Scenario | Expected | Status |
|------|----------|----------|--------|
| 9.1 | User A raggiunge target score | ✅ "User A ha raggiunto 2000 pt e vince!" + stats finali | ☐ |
| 9.2 | /classifica (dopo vittoria) | ✅ Classifica globale aggiornata (vittorie contate) | ☐ |
| 9.3 | /nuovapartita (dopo /finegioco) | ✅ Nuova partita creabile | ☐ |

---

## Test Fase 10: Edge Cases & Error Handling

| Test | Scenario | Expected | Status |
|------|----------|----------|--------|
| 10.1 | Rate limiting: 3x /mano in 2 secondi | ❌ "Aspetta ancora Xs prima del prossimo /mano" | ☐ |
| 10.2 | Session timeout (30+ min idle) | ❌ "La sessione è scaduta" | ☐ |
| 10.3 | Delete user message durante /mano | ✅ Continua normal (no crash) | ☐ |
| 10.4 | Close Telegram app durante /mano | ✅ Sessione mantiene stato (riapri app, prosegui) | ☐ |
| 10.5 | Database offline | ❌ Messaggio errore chiaro (non crash) | ☐ |

---

## Test Fase 11: Concurrent Actions (Race Condition Test)

| Test | Scenario | Expected | Status |
|------|----------|----------|--------|
| 11.1 | User A e User B lanciano /mano simultaneamente | ✅ Entrambi completano correttamente (punteggi non persi) | ☐ |
| 11.2 | verificare punteggi totali corretti | ✅ Total score = sum di tutti gli punteggi (no perdite) | ☐ |
| 11.3 | Undo di una mano durante /mano altro | ✅ No interference (thread-safe) | ☐ |

---

## Test Fase 12: Bot Crash Recovery

| Test | Scenario | Expected | Status |
|------|----------|----------|--------|
| 12.1 | Kill/restart bot durante una mano | ✅ Dati salvati (no perdita) | ☐ |
| 12.2 | Reconnect bot | ✅ Sessioni ripristinate od cancellate correctly | ☐ |

---

## Test Fase 13: Monitoring & Logs

| Test | Cosa verificare | Expected | Status |
|------|-----------------|----------|--------|
| 13.1 | Logs di startup | ✅ "✅ Configurazione d'ambiente validata" | ☐ |
| 13.2 | Logs di mano salvata | ✅ "✅ Mano #1 salvata: 2 punteggi registrati" | ☐ |
| 13.3 | Logs di errore DB | ✅ Errori loggati con stack trace | ☐ |

---

## Post-Test Verification

- [ ] Nessun crash
- [ ] Nessun dato perso
- [ ] Tutti i test checkati ✅
- [ ] performance accettabile (<2s per operazione)
- [ ] Messaggi di feedback chiari

---

## Notes

- **Concurrency test (11.x)**: Richiede due account Telegram reali o test bot paralleli
- **Database offline test (10.5)**: Ferma Supabase dall'API momentaneamente
- **Logs**: Visualizza con `tail -f app.log` esterna Python, che da tutti i log in tempo reale (se log file aggiunto)

---

**RESULT**: ✅ PASS / ❌ FAIL (se tutti i test passano, pronto per production!)
