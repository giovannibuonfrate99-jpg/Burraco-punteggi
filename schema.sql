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
WITH stats AS (
    SELECT
        p.display_name,
        p.telegram_id,
        COUNT(DISTINCT g.id) AS partite_giocate,
        COUNT(DISTINCT g.id) FILTER (
            WHERE g.status = 'finished' AND gp.total_score = (
                SELECT MAX(gp2.total_score) FROM game_players gp2 WHERE gp2.game_id = g.id
            )
        ) AS vittorie,
        COALESCE(AVG(gp.total_score), 0)::INTEGER AS media_punti
    FROM players p
    LEFT JOIN game_players gp ON gp.player_id = p.telegram_id
    LEFT JOIN games g ON g.id = gp.game_id AND g.status = 'finished'
    GROUP BY p.telegram_id, p.display_name
)
SELECT 
    *,
    CASE 
        WHEN partite_giocate > 0 THEN ROUND((vittorie::float / partite_giocate) * 100)::INTEGER 
        ELSE 0 
    END AS win_rate
FROM stats
ORDER BY vittorie DESC, media_punti DESC;

-- Nuova vista per la classifica delle coppie (solo partite a 4)
CREATE OR REPLACE VIEW classifica_coppie AS
WITH pair_matches AS (
    SELECT 
        g.id as game_id,
        p1.display_name as name1,
        p2.display_name as name2,
        (gp1.total_score = (SELECT MAX(gp2.total_score) FROM game_players gp2 WHERE gp2.game_id = g.id)) as won
    FROM games g
    JOIN game_players gp1 ON g.id = gp1.game_id
    JOIN game_players gp2 ON g.id = gp2.game_id AND gp1.player_id < gp2.player_id
    JOIN players p1 ON gp1.player_id = p1.telegram_id
    JOIN players p2 ON gp2.player_id = p2.telegram_id
    WHERE g.status = 'finished'
      AND gp1.total_score = gp2.total_score -- Stesso punteggio = compagni di team
      AND (SELECT COUNT(*) FROM game_players WHERE game_id = g.id) = 4
)
SELECT 
    name1 || ' & ' || name2 as coppia,
    COUNT(*) as giocate,
    COUNT(*) FILTER (WHERE won) as vittorie
FROM pair_matches
GROUP BY name1, name2
ORDER BY vittorie DESC, giocate ASC;

-- ═════════════════════════════════════════════════════════════════════════════
-- RPC: Classifica per singolo gruppo (usata da /classifica senza argomenti)
-- ═════════════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION classifica_gruppo(p_chat_id BIGINT)
RETURNS TABLE(display_name TEXT, telegram_id BIGINT, partite_giocate BIGINT,
              vittorie BIGINT, media_punti INTEGER, win_rate INTEGER)
LANGUAGE sql AS $$
  WITH stats AS (
    SELECT
      p.display_name,
      p.telegram_id,
      COUNT(DISTINCT g.id) AS partite_giocate,
      COUNT(DISTINCT g.id) FILTER (
        WHERE g.status = 'finished' AND gp.total_score = (
          SELECT MAX(gp2.total_score) FROM game_players gp2 WHERE gp2.game_id = g.id
        )
      ) AS vittorie,
      COALESCE(AVG(gp.total_score), 0)::INTEGER AS media_punti
    FROM players p
    LEFT JOIN game_players gp ON gp.player_id = p.telegram_id
    LEFT JOIN games g ON g.id = gp.game_id
                      AND g.status = 'finished'
                      AND g.chat_id = p_chat_id
    GROUP BY p.telegram_id, p.display_name
  )
  SELECT
    display_name, telegram_id, partite_giocate, vittorie, media_punti,
    CASE WHEN partite_giocate > 0
      THEN ROUND((vittorie::float / partite_giocate) * 100)::INTEGER
      ELSE 0
    END AS win_rate
  FROM stats
  WHERE partite_giocate > 0
  ORDER BY vittorie DESC, media_punti DESC;
$$;

