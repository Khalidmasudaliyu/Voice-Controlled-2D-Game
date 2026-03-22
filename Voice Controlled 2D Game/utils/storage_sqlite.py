import json
import sqlite3
from pathlib import Path

JSON_PATH = Path(r"C:\Users\mffar\OneDrive\Desktop\FINAL YEAR PROJECT 2025\Voice Controlled 2D Game\progress.json")
DB_PATH = Path("progress.db")


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS single_scores (
                name TEXT PRIMARY KEY,
                score INTEGER NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS multi_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player1 TEXT NOT NULL,
                player2 TEXT NOT NULL,
                score1 INTEGER NOT NULL,
                score2 INTEGER NOT NULL,
                winner_text TEXT NOT NULL
            )
            """
        )
        conn.commit()


# Ensure DB schema exists on import
init_db()


def import_json_to_db():
    with JSON_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    with get_connection() as conn:
        cur = conn.cursor()

        # Insert single scores
        for name, score in data.get("single", {}).items():
            cur.execute(
                "INSERT OR REPLACE INTO single_scores (name, score) VALUES (?, ?)",
                (name, score),
            )

        # Insert multi matches
        for match_key, entries in data.get("multi", {}).items():
            p1, _, p2 = match_key.partition(" vs ")
            for entry in entries:
                try:
                    left, winner_part = entry.split(" → Winner: ")
                    scores = left.split(", ")
                    s1 = int(scores[0].split(": ")[1])
                    s2 = int(scores[1].split(": ")[1])
                    cur.execute(
                        """
                        INSERT INTO multi_matches (player1, player2, score1, score2, winner_text)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (p1, p2, s1, s2, winner_part),
                    )
                except Exception as e:
                    print(f"Skipping malformed entry '{entry}' in match '{match_key}': {e}")
        conn.commit()
    print("JSON imported into SQLite successfully.")


def show_all_data():
    with get_connection() as conn:
        cur = conn.cursor()

        print("\n--- Single Scores ---")
        for row in cur.execute("SELECT name, score FROM single_scores"):
            print(row)

        print("\n--- Multi Matches ---")
        for row in cur.execute(
            "SELECT player1, player2, score1, score2, winner_text FROM multi_matches"
        ):
            print(row)


if __name__ == "__main__":
    import_json_to_db()
    show_all_data()
