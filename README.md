# 🃏 Bot Burraco — Guida all'installazione

Bot Telegram per gestire partite di Burraco in modalità **tutti contro tutti**.
Calcola punteggi, tiene lo storico delle mani e una classifica globale.

---

## ⚡ Setup rapido (15 minuti)

### 1. Crea il bot su Telegram
1. Apri Telegram e cerca **@BotFather**
2. Scrivi `/newbot` e segui le istruzioni
3. Copia il **token** che ti viene dato (es. `123456:ABC-DEF...`)

---

### 2. Crea il database su Supabase (gratis)
1. Vai su [supabase.com](https://supabase.com) → **Start for free**
2. Crea un nuovo progetto (nome a piacere, scegli la regione **Frankfurt** per latenza minore)
3. Vai su **SQL Editor** → **New query**
4. Incolla tutto il contenuto di `schema.sql` e clicca **Run**
5. Vai su **Project Settings → API** e copia:
   - **Project URL** (es. `https://xxxx.supabase.co`)
   - **anon/public key**

---

### 3. Deploy su Railway (gratis, sempre online)
1. Vai su [railway.app](https://railway.app) → accedi con GitHub
2. **New Project → Deploy from GitHub repo**  
   (se non hai ancora il repo: crea un repo su GitHub e carica questi file)
3. Nelle impostazioni del progetto vai su **Variables** e aggiungi:
   ```
   TELEGRAM_TOKEN = <il tuo token da BotFather>
   SUPABASE_URL   = <la tua URL da Supabase>
   SUPABASE_KEY   = <il tuo anon key da Supabase>
   TARGET_SCORE   = 2000
   ```
4. Railway farà il deploy automaticamente. Il bot sarà online 24/7!

---

## 🎮 Come si usa nel gruppo

| Comando | Chi può usarlo | Descrizione |
|---|---|---|
| `/start` | Tutti | Registrazione e lista comandi |
| `/nuovapartita` | Tutti | Crea una nuova partita |
| `/unisciti` | Tutti | Entra nella partita in attesa |
| `/inizia` | Chi ha creato la partita | Avvia la partita |
| `/mano` | Tutti | Registra i punteggi di una mano |
| `/punteggi` | Tutti | Mostra il tabellone attuale |
| `/classifica` | Tutti | Classifica globale (tutte le partite) |
| `/finegioco` | Chi ha creato la partita | Termina la partita |
| `/annulla` | Tutti | Annulla l'inserimento di una mano |

---

## 🃏 Come funziona /mano

Al termine di ogni mano, usa `/mano`. Il bot chiederà a turno il punteggio finale per ogni giocatore (un numero intero, può essere negativo). Il totale viene aggiornato subito.

Esempio:
```
Bot: 🃏 Mano #3 — 1/3   👤 Mario — punteggio della mano?
Tu:  350
Bot: ✅ Mario: +350 pt → totale 980 pt
Bot: 🃏 Mano #3 — 2/3   👤 Luigi — punteggio della mano?
Tu:  -50
Bot: ✅ Luigi: -50 pt → totale 420 pt
...
```

---

## 🛠️ Sviluppo locale (opzionale)

```bash
# Clona il repo / copia i file in una cartella
cd burraco-bot

# Crea e attiva un ambiente virtuale
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Installa le dipendenze
pip install -r requirements.txt

# Copia il file .env e compila i valori
cp .env.example .env
# Modifica .env con il tuo editor

# Avvia il bot
python bot.py
```

---

## 📁 Struttura del progetto

```
burraco-bot/
├── bot.py          # Logica principale del bot (comandi Telegram)
├── db.py           # Accesso al database Supabase
├── burraco.py      # Calcolo punteggi
├── schema.sql      # Schema database (eseguire una volta su Supabase)
├── requirements.txt
└── .env.example    # Template variabili d'ambiente
```
