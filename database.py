import os
import logging
from datetime import datetime, timezone
from supabase import acreate_client, AsyncClient
from dotenv import load_dotenv

load_dotenv()


class Database:

    async def get_player_by_username_or_name(self, username_or_name: str):
        # Cerca usando ilike per rendere la ricerca case-insensitive
        res = await (
            self.client.table("players")
            .select("*")
            .or_(f"username.ilike.{username_or_name},display_name.ilike.{username_or_name}")
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None
    
    def __init__(self):
        self.url: str = os.environ.get("SUPABASE_URL", "")
        self.key: str = os.environ.get("SUPABASE_KEY", "")
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL e SUPABASE_KEY devono essere impostati nel .env")
        self.client: AsyncClient | None = None
        self.logger = logging.getLogger("Database")

    async def connect(self):
        """Crea il client asincrono Supabase. Va chiamato una volta all'avvio."""
        self.client = await acreate_client(self.url, self.key)
        self.logger.info("Connesso a Supabase ✅")

    # ── Giocatori ──────────────────────────────────────────────────────────

    async def register_player(self, telegram_id: int, username: str | None, display_name: str):
        await (
            self.client.table("players")
            .upsert(
                {"telegram_id": telegram_id, "username": username, "display_name": display_name},
                on_conflict="telegram_id",
            )
            .execute()
        )

    async def get_player(self, telegram_id: int):
        res = await (
            self.client.table("players")
            .select("*")
            .eq("telegram_id", telegram_id)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    # ── Partite ────────────────────────────────────────────────────────────

    async def create_game(self, chat_id: int, chat_title: str, created_by: int, target_score: int = 2000):
        self.logger.info(f"[create_game] chat_id={chat_id}")
        res = await (
            self.client.table("games")
            .insert({
                "chat_id":      chat_id,
                "chat_title":   chat_title or "Gruppo",
                "created_by":   created_by,
                "target_score": target_score,
                "status":       "waiting",
            })
            .execute()
        )
        return res.data[0] if res.data else None

    async def get_active_game(self, chat_id: int):
        """
        Restituisce la partita corrente del gruppo, incluse quelle in pausa.
        Gli stati 'waiting', 'active' e 'paused' sono tutti considerati "attivi"
        nel senso che bloccano la creazione di una nuova partita.
        """
        res = await (
            self.client.table("games")
            .select("*")
            .eq("chat_id", chat_id)
            .in_("status", ["waiting", "active", "paused"])
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    async def start_game(self, game_id: int):
        await (
            self.client.table("games")
            .update({"status": "active"})
            .eq("id", game_id)
            .execute()
        )

    async def cleanup_bad_games(self):
        """
        Identifica e cancella le partite 'finished' che non hanno alcuna mano registrata.
        Queste sono solitamente partite chiuse per errore o prematuramente.
        """
        try:
            # Recuperiamo gli ID di tutte le partite con stato 'finished'
            res = await self.client.table("games").select("id").eq("status", "finished").execute()
            if not res or not res.data:
                return

            game_ids = [g["id"] for g in res.data]
            
            # Troviamo quali di questi ID hanno almeno una mano registrata nella tabella hands
            hands_res = await self.client.table("hands").select("game_id").in_("game_id", game_ids).execute()
            games_with_hands = {h["game_id"] for h in hands_res.data} if (hands_res and hands_res.data) else set()
            
            # Gli ID che sono nello stato 'finished' ma non hanno mani sono "bad games"
            bad_game_ids = [gid for gid in game_ids if gid not in games_with_hands]
            
            if bad_game_ids:
                await self.client.table("games").delete().in_("id", bad_game_ids).execute()
                self.logger.info(f"🧹 Pulizia automatica: rimosse {len(bad_game_ids)} partite 'bad' (senza mani).")
        except Exception as e:
            self.logger.error(f"Errore durante la pulizia dei bad games: {e}")

    async def update_game_target_score(self, game_id: int, new_target: int):
        await (
            self.client.table("games")
            .update({"target_score": new_target})
            .eq("id", game_id)
            .execute()
        )

    async def pause_game(self, game_id: int):
        await (
            self.client.table("games")
            .update({"status": "paused"})
            .eq("id", game_id)
            .execute()
        )

    async def resume_game(self, game_id: int):
        await (
            self.client.table("games")
            .update({"status": "active"})
            .eq("id", game_id)
            .execute()
        )

    async def finish_game(self, game_id: int, winner_id: int):
        await (
            self.client.table("games")
            .update({
                "status":      "finished",
                "winner_id":   winner_id,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", game_id)
            .execute()
        )
        # Esegue la pulizia ogni volta che una partita viene conclusa
        await self.cleanup_bad_games()

    async def cancel_game(self, game_id: int):
        """
        Elimina completamente una partita e tutti i dati associati.
        Utile per annullare una sessione senza salvare statistiche.
        """
        try:
            # 1. Otteniamo gli ID delle mani associate per pulire hand_scores
            res_hands = await self.client.table("hands").select("id").eq("game_id", game_id).execute()
            hand_ids = [h["id"] for h in res_hands.data] if res_hands.data else []

            if hand_ids:
                # 2. Elimina i punteggi delle mani
                await self.client.table("hand_scores").delete().in_("hand_id", hand_ids).execute()

            # 3. Elimina le mani
            await self.client.table("hands").delete().eq("game_id", game_id).execute()

            # 4. Elimina i giocatori dalla partita
            await self.client.table("game_players").delete().eq("game_id", game_id).execute()

            # 5. Elimina la partita stessa
            await self.client.table("games").delete().eq("id", game_id).execute()
            
            self.logger.info(f"🗑️ Partita {game_id} eliminata definitivamente.")
            return True
        except Exception as e:
            self.logger.error(f"Errore durante l'annullamento della partita {game_id}: {e}")
            return False

    # ── Giocatori in partita ───────────────────────────────────────────────

    async def add_player_to_game(self, game_id: int, player_id: int) -> bool:
        res = await (
            self.client.table("game_players")
            .upsert(
                {"game_id": game_id, "player_id": player_id},
                on_conflict="game_id,player_id",
                ignore_duplicates=True,
            )
            .execute()
        )
        return bool(res.data)

    async def get_game_players(self, game_id: int):
        res = await (
            self.client.table("game_players")
            .select("*, players(display_name, username)")
            .eq("game_id", game_id)
            .order("total_score", desc=True)
            .execute()
        )
        return res.data or []

    async def is_in_game(self, game_id: int, player_id: int) -> bool:
        res = await (
            self.client.table("game_players")
            .select("player_id")
            .eq("game_id", game_id)
            .eq("player_id", player_id)
            .limit(1)
            .execute()
        )
        return bool(res.data)

    async def update_player_score(self, game_id: int, player_id: int, delta: int) -> int:
        """
        Aggiorna il punteggio di un giocatore IN MODO ATOMICO usando RPC PostgreSQL.
        Questo evita race condition che potrebbero causare perdita di punti con concorrenza.
        
        Args:
            game_id: ID della partita
            player_id: ID del giocatore (telegram_id)
            delta: Differenza da aggiungere (positiva o negativa)
        
        Returns:
            Il nuovo punteggio totale del giocatore
        
        Raises:
            Exception: Se il giocatore non è in questa partita
        """
        try:
            # Usa l'RPC PostgreSQL atomico per UPDATE thread-safe
            result = await self.client.rpc(
                "update_score_atomic",
                {
                    "p_game_id": game_id,
                    "p_player_id": player_id,
                    "p_delta": delta,
                }
            ).execute()
            
            if not result.data:
                raise ValueError(f"Impossibile aggiornare punteggio per player {player_id} in game {game_id}")
            
            return result.data
        except Exception as e:
            self.logger.error(f"Errore in update_player_score: {e}")
            raise

    # ── Mani ──────────────────────────────────────────────────────────────

    async def next_hand_number(self, game_id: int) -> int:
        res = await (
            self.client.table("hands")
            .select("hand_number")
            .eq("game_id", game_id)
            .order("hand_number", desc=True)
            .limit(1)
            .execute()
        )
        return (res.data[0]["hand_number"] + 1) if res.data else 1

    async def save_full_hand(self, game_id: int, scored: dict) -> dict:
        """
        Crea la mano e salva tutti i punteggi in un colpo solo.
        Chiamato SOLO quando tutti i giocatori hanno confermato.
        
        Raises:
            RuntimeError: Se l'operazione fallisce a Supabase
        """
        try:
            hand_number = await self.next_hand_number(game_id)
            hand_res = await (
                self.client.table("hands")
                .insert({"game_id": game_id, "hand_number": hand_number})
                .execute()
            )
            
            if not hand_res.data:
                raise ValueError("Impossibile creare la mano nel database")
            
            hand = hand_res.data[0]
            rows = [
                {"hand_id": hand["id"], "player_id": pid, "punteggio_mano": punteggio}
                for pid, punteggio in scored.items()
            ]
            
            scores_res = await self.client.table("hand_scores").insert(rows).execute()
            if not scores_res.data:
                raise ValueError("Impossibile salvare i punteggi della mano")
            
            self.logger.info(f"✅ Mano #{hand_number} salvata: {len(rows)} punteggi registrati")
            return hand
            
        except Exception as e:
            self.logger.error(f"❌ Errore nel salvataggio della mano: {e}", exc_info=True)
            raise RuntimeError(f"Errore di salvataggio: {str(e)}") from e

    async def get_last_hand(self, game_id: int) -> tuple[dict | None, list]:
        """
        Restituisce (hand, scores) dell'ultima mano, oppure (None, []) se non esiste.
        Usato per mostrare l'anteprima prima di un undo.
        """
        res = await (
            self.client.table("hands")
            .select("*")
            .eq("game_id", game_id)
            .order("hand_number", desc=True)
            .limit(1)
            .execute()
        )
        if not res.data:
            return None, []
        hand = res.data[0]
        scores_res = await (
            self.client.table("hand_scores")
            .select("*")
            .eq("hand_id", hand["id"])
            .execute()
        )
        return hand, scores_res.data or []

    async def undo_last_hand(self, game_id: int, expected_hand_id: int) -> bool:
        """
        Annulla l'ultima mano verificando che sia ancora quella attesa (anti-race-condition).
        - Sottrae i punteggi da game_players
        - Cancella hand_scores e hand
        - Se il gioco era 'finished', lo riporta ad 'active' (rimuove vincitore)
        
        Ritorna True se l'undo è avvenuto, False se la mano non esiste più o errore.
        """
        try:
            hand, scores = await self.get_last_hand(game_id)
            if not hand or hand["id"] != expected_hand_id:
                self.logger.warning(
                    f"Undo fallito: mano non trovata o già annullata (expected_id={expected_hand_id})"
                )
                return False

            # Sottrai i punteggi di questa mano dai totali dei giocatori
            for score_row in scores:
                try:
                    await self.update_player_score(
                        game_id, score_row["player_id"], -score_row["punteggio_mano"]
                    )
                except Exception as e:
                    self.logger.error(f"Errore nel revert dei punteggi per player {score_row['player_id']}: {e}")
                    raise

            # Cancella i punteggi della mano (prima, per FK)
            await (
                self.client.table("hand_scores")
                .delete()
                .eq("hand_id", hand["id"])
                .execute()
            )

            # Cancella la mano
            await (
                self.client.table("hands")
                .delete()
                .eq("id", hand["id"])
                .execute()
            )

            # Se il gioco era già concluso, riportalo ad 'active'
            game_res = await (
                self.client.table("games")
                .select("status")
                .eq("id", game_id)
                .limit(1)
                .execute()
            )
            if game_res.data and game_res.data[0]["status"] == "finished":
                await (
                    self.client.table("games")
                    .update({"status": "active", "winner_id": None, "finished_at": None})
                    .eq("id", game_id)
                    .execute()
                )

            self.logger.info(f"✅ Mano (ID={expected_hand_id}) annullata con successo")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Errore nell'undo della mano: {e}", exc_info=True)
            return False

    async def get_hands_history(self, game_id: int):
        res = await (
            self.client.table("hands")
            .select("*, hand_scores(*, players(display_name))")
            .eq("game_id", game_id)
            .order("hand_number")
            .execute()
        )
        return res.data or []

    # ── Classifica globale ────────────────────────────────────────────────

    async def get_classifica_globale(self):
        res = await self.client.table("classifica_globale").select("*").execute()
        return res.data or []

    # ── Pulizia dati ──────────────────────────────────────────────────────

    async def delete_all_data_except_players(self):
        # Cancella i dati rispettando l'ordine delle FK
        for table in ("hand_scores", "hands", "game_players", "games"):
            await self.client.table(table).delete().neq("id", 0).execute()
 
        # Resetta le sequenze così i nuovi ID ripartono da 1.
        # Richiede la funzione RPC 'reset_sequences' su Supabase (vedi sotto).
        try:
            await self.client.rpc("reset_sequences").execute()
            self.logger.info("Sequenze resettate a 1.")
        except Exception as e:
            self.logger.warning(
                f"Reset sequenze non riuscito (funzione RPC assente?): {e}\n"
                "Crea la funzione su Supabase — vedi istruzioni nel codice."
            )
 
        self.logger.info("Tutti i dati tranne i giocatori sono stati cancellati.")

if __name__ == "__main__":
    import asyncio

    async def test():
        db = Database()
        await db.connect()
        # Esempio: cancellare tutti i dati tranne i giocatori
        await db.delete_all_data_except_players()

    asyncio.run(test())