# utils/storage.py  — now backed by SQLite via database.py
from utils.database import (
    legacy_add_single_score,
    legacy_load_progress,
    save_multi_match,
    get_conn,
    init_db,
)
import sqlite3

def load_progress():
    return legacy_load_progress()

def add_single_score(name: str, score: int):
    legacy_add_single_score(name, score)

def add_multi_match(p1, p2, s1, s2, winner_text):
    save_multi_match(p1, p2, s1, s2, winner_text, "unknown", "unknown")

def delete_pair(match_key: str) -> bool:
    parts = match_key.split(" vs ", 1)
    if len(parts) != 2:
        return False
    p1, p2 = parts
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM multi_matches WHERE player1_name=? AND player2_name=?",
            (p1.strip(), p2.strip())
        )
        return cur.rowcount > 0

def reset_progress():
    with get_conn() as conn:
        conn.executescript("""
            DELETE FROM questions_log;
            DELETE FROM sessions;
            DELETE FROM multi_matches;
            DELETE FROM achievements;
        """)
