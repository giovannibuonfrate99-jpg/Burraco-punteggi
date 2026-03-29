# 🃏 Bot Burraco — Guida all'installazione

Bot Telegram per gestire partite di Burraco in modalità **tutti contro tutti**.
Calcola punteggi, tiene lo storico delle mani e una classifica globale.

---

## 🛠️ Sviluppo e utilizzo sul tuo PC

### 1. Prerequisiti
- **Python**: Assicurati di avere Python installato.
- **PostgreSQL**: Devi installare un server PostgreSQL sul tuo computer.
  - **macOS**: La via più semplice è Postgres.app.
  - **Windows**: Scarica l'installer ufficiale da EDB. Durante l'installazione, ti chiederà di impostare una password per l'utente `postgres`. **Memorizzala!**

### 2. Crea il Database
Dopo aver installato PostgreSQL, apri un terminale e crea il database per il bot:
```bash
# Se il comando 'createdb' non funziona, apri la console SQL di Postgres ed esegui:
# CREATE DATABASE burraco_bot_db;
```

### 3. Configura il Bot
1. **Crea il bot su Telegram**:
   - Apri Telegram e cerca **@BotFather**.
   - Scrivi `/newbot` e segui le istruzioni.
   - Copia il **token** che ti viene dato (es. `123456:ABC-DEF...`).

2. **Prepara il progetto**:
   ```bash
   # Clona il repo o copia i file in una cartella
   cd burraco-bot

   # Crea e attiva un ambiente virtuale
   python -m venv .venv
   source .venv/bin/activate   # Su Windows: .venv\Scripts\activate

   # Installa le dipendenze
   pip install -r requirements.txt
   ```

3. **Configura le variabili d'ambiente**:
   - Crea un file chiamato `.env` nella cartella del progetto (puoi copiare da `.env.example` se esiste).
   - Aggiungi le seguenti righe, sostituendo i valori:
     ```
     TELEGRAM_TOKEN="<il tuo token da BotFather>"
     DATABASE_URL="postgresql://postgres:TUA_PASSWORD_POSTGRES@localhost:5432/burraco_bot_db"
     TARGET_SCORE="2000"
     ```
     > **Nota**: Sostituisci `TUA_PASSWORD_POSTGRES` con la password che hai scelto durante l'installazione di PostgreSQL.

### 4. Avvia il Bot
Una volta configurato tutto, avvia il bot dal tuo terminale:
```bash
python bot.py
```
Al primo avvio, il bot creerà automaticamente le tabelle nel tuo database locale `burraco_bot_db`. Il bot rimarrà in esecuzione finché non chiuderai il terminale.

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

## 🃏 Come funziona il comando /mano

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

## 🚀 Deploy Online (Opzionale)

Se vuoi che il bot sia sempre online, puoi usare un servizio come [Railway](https://railway.app) o [Heroku](https://www.heroku.com/).

Per farlo, avrai bisogno di un database PostgreSQL online. Puoi usare il piano gratuito di [Supabase](https://supabase.com) o [ElephantSQL](https://www.elephantsql.com/) per ottenerne uno.

Una volta ottenuto l'URL del database online, dovrai configurare le variabili d'ambiente nel servizio di hosting che hai scelto (es. Railway) in modo simile a come hai fatto per il file `.env` locale:

```
TELEGRAM_TOKEN = <il tuo token da BotFather>
DATABASE_URL   = <l'URL del tuo database online>
TARGET_SCORE   = 2000
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
