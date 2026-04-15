-- Esegui questo script nell'editor SQL di Supabase

-- Giocatori registrati
CREATE TABLE IF NOT EXISTS players (
    telegram_id BIGINT PRIMARY KEY,
    username TEXT,
    display_name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Partite
CREATE TABLE IF NOT EXISTS games (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    chat_title TEXT,
    status TEXT DEFAULT 'waiting',   -- waiting | active | finished
    target_score INTEGER DEFAULT 2000,
    created_by BIGINT REFERENCES players(telegram_id),
    winner_id BIGINT REFERENCES players(telegram_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    finished_at TIMESTAMP WITH TIME ZONE
);

-- Giocatori in una partita
CREATE TABLE IF NOT EXISTS game_players (
    id SERIAL PRIMARY KEY,
    game_id INTEGER REFERENCES games(id) ON DELETE CASCADE,
    player_id BIGINT REFERENCES players(telegram_id),
    total_score INTEGER DEFAULT 0,
    UNIQUE(game_id, player_id)
);

-- Mani giocate
CREATE TABLE IF NOT EXISTS hands (
    id SERIAL PRIMARY KEY,
    game_id INTEGER REFERENCES games(id) ON DELETE CASCADE,
    hand_number INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Punteggi per mano, per giocatore
CREATE TABLE IF NOT EXISTS hand_scores (
    id SERIAL PRIMARY KEY,
    hand_id INTEGER REFERENCES hands(id) ON DELETE CASCADE,
    player_id BIGINT REFERENCES players(telegram_id),
    punteggio_mano INTEGER NOT NULL
);

-- Vista classifica globale (vince chi ha più vittorie)
CREATE OR REPLACE VIEW classifica_globale AS
SELECT
    p.display_name,
    p.telegram_id,
    COUNT(DISTINCT g.id) AS partite_giocate,
    COUNT(DISTINCT g.id) FILTER (WHERE g.winner_id = p.telegram_id) AS vittorie,
    COALESCE(AVG(gp.total_score), 0)::INTEGER AS media_punti
FROM players p
LEFT JOIN game_players gp ON gp.player_id = p.telegram_id
LEFT JOIN games g ON g.id = gp.game_id AND g.status = 'finished'
GROUP BY p.telegram_id, p.display_name
ORDER BY vittorie DESC, media_punti DESC;

-- ═════════════════════════════════════════════════════════════════════════════
-- RPC: Aggiorna punteggio in modo atomico (anti-race-condition)
-- ═════════════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION update_score_atomic(
    p_game_id INTEGER,
    p_player_id BIGINT,
    p_delta INTEGER
) RETURNS INTEGER AS $$
DECLARE
    v_new_score INTEGER;
BEGIN
    -- UPDATE atomico: incrementa il punteggio direttamente nel DB
    UPDATE game_players
    SET total_score = total_score + p_delta
    WHERE game_id = p_game_id AND player_id = p_player_id
    RETURNING total_score INTO v_new_score;
    
    -- Se nessuna riga è stata aggiornata, significa che il giocatore non esiste
    IF v_new_score IS NULL THEN
        RAISE EXCEPTION 'Giocatore non trovato in questa partita';
    END IF;
    
    RETURN v_new_score;
END;
$$ LANGUAGE plpgsql;