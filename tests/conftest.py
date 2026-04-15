"""
Pytest configuration e fixtures shared per tutti i test
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
import os
import sys

# Aggiungi il parent directory per importare bot e database
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/../"))


@pytest.fixture
def event_loop():
    """Crea un event loop per i test async."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_supabase_client():
    """Mock del client Supabase asincrono."""
    client = AsyncMock()
    
    # Mock della tabella() method
    client.table = MagicMock()
    
    # Mock RPC method
    client.rpc = MagicMock()
    
    return client


@pytest.fixture
def sample_player():
    """Giocatore sample per test."""
    return {
        "telegram_id": 123456,
        "username": "testuser",
        "display_name": "Test Player",
        "created_at": "2026-04-15T12:00:00+00:00"
    }


@pytest.fixture
def sample_game():
    """Partita sample per test."""
    return {
        "id": 1,
        "chat_id": 789012,
        "chat_title": "Test Group",
        "status": "active",
        "target_score": 2000,
        "created_by": 123456,
        "winner_id": None,
        "created_at": "2026-04-15T12:00:00+00:00",
        "finished_at": None
    }


@pytest.fixture
def sample_game_players():
    """Giocatori in una partita sample."""
    return [
        {
            "id": 1,
            "game_id": 1,
            "player_id": 123456,
            "total_score": 150,
            "players": {"display_name": "Alice", "username": "alice"}
        },
        {
            "id": 2,
            "game_id": 1,
            "player_id": 789012,
            "total_score": 200,
            "players": {"display_name": "Bob", "username": "bob"}
        }
    ]


@pytest.fixture
def sample_hand():
    """Mano sample per test."""
    return {
        "id": 101,
        "game_id": 1,
        "hand_number": 1,
        "created_at": "2026-04-15T12:05:00+00:00"
    }


@pytest.fixture
def sample_hand_scores():
    """Punteggi di una mano sample."""
    return [
        {
            "id": 1001,
            "hand_id": 101,
            "player_id": 123456,
            "punteggio_mano": 150
        },
        {
            "id": 1002,
            "hand_id": 101,
            "player_id": 789012,
            "punteggio_mano": 200
        }
    ]
