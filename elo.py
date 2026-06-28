from config import ELO_K_HIGH, ELO_K_MID, ELO_K_LOW


def get_k_factor(games_played: int) -> int:
    if games_played < 10:
        return ELO_K_HIGH
    if games_played < 30:
        return ELO_K_MID
    return ELO_K_LOW


def expected_score(rating_a: int, rating_b: int) -> float:
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def _detect_teams(players: list[dict]) -> list[set[int]] | None:
    """
    In a 4-player game, two players with the same total_score are partners.
    Returns [[team1_ids], [team2_ids]] if 2v2 teams detected, else None.
    """
    if len(players) != 4:
        return None
    score_groups: dict[int, list[int]] = {}
    for p in players:
        score_groups.setdefault(p["total_score"], []).append(p["player_id"])
    groups = list(score_groups.values())
    if len(groups) == 2 and all(len(g) == 2 for g in groups):
        return [set(g) for g in groups]
    return None


def calculate_elo_deltas(players: list[dict]) -> dict[int, int]:
    """
    Calculates ELO rating changes for all players after a game.

    Each player is compared pairwise against every opponent (not teammates).
    Deltas are normalized by the number of comparisons per player so that
    the magnitude stays comparable to a standard 1v1 game.

    Args:
        players: list of dicts with keys:
            - player_id: int
            - elo: int (current rating)
            - total_score: int (final game score, higher = better)
            - games_played: int (for dynamic K-factor)

    Returns:
        {player_id: delta_elo} (rounded to nearest integer, can be negative)
    """
    teams = _detect_teams(players)

    teammate_of: dict[int, int] = {}
    if teams:
        for team in teams:
            ids = list(team)
            teammate_of[ids[0]] = ids[1]
            teammate_of[ids[1]] = ids[0]

    sorted_by_score = sorted(players, key=lambda p: p["total_score"], reverse=True)
    ranks: dict[int, int] = {}
    prev_score = None
    for p in sorted_by_score:
        if p["total_score"] != prev_score:
            prev_score = p["total_score"]
        ranks[p["player_id"]] = len(ranks) + 1 if p["player_id"] not in ranks else ranks[p["player_id"]]

    # Rebuild ranks properly (tied scores get the same rank)
    ranks = {}
    rank = 1
    prev_score = None
    for p in sorted_by_score:
        if p["total_score"] != prev_score:
            rank = len(ranks) + 1
            prev_score = p["total_score"]
        ranks[p["player_id"]] = rank

    raw_deltas: dict[int, float] = {p["player_id"]: 0.0 for p in players}
    opponent_counts: dict[int, int] = {p["player_id"]: 0 for p in players}

    for i in range(len(players)):
        for j in range(i + 1, len(players)):
            pa, pb = players[i], players[j]
            if teammate_of.get(pa["player_id"]) == pb["player_id"]:
                continue

            ea = expected_score(pa["elo"], pb["elo"])
            eb = 1.0 - ea

            rank_a = ranks[pa["player_id"]]
            rank_b = ranks[pb["player_id"]]

            if rank_a < rank_b:
                sa, sb = 1.0, 0.0
            elif rank_a > rank_b:
                sa, sb = 0.0, 1.0
            else:
                sa, sb = 0.5, 0.5

            k_a = get_k_factor(pa["games_played"])
            k_b = get_k_factor(pb["games_played"])

            raw_deltas[pa["player_id"]] += k_a * (sa - ea)
            raw_deltas[pb["player_id"]] += k_b * (sb - eb)
            opponent_counts[pa["player_id"]] += 1
            opponent_counts[pb["player_id"]] += 1

    return {
        pid: round(raw_deltas[pid] / opponent_counts[pid]) if opponent_counts[pid] > 0 else 0
        for pid in raw_deltas
    }