CREATE OR REPLACE FUNCTION classifica_coppie_gruppo(p_chat_id BIGINT)
RETURNS TABLE(coppia TEXT, giocate BIGINT, vittorie BIGINT)
LANGUAGE sql AS $$
  WITH pair_matches AS (
    SELECT
      g.id AS game_id,
      p1.display_name AS name1,
      p2.display_name AS name2,
      (gp1.total_score = (SELECT MAX(gp2b.total_score) FROM game_players gp2b WHERE gp2b.game_id = g.id)) AS won
    FROM games g
    JOIN game_players gp1 ON g.id = gp1.game_id
    JOIN game_players gp2 ON g.id = gp2.game_id AND gp1.player_id < gp2.player_id
    JOIN players p1 ON gp1.player_id = p1.telegram_id
    JOIN players p2 ON gp2.player_id = p2.telegram_id
    WHERE g.status = 'finished'
      AND g.chat_id = p_chat_id
      AND gp1.total_score = gp2.total_score
      AND (SELECT COUNT(*) FROM game_players WHERE game_id = g.id) = 4
  )
  SELECT
    name1 || ' & ' || name2 AS coppia,
    COUNT(*) AS giocate,
    COUNT(*) FILTER (WHERE won) AS vittorie
  FROM pair_matches
  GROUP BY name1, name2
  ORDER BY vittorie DESC, giocate ASC;
$$;

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

-- ═════════════════════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY (RLS) - Proteggi le tabelle
-- ═════════════════════════════════════════════════════════════════════════════
-- Il bot usa la Service Role Key che bypassa RLS, ma le policy proteggono
-- l'accesso da chiavi anonime o da utenti non autorizzati

ALTER TABLE IF EXISTS players ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS games ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS game_players ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS hands ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS hand_scores ENABLE ROW LEVEL SECURITY;

-- Players: Permetti tutte le operazioni (il bot usa service role)
CREATE POLICY "players_allow_all" ON players
FOR ALL USING (true) WITH CHECK (true);

-- Games: Permetti tutte le operazioni
CREATE POLICY "games_allow_all" ON games
FOR ALL USING (true) WITH CHECK (true);

-- Game Players: Permetti tutte le operazioni
CREATE POLICY "game_players_allow_all" ON game_players
FOR ALL USING (true) WITH CHECK (true);

-- Hands: Permetti tutte le operazioni
CREATE POLICY "hands_allow_all" ON hands
FOR ALL USING (true) WITH CHECK (true);

-- Hand Scores: Permetti tutte le operazioni
CREATE POLICY "hand_scores_allow_all" ON hand_scores
FOR ALL USING (true) WITH CHECK (true);

-- ═════════════════════════════════════════════════════════════════════════════
-- Sistema ELO
-- ═════════════════════════════════════════════════════════════════════════════

-- Rating ELO corrente per giocatore (aggiornato dopo ogni partita)
CREATE TABLE IF NOT EXISTS player_elo (
    player_id   BIGINT PRIMARY KEY REFERENCES players(telegram_id),
    elo         INTEGER NOT NULL DEFAULT 1000,
    games_played INTEGER NOT NULL DEFAULT 0,
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Storico variazioni ELO partita per partita
CREATE TABLE IF NOT EXISTS elo_history (
    id         SERIAL PRIMARY KEY,
    player_id  BIGINT REFERENCES players(telegram_id),
    game_id    INTEGER REFERENCES games(id) ON DELETE CASCADE,
    elo_before INTEGER NOT NULL,
    elo_after  INTEGER NOT NULL,
    delta      INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Vista classifica ELO globale
CREATE OR REPLACE VIEW classifica_elo AS
SELECT
    p.display_name,
    p.telegram_id,
    pe.elo,
    pe.games_played,
    pe.updated_at
FROM player_elo pe
JOIN players p ON p.telegram_id = pe.player_id
WHERE pe.games_played > 0
ORDER BY pe.elo DESC;

ALTER TABLE IF EXISTS player_elo ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS elo_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "player_elo_allow_all" ON player_elo
FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "elo_history_allow_all" ON elo_history
FOR ALL USING (true) WITH CHECK (true);