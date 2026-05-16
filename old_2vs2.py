import asyncio
import os
from dotenv import load_dotenv
from supabase import acreate_client

# Carica variabili d'ambiente
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

async def analyze_old_games():
    # Inizializza client
    supabase = await acreate_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("🔍 Recupero partite concluse...")
    
    # 1. Prendi tutte le partite finite
    games_res = await supabase.table("games").select("*").eq("status", "finished").execute()
    games = games_res.data
    
    report = []
    
    for game in games:
        # 2. Prendi i giocatori e i punteggi di quella partita
        players_res = await supabase.table("game_players") \
            .select("player_id, total_score, players(display_name)") \
            .eq("game_id", game["id"]) \
            .execute()
        
        players = players_res.data
        
        # Filtriamo solo le partite a 4 giocatori (2 vs 2)
        if len(players) == 4:
            # Trova il punteggio massimo
            max_score = max(p["total_score"] for p in players)
            # Identifica tutti i vincitori (la coppia)
            winners = [p for p in players if p["total_score"] == max_score]
            
            winner_names = [w["players"]["display_name"] for w in winners]
            
            report.append({
                "game_id": game["id"],
                "date": game["finished_at"],
                "winners": winner_names,
                "score": max_score,
                "is_tie": len(winners) > 1
            })

    # Stampa i risultati
    print(f"\n✅ Analisi completata su {len(report)} partite a 4 giocatori.\n")
    print(f"{'ID':<5} | {'Data':<25} | {'Punteggio':<10} | {'Vincitori'}")
    print("-" * 70)
    for r in report:
        win_str = ", ".join(r["winners"])
        print(f"{r['game_id']:<5} | {r['date']:<25} | {r['score']:<10} | {win_str}")

if __name__ == "__main__":
    asyncio.run(analyze_old_games())
