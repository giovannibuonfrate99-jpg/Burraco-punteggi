import pytest
from database import calculate_elo_deltas, _expected_score as expected_score, _get_k_factor as get_k_factor, _detect_teams


class TestKFactor:
    def test_provisional(self):
        assert get_k_factor(0) == 40
        assert get_k_factor(9) == 40

    def test_mid(self):
        assert get_k_factor(10) == 32
        assert get_k_factor(29) == 32

    def test_established(self):
        assert get_k_factor(30) == 24
        assert get_k_factor(100) == 24


class TestExpectedScore:
    def test_equal_ratings(self):
        assert expected_score(1000, 1000) == pytest.approx(0.5)

    def test_higher_rating_favored(self):
        assert expected_score(1200, 1000) > 0.5

    def test_lower_rating_underdog(self):
        assert expected_score(1000, 1200) < 0.5

    def test_symmetry(self):
        e_a = expected_score(1000, 1200)
        e_b = expected_score(1200, 1000)
        assert e_a + e_b == pytest.approx(1.0)


class TestDetectTeams:
    def test_two_players_no_teams(self):
        players = [
            {"player_id": 1, "total_score": 2100},
            {"player_id": 2, "total_score": 1800},
        ]
        assert _detect_teams(players) is None

    def test_three_players_no_teams(self):
        players = [
            {"player_id": 1, "total_score": 2100},
            {"player_id": 2, "total_score": 1800},
            {"player_id": 3, "total_score": 1500},
        ]
        assert _detect_teams(players) is None

    def test_four_players_teams_detected(self):
        players = [
            {"player_id": 1, "total_score": 2100},
            {"player_id": 2, "total_score": 2100},
            {"player_id": 3, "total_score": 1800},
            {"player_id": 4, "total_score": 1800},
        ]
        teams = _detect_teams(players)
        assert teams is not None
        assert len(teams) == 2
        team_sets = [frozenset(t) for t in teams]
        assert frozenset({1, 2}) in team_sets
        assert frozenset({3, 4}) in team_sets

    def test_four_players_all_different_no_teams(self):
        players = [
            {"player_id": 1, "total_score": 2100},
            {"player_id": 2, "total_score": 1900},
            {"player_id": 3, "total_score": 1800},
            {"player_id": 4, "total_score": 1500},
        ]
        assert _detect_teams(players) is None


class TestCalculateEloDeltas:
    def _make_player(self, pid: int, score: int, elo: int = 1000, games: int = 0) -> dict:
        return {"player_id": pid, "total_score": score, "elo": elo, "games_played": games}

    def test_two_players_zero_sum(self):
        players = [
            self._make_player(1, 2100),
            self._make_player(2, 1800),
        ]
        deltas = calculate_elo_deltas(players)
        assert deltas[1] + deltas[2] == pytest.approx(0, abs=1)

    def test_winner_gains_elo(self):
        players = [
            self._make_player(1, 2100),
            self._make_player(2, 1800),
        ]
        deltas = calculate_elo_deltas(players)
        assert deltas[1] > 0
        assert deltas[2] < 0

    def test_beating_stronger_opponent_bigger_gain(self):
        upset = [
            self._make_player(1, 2100, elo=800),   # weaker upsets stronger
            self._make_player(2, 1800, elo=1200),
        ]
        normal = [
            self._make_player(1, 2100, elo=1200),  # stronger beats weaker
            self._make_player(2, 1800, elo=800),
        ]
        deltas_upset = calculate_elo_deltas(upset)
        deltas_normal = calculate_elo_deltas(normal)
        assert deltas_upset[1] > deltas_normal[1]

    def test_three_players_zero_sum(self):
        players = [
            self._make_player(1, 2100),
            self._make_player(2, 1800),
            self._make_player(3, 1500),
        ]
        deltas = calculate_elo_deltas(players)
        total = sum(deltas.values())
        assert total == pytest.approx(0, abs=2)

    def test_three_players_ranking(self):
        players = [
            self._make_player(1, 2100),
            self._make_player(2, 1800),
            self._make_player(3, 1500),
        ]
        deltas = calculate_elo_deltas(players)
        assert deltas[1] > deltas[2] > deltas[3]
        assert deltas[1] > 0
        assert deltas[3] < 0

    def test_team_game_teammates_not_compared(self):
        # Teams: {1,2} vs {3,4}; team 1 wins
        players = [
            self._make_player(1, 2100),
            self._make_player(2, 2100),
            self._make_player(3, 1800),
            self._make_player(4, 1800),
        ]
        deltas = calculate_elo_deltas(players)
        # Both winners gain, both losers lose
        assert deltas[1] > 0
        assert deltas[2] > 0
        assert deltas[3] < 0
        assert deltas[4] < 0
        # Teammates have symmetric deltas (same ELO, same opponents)
        assert deltas[1] == deltas[2]
        assert deltas[3] == deltas[4]

    def test_team_game_zero_sum(self):
        players = [
            self._make_player(1, 2100),
            self._make_player(2, 2100),
            self._make_player(3, 1800),
            self._make_player(4, 1800),
        ]
        deltas = calculate_elo_deltas(players)
        assert sum(deltas.values()) == pytest.approx(0, abs=2)

    def test_higher_k_factor_for_new_players(self):
        veteran = [
            self._make_player(1, 2100, games=50),
            self._make_player(2, 1800, games=50),
        ]
        rookie = [
            self._make_player(1, 2100, games=0),
            self._make_player(2, 1800, games=0),
        ]
        deltas_veteran = calculate_elo_deltas(veteran)
        deltas_rookie  = calculate_elo_deltas(rookie)
        assert abs(deltas_rookie[1]) > abs(deltas_veteran[1])
