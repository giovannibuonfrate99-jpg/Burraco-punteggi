# 💾 Backup & Recovery Guide

## Automatic Backups with Supabase

Supabase offre **automatic backups** gratuitamente al libre tier:

### ✅ Come Verificare i Backup su Supabase

1. Accedi a [supabase.com](https://supabase.com)
2. Vai al tuo progetto
3. **Settings → Database → Backups**
4. Vedrai:
   - ✅ Daily automatic backups (ultimi 7 giorni)
   - ✅ On-demand point-in-time restores
   - Storage gratuito per retention automatica

### 🔄 Backup Manuale (Opzionale)

Se vuoi un backup su Google Drive o su cloud storage:

```bash
# 1. Esegui lo script di backup
python backup_supabase.py

# 2. Carica su Google Drive / AWS S3 / etc
# (Vedi istruzioni nel file backup_supabase.py)
```

---

## Recovery Procedure

Se il database è corrotto:

### 1. Restore da Supabase Backup
- **Settings → Database → Backups**
- Seleziona il backup e clicca "Restore"
- ⏱ Restore impiega ~5-10 minuti

### 2. Se il Backup è Perduto
- Backup dei PNG/messaggi: Telegram salva la history automaticamente
- **Worst case**: Ricreare la classifica da <0> (game player totals sono calcolati)
- I dati granulari (hand_scores) potrebbero non essere recuperabili

### 3. Verificare l'Integrità Dopo Restore
```bash
# Connetti e verifica che le tabelle esistano
psql -U postgres -h your-supabase-host -d postgres
SELECT * FROM players LIMIT 1;
SELECT * FROM games LIMIT 1;
```

---

## Strategie di Ridondanza (Post-Launch)

Se scale > 100 utenti:

1. **Dual Backup Strategy**:
   - Supabase auto-backup (primary)
   - Monthly export to AWS S3 (secondary)

2. **Monitoring**:
   - Sentry alerts if database errors spike
   - Weekly health check query

3. **Disaster Recovery Plan**:
   - RTO (Recovery Time Objective): 1 hour
   - RPO (Recovery Point Objective): 1 day

---

## Notes

- ⚠️ **DO NOT** delete `players` table (referential integrity!)
- ⚠️ Supabase free tier: **Max 500 MB** storage (plenty for 50 users)
- ✅ Encryption: All backups are encrypted in transit + at rest
