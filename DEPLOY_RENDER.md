# 🚀 Deploy Manual — Burraco Bot on Render

## Panoramica

Questo documento fornisce una guida step-by-step per deployare il bot Burraco su **Render.com** (free tier, no credit card required).

**Target**: Far girare il bot 24/7 su cloud senza costi.

---

## ✅ Pre-requisiti

- ✅ GitHub repository pubblico o privato
- ✅ Account Render.com (free) — [sign up qui](https://render.com)
- ✅ TELEGRAM_TOKEN da @BotFather (già ottenuto)
- ✅ SUPABASE_URL + SUPABASE_KEY (già ottenuti)

---

## 🎯 Passo-by-Passo

### Passo 1: Verifica che il Repo sia Pronto

Assicurati che:
- ✅ `.env` è in `.gitignore` (credenziali non pubbliche)
- ✅ `Dockerfile` esiste nella root
- ✅ `requirements.txt` contiene tutte le dipendenze

```bash
# Verifica locale (opzionale)
ls -la Dockerfile requirements.txt .env.example
```

---

### Passo 2: Connetti GitHub a Render

1. Vai a [render.com](https://render.com)
2. **Click "Sign Up"** → Google/GitHub auth (consigliato GitHub per facilità)
3. **Authorize** Render ad accedere al tuo account GitHub

**Output atteso**: Vieni loggato su Render dashboard

---

### Passo 3: Crea un Nuovo Web Service

1. **Dashboard Render** → Click **"+ New"** (top-right)
2. Seleziona **"Web Service"** (rimane GRATIS!)

```
┌────────────────────────────────────┐
│ New +                              │
├────────────────────────────────────┤
│ Web Service              ← SELEZIONA QUESTO │
│ Static Site                        │
│ Background Worker                  │
│ Cron Job                           │
└────────────────────────────────────┘
```

**Perché Web Service?**
- ✅ Rimane completamente GRATIS (niente costi nascosti)
- ✅ Il bot ora usa **webhook mode** (espone una porta HTTP su 8000)
- ✅ Render può fare health check sulla porta
- ✅ Telegram invia i messaggi al webhook URL del tuo servizio

**Nota tecnica**: Il bot precedentemente usava polling, adesso usa webhook per essere compatible con Render free tier.

3. Click **"Web Service"**

---

### Passo 4: Seleziona il Repository

1. **Connect repository** → Visualizzi la lista dei tuoi repo GitHub
2. Seleziona **`Burraco-punteggi`**
3. **Autorizza** Render se richiesto

```
Connected repository: "giovannibuonfrate99-jpg/Burraco-punteggi"
Branch: "main"
```

Click **"Next"**

---

### Passo 5: Configura il Web Service

Compila il form come segue:

| Campo | Valore | Note |
|-------|--------|------|
| **Name** | `burraco-bot` | Slug per URL (non usato per il bot, ma required) |
| **Environment** | `Docker` | 🔑 **IMPORTANTE**: seleziona Docker (non Python direct) |
| **Region** | `Frankfurt` (o altra EU) | Più vicino = latenza migliore |
| **Branch** | `main` | Deploy automatico su push |

**Scroll down** → Continua con:

| Campo | Valore |
|-------|--------|
| **Auto-deploy** | ✅ **ON** (rideploy automatico su git push) |

---

### Passo 6: Aggiungi Environment Variables

**CRUCIALE**: È qui che metti le credenziali!

Under **"Environment"** → Click **"Add Environment Variable"** (non il file .env)

Aggiungi **3 variabili**:

#### 1️⃣ TELEGRAM_TOKEN
```
Key:   TELEGRAM_TOKEN
Value: <il_tuo_token_da_botfather>
Example: 123456:ABC-DEF1234567890XYZ
```

#### 2️⃣ SUPABASE_URL
```
Key:   SUPABASE_URL
Value: <il_tuo_supabase_url>
Example: https://rsfpxbnjpzlmkqaaxabj.supabase.co
```

#### 3️⃣ SUPABASE_KEY
```
Key:   SUPABASE_KEY
Value: <il_tuo_supabase_secret_key>
Example: sb_secret_KhhOuLjx9pbIHHeBMUbTaw_...
```

**⚠️ ATTENZIONE**: 
- Usa il **Service Role Key** di Supabase, NON la ANON key
- Copia esattamente → no spazi extra

**Screenshot di esempio:**
```
Environment Variables
┌─────────────────────────────────────────────────────────────┐
│ TELEGRAM_TOKEN          │ 123456:ABC-DEF...                 │
│ SUPABASE_URL            │ https://xxxxx.supabase.co         │
│ SUPABASE_KEY            │ sb_secret_KhhOu...                │
│ TARGET_SCORE (optional) │ 2000                              │
└─────────────────────────────────────────────────────────────┘
```

---

### Passo 7: Deploy! 🚀

1. **Scroll to bottom** → Click **"Create Web Service"** (blue button)

**Render inizia a build:**
```
Building Docker image...
Provisioning container...
Running: uvicorn bot:web_app --host 0.0.0.0 --port 8000
✅ Web Service disponibile
🌐 L'app è online su https://burraco-bot.onrender.com
```

**⏳ Tempo atteso**: 2-5 minuti per il primo deploy

**Output atteso nel log** (vedi da Render Dashboard → Logs):
```
> uvicorn bot:web_app ...
✅ Configurazione d'ambiente validata
✅ Connesso a Supabase
🃏 Bot Burraco avviato in webhook mode
   Porta: 8000
   Webhook URL: https://burraco-bot.onrender.com/webhook
Uvicorn running on http://0.0.0.0:8000
```

Il webhook viene configurato automaticamente dal bot all'avvio!

---

### Passo 8: Verifica che il Bot sia Online

1. **Apri Telegram**
2. Cerca il tuo bot oppure apri il link from BotFather
3. Invia `/start`
4. Aspetta la risposta

**Expected response:**
```
🃏 Bot Burraco — Benvenuto, [Nome]!

Comandi principali:
• /nuovapartita — crea partita
...
```

✅ **SUCCESSO!** Il bot è online 24/7 su Render!

---

## 🔄 Auto-Deploy su Every Push

Quando fai un `git push`:

```bash
git add .
git commit -m "bug fix: better error handling"
git push origin main
```

**Render triggera automaticamente** un nuovo build:
1. Pull il codice da GitHub
2. Rebuild Docker image
3. Redeploy il bot
4. Bot rimane online durante il deploy (~60-90 secondi downtime)

**Check logs:**
- Render dashboard → Select `burraco-bot` → Click **"Logs"**
- Visualizzi tutta l'output del bot

---

## 🛠️ Troubleshooting

### "Bot non risponde a /start"

**Soluzione step-by-step:**

1. **Verifica le env vars su Render**:
   - Dashboard → burraco-bot → Settings → Environment
   - Controlla TELEGRAM_TOKEN sia uguale a quello in BotFather

2. **Verifica i Logs**:
   - Click **"Logs"** → Visualizzi tutto l'output
   - Cerca "Configurazione d'ambiente validata" (significa startup ok)
   - Cerca errori Supabase connection

3. **Test locale**:
   ```bash
   # Se vuoi verificare che il codice funziona prima di Render
   cp .env.example .env
   # Edita .env con le credenziali
   python bot.py
   ```

### "Errore di connessione a Supabase"

**Possibili cause + fix:**

| Errore | Causa | Fix |
|--------|-------|-----|
| `SUPABASE_URL=` empty | Env var non configurata | Aggiungi su Render dashboard |
| `SUPABASE_KEY=` wrong | Key non corretta | Verifica secret_key, non anon |
| `Connection timeout` | Firewall Supabase | Supabase deve essere public (è default) |
| `Table doesn't exist` | Schema non eseguito | Esegui `schema.sql` su Supabase dashboard |

### "Service keeps restarting"

**Laikly bottleneck:**
- Memoria insufficiente (Render free tier: 512 MB)
- Infinite loop nel codice (rare)

**Verifica aggiungendo log:**
```bash
# Nel file render.yaml (vedi sotto) aumenta memory
# O controlla logs per leak/crash
```

### ⚠️ "Webhook not working / Invalid token"

**Cosa significa:**
Il webhook di Telegram non riesce a contattare il tuo servizio, di solito causa token errato o URL non raggiungibile.

**Soluzione step-by-step:**

1. **Controlla i logs Render**:
   ```
   Dashboard → burraco-bot → Logs
   ```
   Ricerca (`Cmd+F`) per:
   - ❌ "Invalid token" → TELEGRAM_TOKEN non corretto
   - ❌ "HTTP 401" → credenziali errate
   - ✅ "Webhook URL: https://burraco-bot.onrender.com/webhook" → OK

2. **Verifica il TELEGRAM_TOKEN**:
   - Vai su @BotFather su Telegram
   - `/mybots` → seleziona il tuo bot
   - Copia il token
   - Compara con quello in Render dashboard → Settings → Environment

3. **Se il token è corretto** ma ancora non funziona:
   - Attendi 1-2 minuti dopo il deploy (il webhook ha un delay)
   - Riavvia il servizio: Dashboard → burraco-bot → Settings → "Restart" button
   - Invia di nuovo `/start` al bot su Telegram

4. **Ultimo resort: Rigenera il token**:
   - @BotFather → `/mybots` → tuo bot → `/revoke`
   - `/newtoken` per generare uno nuovo
   - Aggiorna Render env var
   - Redeploy (push qualcosa a GitHub o manuale restart)

---

## 📊 Monitoring

### Visualizza i Logs in Real-Time

```
Render dashboard → burraco-bot → Logs
```

**Seguire i log live:**
```bash
# Se supportato da Render (check docs)
tail -f render-logs.txt
```

### Impostare Alert (Opzionale)

Render free tier non include alert email standard, ma puoi:
- ✅ Controllare logs periodicamente
- ✅ Testare bot con `/start` regolarmente
- ✅ Setup Sentry alerts (opzionale, free tier disponibile)

---

## 🔒 Sicurezza

### ✅ Cosa hai fatto giusto:
- `.env` è in `.gitignore` → credenziali NON in GitHub
- `.env.example` è pubblico → template safe

### ⚠️ Se le credenziali dovessero leakarsi:

**Cambiate SUBITO:**

1. **TELEGRAM_TOKEN**: @BotFather → tuo bot → `/revoke` → genera nuovo token
2. **SUPABASE_KEY**: Supabase dashboard → API → Regenerate key
3. **Render env vars**: Update su dashboard (auto-redeploy)

---

## 📈 Limiti Render Free Tier

| Limite | Valore | Note |
|--------|--------|------|
| Memory | 512 MB | Sufficiente per 50 utenti/50 partite |
| CPU | Shared | No performance SLA |
| Uptime | ~99.9% | Riavvio mensile per maintenance |
| Egress data | Non limitato | OK per Telegram + Supabase |
| Build time | 30 min | Ok (build <5 min) |

**Se superi**: Upgrade zu Render Pro (~$7/mese) o trasferisci altove

---

## 🚀 Prossimi Step (Optional)

### 1. Monitoring Avanzato
```bash
# Aggiungi Sentry (error tracking)
pip install sentry-sdk
# Nel bot.py
import sentry_sdk
sentry_sdk.init("your-sentry-dsn")
```

### 2. Backup Automation
```bash
# Script per backup settimanale Supabase → AWS S3
# Vedi BACKUP_GUIDE.md
```

### 3. Admin Dashboard
```bash
# Web UI semplice (Flask/Django minimal)
# Visualizza stats, user list, recent games
# Opzionale, post-launch
```

---

## ✅ DEPLOYMENT CHECKLIST

Completa questo prima di considerare il deploy "done":

- [ ] `.env` è gitignored
- [ ] `Dockerfile` è nella root `/`
- [ ] `requirements.txt` ha tutte le dipendenze
- [ ] Schema.sql eseguito su Supabase (DB inizializzato)
- [ ] GitHub repo linkato a Render
- [ ] TELEGRAM_TOKEN aggiunto su Render env vars
- [ ] SUPABASE_URL aggiunto su Render env vars
- [ ] SUPABASE_KEY aggiunto su Render env vars
- [ ] Deploy completato (no build errors)
- [ ] `/start` funziona su Telegram
- [ ] Teste una partita completa (nuovapartita → unisciti → inizia → mano → finegioco)

**Se tutto ✅**:
```
🎉 PRODUCTION LIVE! 🎉
Bot è online 24/7 e auto-deploy su ogni push.
```

---

## 📞 Support Links

- **Render docs**: https://render.com/docs
- **Docker docs**: https://docs.docker.com
- **Supabase docs**: https://supabase.com/docs
- **python-telegram-bot**: https://docs.python-telegram-bot.org

---

**Happy deploying! 🚀**
