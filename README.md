# 🃏 Bot Burraco — Guida all'installazione

Bot Telegram per gestire partite di Burraco in modalità **tutti contro tutti**.
Calcola punteggi, tiene lo storico delle mani e una classifica globale.

**Status**: 🚀 Production-ready | **Python**: 3.14+ | **License**: MIT

---

## 🚀 Avvio rapido (Locally)

### Prerequisiti
- **Python 3.14+** — [Scarica qui](https://www.python.org/downloads/)
- **Telegram**Che ha raccolto account (per ottenere token)

### Setup locale (3 minuti)

```bash
# 1. Clona il repo
git clone https://github.com/yourusername/burraco_bot.git
cd burraco_bot

# 2. Copia il template di configurazione
cp .env.example .env

# 3. Installa dipendenze
pip install -r requirements.txt

# 4. Configura credenziali (vedi sotto)
# Edita .env con il tuo TELEGRAM_TOKEN e SUPABASE_KEY

# 5. Avvia il bot
python bot.py
```

---

## 🔐 Configurazione Credenziali

### Ottenere TELEGRAM_TOKEN
1. Apri Telegram e cerca **@BotFather**
2. Scrivi `/newbot` e segui le istruzioni
3. Copia il token fornito

### Ottenere SUPABASE_KEY (Database Cloud)
1. Vai su [supabase.com](https://supabase.com) e crea un progetto gratis
2. Vai a **Settings → API**
3. Copia l'**URL** e la **Service Role Key** (KEY, non ANON)
4. Esegui il `schema.sql` nell'editor SQL di Supabase

### Configurare il file `.env`
```env
# .env (não comitir este arquivo!)
TELEGRAM_TOKEN=123456:ABC-DEF...
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=sb_secret_xxxxx
TARGET_SCORE=2000  # Punteggio default 
```

---

## 🐳 Deployment con Docker

### Opzione 1: Docker Compose (Local Testing)
```bash
# Build e avvia il container
make docker-run

# Visualizza i logs
make docker-logs

# Ferma il container
make docker-stop
```

### Opzione 2: Deploy su Cloud (Render, Railway, Heroku)

#### 🎁 Su **Render** (Gratuito):
1. Push il codice a GitHub (con credenziali nel `.env` locale, `.env` ignorato in git)
2. Vai a [render.com](https://render.com)
3. Crea un nuovo **Web Service**:
   - **Repository**: Collega il tuo GitHub
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `python bot.py`
   - **Environment variables**: Carica `TELEGRAM_TOKEN`, `SUPABASE_URL`, `SUPABASE_KEY` dal Render dashboard
4. Deploy — il bot verrà eseguito sempre

---

## 🛠️ Development

### Installa dipendenze di dev
```bash
make install-dev
```

### Esegui i test
```bash
make test
```

### Lint/Format
```bash
make lint
make format
```

### Comandi disponibili
```bash
make help  # Mostra tutti i comandi
```

---

## 🎮 Comandi del Bot

| Comando | Chi può usarlo | Descrizione |
|---|---|---|
| `/start` | Tutti | Registrazione e lista comandi |
| `/nuovapartita [punti]` | Tutti | Crea una partita (default 2000 pt) |
| `/unisciti` | Tutti | Entra nella partita in attesa |
| `/inizia` | Creatore | Avvia la partita (min 2 giocatori) |
| `/mano` | Tutti | Registra i punteggi di una mano |
| `/punteggi` | Tutti | Mostra il tabellone attuale |
| `/storico` | Tutti | Ultime 20 mani giocate |
| `/annullamano` | Tutti | Annulla l'ultima mano registrata |
| `/pausa` | Creatore | Metti la partita in pausa |
| `/riprendi` | Creatore | Riprendi una partita in pausa |
| `/classifica` | Tutti | Classifica globale 🏆 |
| `/finegioco` | Creatore | Termina partita, incorona vincitore |

---

## 🔧 Troubleshooting

### "Variabili d'ambiente mancanti"
```bash
# Verifica che .env esista e contenga:
cat .env
# Dovrebbe avere: TELEGRAM_TOKEN, SUPABASE_URL, SUPABASE_KEY

# Se no:
cp .env.example .env
# Edita .env con i valori reali
```

### "Errore di connessione a Supabase"
- Verifica l'URL e la KEY in `.env`
- Controlla che il progetto Supabase sia attivo
- Esegui `schema.sql` nella dashboard di Supabase (Settings → SQL Editor)

### "Bot non risponde a /start"
- Verifica che il TELEGRAM_TOKEN sia corretto
- Il bot deve essere in modo "Private" (non "Inline" o "Group")
- Riavvia il bot: `make run`

###"Permission denied" su Render
- Assicurati che il file `.env` sia in `.gitignore` (no credenziali in git!)
- Leggi le Environment Variables nel Render dashboard, non dal repo

---

## 📋 Struttura del Progetto

```
burraco_bot/
├── bot.py                  # Handler Telegram principali
├── database.py             # Client Supabase async
├── schema.sql              # Schema database (run su Supabase)
├── Dockerfile              # Container per cloud deployment
├── requirements.txt        # Dipendenze produzione
├── requirements-dev.txt    # Dipendenze dev/test
├── Makefile                # Comandi automatizzati
├── .env.example            # Template configurazione
├── .gitignore              # Esclude .env, cache, etc
├── README.md               # Questo file
└── tests/                  # Unit tests
    ├── test_database.py
    └── test_game_logic.py
```

---

## 🚀 Roadmap (Post-Launch)

- [ ] Multi-language support (en, es, fr, ...)
- [ ] Admin dashboard (web UI per stats)
- [ ] Caching Redis (classifica live)
- [ ] Sentry monitoring (error tracking)
- [ ] API GraphQL (integrazioni terze)
- [ ] Mobile-friendly web interface

---

## 📝 Licenza

MIT License — Usa liberamente nel tuo progetto!

---

## 👥 Contributi

Segnalazioni di bug e feature requests? Apri una [issue su GitHub](https://github.com/yourusername/burraco_bot/issues)!

---

## 🃏 Come funziona il comando /mano

Al termine di ogni mano, usa `/mano`. Il bot chiederà a turno il punteggio finale di ogni giocatore (un numero intero, può essere negativo).
Il totale viene aggiornato subito automaticamente.

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
