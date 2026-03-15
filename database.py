import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_KEY"]
        self.client: Client = create_client(url, key)

    # ── Giocatori ──────────────────────────────────────────────────────────

    def register_player(self, telegram_id: int, username: str | None, display_name: str):
        self.client.table("players").upsert({
            "telegram_id": telegram_id,
            "username": username,
            "display_name": display_name,
        }).execute()

    def get_player(self, telegram_id: int):
        res = self.client.table("players").select("*").eq("telegram_id", telegram_id).execute()
        return res.data[0] if res.data else None

    # ── Partite ────────────────────────────────────────────────────────────

    def create_game(self, chat_id: int, chat_title: str, created_by: int, target_score: int = 2000):
        res = self.client.table("games").insert({
            "chat_id": chat_id,
            "chat_title": chat_title or "Gruppo",
            "created_by": created_by,
            "target_score": target_score,
            "status": "waiting",
        }).execute()
        return res.data[0]

    def get_active_game(self, chat_id: int):
        res = (
            self.client.table("games")
            .select("*")
            .eq("chat_id", chat_id)
            .in_("status", ["waiting", "active"])
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    def start_game(self, game_id: int):
        self.client.table("games").update({"status": "active"}).eq("id", game_id).execute()

    def finish_game(self, game_id: int, winner_id: int):
        from datetime import datetime, timezone
        self.client.table("games").update({
            "status": "finished",
            "winner_id": winner_id,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", game_id).execute()

    # ── Giocatori in partita ───────────────────────────────────────────────

    def add_player_to_game(self, game_id: int, player_id: int):
        try:
            self.client.table("game_players").insert({
                "game_id": game_id,
                "player_id": player_id,
            }).execute()
            return True
        except Exception:
            return False  # già iscritto

    def get_game_players(self, game_id: int):
        res = (
            self.client.table("game_players")
            .select("*, players(display_name, username)")
            .eq("game_id", game_id)
            .order("total_score", desc=True)
            .execute()
        )
        return res.data

    def is_in_game(self, game_id: int, player_id: int) -> bool:
        res = (
            self.client.table("game_players")
            .select("id")
            .eq("game_id", game_id)
            .eq("player_id", player_id)
            .execute()
        )
        return bool(res.data)

    def update_player_score(self, game_id: int, player_id: int, delta: int):
        gp = (
            self.client.table("game_players")
            .select("total_score")
            .eq("game_id", game_id)
            .eq("player_id", player_id)
            .execute()
        )
        current = gp.data[0]["total_score"] if gp.data else 0
        self.client.table("game_players").update({
            "total_score": current + delta
        }).eq("game_id", game_id).eq("player_id", player_id).execute()
        return current + delta

    # ── Mani ──────────────────────────────────────────────────────────────

    def next_hand_number(self, game_id: int) -> int:
        res = (
            self.client.table("hands")
            .select("hand_number")
            .eq("game_id", game_id)
            .order("hand_number", desc=True)
            .limit(1)
            .execute()
        )
        return (res.data[0]["hand_number"] + 1) if res.data else 1

    def create_hand(self, game_id: int) -> dict:
        hand_number = self.next_hand_number(game_id)
        res = self.client.table("hands").insert({
            "game_id": game_id,
            "hand_number": hand_number,
        }).execute()
        return res.data[0]

    def save_hand_score(self, hand_id: int, player_id: int, data: dict):
        self.client.table("hand_scores").insert({
            "hand_id": hand_id,
            "player_id": player_id,
            **data,
        }).execute()

    def get_hands_history(self, game_id: int):
        res = (
            self.client.table("hands")
            .select("*, hand_scores(*, players(display_name))")
            .eq("game_id", game_id)
            .order("hand_number")
            .execute()
        )
        return res.data

    # ── Classifica globale ────────────────────────────────────────────────

    def get_classifica_globale(self):
        res = self.client.table("classifica_globale").select("*").execute()
        return res.data
