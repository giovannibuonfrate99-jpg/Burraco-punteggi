import os
from supabase import create_client, Client

# ==========================================
# CONFIGURAZIONE SUPABASE
# Inserisci qui le tue credenziali Supabase
# ==========================================
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
def main():
    print("Connessione a Supabase in corso...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    try:
        # Recuperiamo tutti i giocatori e, per ognuno, i relativi record in game_players
        # Questo ci permette di vedere se hanno mai partecipato a una partita (di qualsiasi stato)
        response = supabase.table("players").select("telegram_id, display_name, username, game_players(id)").execute()
        all_players = response.data
        
    except Exception as e:
        print(f"Errore durante la connessione o il recupero dei dati: {e}")
        return

    # Filtriamo i giocatori che non hanno nessun record in game_players
    giocatori_inattivi = []
    for player in all_players:
        if len(player.get("game_players", [])) == 0:
            giocatori_inattivi.append(player)

    # Se non ci sono giocatori da eliminare, fermiamo lo script
    if not giocatori_inattivi:
        print("\nOttimo! Nessun giocatore con 0 partite trovato. Il database è pulito.")
        return

    # Mostriamo l'elenco dei giocatori inattivi
    print(f"\nSono stati trovati {len(giocatori_inattivi)} giocatori con 0 partite:")
    print("-" * 50)
    for p in giocatori_inattivi:
        username_str = f" (@{p['username']})" if p.get('username') else ""
        print(f"- {p['display_name']}{username_str} (ID: {p['telegram_id']})")
    print("-" * 50)

    # Chiediamo conferma all'utente
    scelta = input("\nVuoi procedere con l'eliminazione definitiva di questi giocatori dal database? (s/n): ")

    if scelta.strip().lower() != 's':
        print("Operazione annullata. Nessun giocatore è stato eliminato.")
        return

    print("\nInizio eliminazione...")
    eliminati = 0
    errori = 0

    # Ciclo per eliminare i giocatori
    for p in giocatori_inattivi:
        try:
            # Elimina il giocatore usando il suo telegram_id
            supabase.table("players").delete().eq("telegram_id", p["telegram_id"]).execute()
            print(f"✅ Eliminato: {p['display_name']}")
            eliminati += 1
        except Exception as e:
            # Se un giocatore ha ad esempio creato una partita (created_by) ma non vi ha partecipato,
            # la Foreign Key bloccherà l'eliminazione. Catturiamo l'errore per non far crashare lo script.
            print(f"❌ Impossibile eliminare {p['display_name']}. Potrebbe essere collegato ad altre tabelle. Errore: {e}")
            errori += 1

    # Resoconto finale
    print("\n" + "=" * 30)
    print("OPERAZIONE COMPLETATA")
    print(f"Giocatori eliminati: {eliminati}")
    if errori > 0:
        print(f"Errori riscontrati: {errori}")
    print("=" * 30)

if __name__ == "__main__":
    main()