"""
Test per operazioni critiche del database
- Race condition in update_player_score (RPC atomico)
- Save/undo hand operations
- Game transitions
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.asyncio


class TestUpdatePlayerScoreAtomic:
    """Test per il RPC atomico update_player_score."""
    
    async def test_update_score_single_call(self, mock_supabase_client):
        """Test: Single update works correctly."""
        from database import Database
        
        # Mock the RPC call
        mock_result = MagicMock()
        mock_result.data = 350  # Nuovo punteggio atomico
        
        mock_supabase_client.rpc.return_value.execute = AsyncMock(return_value=mock_result)
        
        db = Database()
        db.client = mock_supabase_client
        
        # Call
        result = await db.update_player_score(game_id=1, player_id=123456, delta=150)
        
        # Assert
        assert result == 350
        mock_supabase_client.rpc.assert_called_once_with(
            "update_score_atomic",
            {
                "p_game_id": 1,
                "p_player_id": 123456,
                "p_delta": 150,
            }
        )

    async def test_update_score_negative_delta(self, mock_supabase_client):
        """Test: Negative delta (undo/penalty) works."""
        from database import Database
        
        mock_result = MagicMock()
        mock_result.data = 50  # 200 - 150 = 50
        
        mock_supabase_client.rpc.return_value.execute = AsyncMock(return_value=mock_result)
        
        db = Database()
        db.client = mock_supabase_client
        
        result = await db.update_player_score(game_id=1, player_id=123456, delta=-150)
        
        assert result == 50

    async def test_update_score_player_not_found(self, mock_supabase_client):
        """Test: Error if player not in game."""
        from database import Database
        
        # Mock RPC raising exception (player not found)
        mock_supabase_client.rpc.return_value.execute = AsyncMock(
            side_effect=Exception("Giocatore non trovato in questa partita")
        )
        
        db = Database()
        db.client = mock_supabase_client
        
        # Should raise
        with pytest.raises(RuntimeError):
            await db.update_player_score(game_id=1, player_id=999999, delta=150)

    async def test_concurrent_updates_consistency(self, mock_supabase_client):
        """
        Test: Concurrent updates don't lose data.
        
        In realtà, il test di race condition vero richiederebbe
        un database reale. Questo test mocka il comportamento atomico.
        """
        from database import Database
        
        # Simuliamo due update concorrenti
        player_id = 123456
        game_id = 1
        
        # Prima chiamata: +100
        mock_result_1 = MagicMock()
        mock_result_1.data = 100
        
        # Seconda chiamata: +150 (non 50, perché atomica!)
        mock_result_2 = MagicMock()
        mock_result_2.data = 250  # 100 + 150 atomicamente
        
        # Simuliamo il comportamento
        mock_supabase_client.rpc.return_value.execute = AsyncMock(
            side_effect=[mock_result_1, mock_result_2]
        )
        
        db = Database()
        db.client = mock_supabase_client
        
        # Due update concorrenti
        result_1 = await db.update_player_score(game_id, player_id, 100)
        result_2 = await db.update_player_score(game_id, player_id, 150)
        
        # Con RPC atomico, il totale è sempre 250 (non 50 in una race condition non-atomica)
        assert result_1 == 100
        assert result_2 == 250


class TestSaveFullHand:
    """Test per il salvataggio atomico di una mano."""
    
    async def test_save_hand_success(self, mock_supabase_client, sample_game, sample_hand):
        """Test: Save hand con tutti i punteggi."""
        from database import Database
        
        # Mock insert delle mani
        hand_response = MagicMock()
        hand_response.data = [sample_hand]
        
        # Mock insert dei punteggi
        scores_response = MagicMock()
        scores_response.data = [
            {"id": 1001, "hand_id": 101, "player_id": 123456, "punteggio_mano": 150},
            {"id": 1002, "hand_id": 101, "player_id": 789012, "punteggio_mano": 200},
        ]
        
        # Chain mocka per next_hand_number
        mock_select = MagicMock()
        mock_select_result = MagicMock()
        mock_select_result.data = [{"hand_number": 0}]
        mock_select.order.return_value = mock_select
        mock_select.limit.return_value = mock_select
        mock_select.execute = AsyncMock(return_value=mock_select_result)
        
        mock_supabase_client.table.return_value = mock_select
        
        # Setup per insert
        insert_mock = MagicMock()
        insert_mock.execute = AsyncMock(side_effect=[hand_response, scores_response])
        mock_supabase_client.table.return_value.insert = MagicMock(return_value=insert_mock)
        
        db = Database()
        db.client = mock_supabase_client
        
        # Call
        scored = {123456: 150, 789012: 200}
        result = await db.save_full_hand(sample_game["id"], scored)
        
        # Assert
        assert result is not None

    async def test_save_hand_partial_failure(self, mock_supabase_client, sample_game):
        """Test: Error handling if hand save fails."""
        from database import Database
        
        # Mock che simula fallimento
        error_msg = "Database connection error"
        
        mock_supabase_client.table.return_value.select.return_value.order.return_value.limit.return_value.execute = AsyncMock(
            side_effect=Exception(error_msg)
        )
        
        db = Database()
        db.client = mock_supabase_client
        
        # Should raise RuntimeError wrapped
        with pytest.raises(RuntimeError):
            await db.save_full_hand(sample_game["id"], {123456: 150})


class TestValidateScoreInput:
    """Test per la validazione del punteggio."""
    
    def test_valid_positive_score(self):
        """Test: Numero positivo valido."""
        from bot import _validate_score_input
        
        is_valid, score, msg = _validate_score_input("150")
        
        assert is_valid is True
        assert score == 150
        assert msg == ""

    def test_valid_negative_score(self):
        """Test: Numero negativo valido."""
        from bot import _validate_score_input
        
        is_valid, score, msg = _validate_score_input("-50")
        
        assert is_valid is True
        assert score == -50
        assert msg == ""

    def test_zero_score(self):
        """Test: Zero è valido."""
        from bot import _validate_score_input
        
        is_valid, score, msg = _validate_score_input("0")
        
        assert is_valid is True
        assert score == 0

    def test_invalid_text(self):
        """Test: Testo non-numerico rejected."""
        from bot import _validate_score_input
        
        is_valid, score, msg = _validate_score_input("abc")
        
        assert is_valid is False
        assert score is None
        assert "numero" in msg.lower()

    def test_score_too_high(self):
        """Test: Numero troppo grande rejected."""
        from bot import _validate_score_input
        
        is_valid, score, msg = _validate_score_input("9999999")
        
        assert is_valid is False
        assert "troppo alto" in msg.lower()

    def test_empty_input(self):
        """Test: Input vuoto rejected."""
        from bot import _validate_score_input
        
        is_valid, score, msg = _validate_score_input("")
        
        assert is_valid is False
