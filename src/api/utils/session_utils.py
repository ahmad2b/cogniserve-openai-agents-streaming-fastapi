"""
Simple session utilities for OpenAI Agents with environment-based configuration.

This module provides a clean, minimal interface for session memory that can be
easily enabled/disabled via environment variables.
"""

import os
import logging
from typing import Optional
from pathlib import Path

from agents import SQLiteSession

logger = logging.getLogger(__name__)

# Environment variable names
ENV_ENABLE_SESSIONS = "ENABLE_SESSIONS"
ENV_SESSION_DB_PATH = "SESSION_DB_PATH"

# Default configuration
DEFAULT_DB_PATH = "./conversations.db"


def is_sessions_enabled() -> bool:
    """
    Check if sessions are enabled via environment variable.
    
    Returns:
        bool: True if sessions are enabled, False otherwise
    """
    enabled = os.getenv(ENV_ENABLE_SESSIONS, "true").lower()
    return enabled in ("true", "1", "yes", "on")


def get_session_db_path() -> str:
    """
    Get the database path for sessions.
    
    Returns:
        str: Database file path
    """
    db_path = os.getenv(ENV_SESSION_DB_PATH, DEFAULT_DB_PATH)
    
    # Ensure directory exists for file-based storage
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    return db_path


def create_session_if_enabled(session_id: Optional[str]) -> Optional[SQLiteSession]:
    """
    Create a session if sessions are enabled and session_id is provided.
    
    Args:
        session_id: Optional session identifier
        
    Returns:
        SQLiteSession if sessions enabled and session_id provided, None otherwise
    """
    if not session_id:
        return None
        
    if not is_sessions_enabled():
        logger.debug("Sessions disabled, ignoring session_id")
        return None
    
    try:
        db_path = get_session_db_path()
        session = SQLiteSession(session_id=session_id, db_path=db_path)
        logger.info(f"Created session: {session_id} (db: {db_path})")
        return session
    except Exception as e:
        logger.error(f"Failed to create session {session_id}: {e}")
        return None


def clear_session(session_id: str) -> bool:
    """
    Clear a session's conversation history.
    
    Args:
        session_id: Session to clear
        
    Returns:
        bool: True if cleared successfully, False otherwise
    """
    if not is_sessions_enabled():
        logger.warning("Sessions disabled, cannot clear session")
        return False
    
    try:
        db_path = get_session_db_path()
        session = SQLiteSession(session_id=session_id, db_path=db_path)
        session.clear_session()
        logger.info(f"Cleared session: {session_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to clear session {session_id}: {e}")
        return False


def get_session_info() -> dict:
    """
    Get current session configuration information.
    
    Returns:
        dict: Session configuration details
    """
    return {
        "sessions_enabled": is_sessions_enabled(),
        "db_path": get_session_db_path() if is_sessions_enabled() else None,
        "env_variables": {
            ENV_ENABLE_SESSIONS: os.getenv(ENV_ENABLE_SESSIONS, "not set"),
            ENV_SESSION_DB_PATH: os.getenv(ENV_SESSION_DB_PATH, "not set")
        }
    } 