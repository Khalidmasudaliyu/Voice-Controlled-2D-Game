# utils/database.py
import sqlite3
import os
import hashlib
import logging
from datetime import datetime

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "progress.db"))

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL UNIQUE COLLATE NOCASE,
            pin_hash    TEXT,
            age         INTEGER DEFAULT 0,
            avatar      TEXT    DEFAULT 'star',
            created_at  TEXT    DEFAULT (datetime('now')),
            last_login  TEXT
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id    INTEGER NOT NULL REFERENCES players(id),
            game_type    TEXT    NOT NULL,
            difficulty   TEXT    NOT NULL,
            score        INTEGER DEFAULT 0,
            total_q      INTEGER DEFAULT 0,
            correct_q    INTEGER DEFAULT 0,
            duration_sec INTEGER DEFAULT 0,
            played_at    TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS questions_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  INTEGER NOT NULL REFERENCES sessions(id),
            question    TEXT    NOT NULL,
            expected    TEXT    NOT NULL,
            heard       TEXT,
            correct     INTEGER DEFAULT 0,
            tries_used  INTEGER DEFAULT 1,
            asked_at    TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS sentences (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            lang        TEXT    NOT NULL DEFAULT 'en',
            category    TEXT    NOT NULL DEFAULT 'general',
            difficulty  TEXT    NOT NULL DEFAULT 'easy',
            sentence    TEXT    NOT NULL,
            answer      TEXT    NOT NULL,
            hint        TEXT
        );

        CREATE TABLE IF NOT EXISTS multi_matches (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            player1_id  INTEGER REFERENCES players(id),
            player2_id  INTEGER REFERENCES players(id),
            player1_name TEXT,
            player2_name TEXT,
            score1      INTEGER DEFAULT 0,
            score2      INTEGER DEFAULT 0,
            winner      TEXT,
            game_type   TEXT,
            difficulty  TEXT,
            played_at   TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS achievements (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id   INTEGER NOT NULL REFERENCES players(id),
            badge       TEXT    NOT NULL,
            earned_at   TEXT    DEFAULT (datetime('now'))
        );
        """)
        _seed_sentences(conn)

def _seed_sentences(conn):
    existing = conn.execute("SELECT COUNT(*) FROM sentences").fetchone()[0]
    if existing > 0:
        return
    sentences = [
        # English easy
        ("en","greetings","easy","Say hello to greet someone","hello","Start with H"),
        ("en","greetings","easy","What do you say when you leave?","goodbye","Ends with bye"),
        ("en","greetings","easy","Say thank you to show gratitude","thank you","Two words"),
        ("en","greetings","easy","What do you say in the morning?","good morning","Two words"),
        ("en","greetings","easy","How do you ask if someone is well?","how are you","Three words"),
        # English medium
        ("en","animals","medium","A dog says woof. A cat says what?","meow","Sounds like a cat"),
        ("en","animals","medium","This animal has a long neck","giraffe","Tallest animal"),
        ("en","animals","medium","This animal lives in water and has fins","fish","Lives in the sea"),
        ("en","colors","medium","The sky is this color on a clear day","blue","Like the ocean"),
        ("en","colors","medium","Grass and leaves are this color","green","Color of nature"),
        ("en","colors","medium","The sun looks this color","yellow","Bright and warm"),
        # English hard
        ("en","sentences","hard","Finish: The quick brown fox jumps over the lazy","dog","Common typing test"),
        ("en","sentences","hard","Finish: An apple a day keeps the doctor","away","Health proverb"),
        ("en","sentences","hard","Finish: Actions speak louder than","words","Famous saying"),
        ("en","sentences","hard","Finish: Every cloud has a silver","lining","Optimism saying"),
        ("en","sentences","hard","Finish: Better late than","never","Common proverb"),
        ("en","sentences","hard","Finish: Look before you","leap","Safety proverb"),
        ("en","sentences","hard","Finish: Two wrongs don't make a","right","Ethics saying"),
        # Hausa easy
        ("ha","gaisuwa","easy","Faɗi kalmar gaisuwa da safe","sannu","Farko da S"),
        ("ha","gaisuwa","easy","Yaya ake cewa lafiya lau?","lafiya lau","Kalma biyu"),
        ("ha","gaisuwa","easy","Yaya ake cewa na gode?","na gode","Kalma biyu"),
        ("ha","gaisuwa","easy","Yaya ake cewa sai anjima?","sai anjima","Kalma biyu"),
        # Hausa medium
        ("ha","dabbobi","medium","Wannan dabba tana ihu kukan kaza","kaza","Dabbar gida"),
        ("ha","dabbobi","medium","Wannan dabba tana ba da madara","saniya","Dabbar gona"),
        ("ha","launi","medium","Launi na sama a rana mai kyau","shuɗi","Launi na ruwa"),
        ("ha","launi","medium","Launi na ciyawa da ganye","kore","Launi na daji"),
        # Hausa hard
        ("ha","karin magana","hard","Kammala: Haƙuri shi ne","maganin dukan cuta","Karin magana"),
        ("ha","karin magana","hard","Kammala: Duk wanda ya yi gaskiya","Allah zai taimake shi","Karin magana"),
        ("ha","karin magana","hard","Kammala: Ilimi shi ne","haske","Karin magana"),
    ]
    conn.executemany(
        "INSERT INTO sentences (lang,category,difficulty,sentence,answer,hint) VALUES (?,?,?,?,?,?)",
        sentences
    )

# ── Player auth ──────────────────────────────────────────────────────────────

def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()

def create_player(name: str, pin: str = "", age: int = 0) -> int:
    ph = hash_pin(pin) if pin else None
    with get_conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO players (name, pin_hash, age) VALUES (?,?,?)",
                (name.strip(), ph, age)
            )
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None  # name taken

def get_player(name: str):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM players WHERE name=? COLLATE NOCASE", (name,)).fetchone()

def verify_pin(name: str, pin: str) -> bool:
    row = get_player(name)
    if not row:
        return False
    if not row["pin_hash"]:
        return True  # no PIN set
    return row["pin_hash"] == hash_pin(pin)

def update_last_login(player_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE players SET last_login=datetime('now') WHERE id=?", (player_id,))

def list_players():
    with get_conn() as conn:
        return conn.execute("SELECT id, name, age, avatar, last_login FROM players ORDER BY name").fetchall()

# ── Sessions ─────────────────────────────────────────────────────────────────

def start_session(player_id: int, game_type: str, difficulty: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO sessions (player_id, game_type, difficulty) VALUES (?,?,?)",
            (player_id, game_type, difficulty)
        )
        return cur.lastrowid

def finish_session(session_id: int, score: int, total_q: int, correct_q: int, duration_sec: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE sessions SET score=?,total_q=?,correct_q=?,duration_sec=? WHERE id=?",
            (score, total_q, correct_q, duration_sec, session_id)
        )

def log_question(session_id: int, question: str, expected: str, heard: str, correct: bool, tries_used: int):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO questions_log (session_id,question,expected,heard,correct,tries_used) VALUES (?,?,?,?,?,?)",
            (session_id, question, expected, heard or "", int(correct), tries_used)
        )

# ── Scores / leaderboard ─────────────────────────────────────────────────────

def get_high_score(player_id: int, game_type: str = None):
    with get_conn() as conn:
        if game_type:
            row = conn.execute(
                "SELECT MAX(score) as hs FROM sessions WHERE player_id=? AND game_type=?",
                (player_id, game_type)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT MAX(score) as hs FROM sessions WHERE player_id=?",
                (player_id,)
            ).fetchone()
        return row["hs"] or 0

def get_leaderboard(game_type: str = None, limit: int = 10):
    with get_conn() as conn:
        if game_type:
            return conn.execute("""
                SELECT p.name, MAX(s.score) as best, COUNT(s.id) as games_played,
                       ROUND(AVG(s.correct_q * 100.0 / MAX(s.total_q, 1)), 1) as avg_accuracy
                FROM sessions s JOIN players p ON p.id=s.player_id
                WHERE s.game_type=?
                GROUP BY p.id ORDER BY best DESC LIMIT ?
            """, (game_type, limit)).fetchall()
        return conn.execute("""
            SELECT p.name, MAX(s.score) as best, COUNT(s.id) as games_played,
                   ROUND(AVG(s.correct_q * 100.0 / MAX(s.total_q, 1)), 1) as avg_accuracy
            FROM sessions s JOIN players p ON p.id=s.player_id
            GROUP BY p.id ORDER BY best DESC LIMIT ?
        """, (limit,)).fetchall()

def get_player_stats(player_id: int):
    with get_conn() as conn:
        row = conn.execute("""
            SELECT
                COUNT(id)                                          as total_sessions,
                SUM(score)                                         as total_score,
                MAX(score)                                         as best_score,
                ROUND(AVG(score), 1)                               as avg_score,
                SUM(correct_q)                                     as total_correct,
                SUM(total_q)                                       as total_questions,
                ROUND(SUM(correct_q)*100.0/MAX(SUM(total_q),1),1) as accuracy,
                SUM(duration_sec)                                  as total_time_sec,
                MAX(played_at)                                     as last_played
            FROM sessions WHERE player_id=?
        """, (player_id,)).fetchone()
        return row

def get_streak(player_id: int) -> int:
    """Return current daily login streak."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT DATE(played_at) as d FROM sessions
            WHERE player_id=? GROUP BY d ORDER BY d DESC
        """, (player_id,)).fetchall()
    if not rows:
        return 0
    streak = 1
    from datetime import date, timedelta
    today = date.today()
    prev = datetime.strptime(rows[0]["d"], "%Y-%m-%d").date()
    if (today - prev).days > 1:
        return 0
    for i in range(1, len(rows)):
        cur = datetime.strptime(rows[i]["d"], "%Y-%m-%d").date()
        if (prev - cur).days == 1:
            streak += 1
            prev = cur
        else:
            break
    return streak

# ── Sentences ────────────────────────────────────────────────────────────────

def get_sentences(lang: str, difficulty: str, limit: int = 20):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM sentences WHERE lang=? AND difficulty=? ORDER BY RANDOM() LIMIT ?",
            (lang, difficulty, limit)
        ).fetchall()

# ── Multiplayer ──────────────────────────────────────────────────────────────

def save_multi_match(p1_name, p2_name, s1, s2, winner, game_type, difficulty, p1_id=None, p2_id=None):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO multi_matches
            (player1_id,player2_id,player1_name,player2_name,score1,score2,winner,game_type,difficulty)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (p1_id, p2_id, p1_name, p2_name, s1, s2, winner, game_type, difficulty))

def get_multi_history(limit: int = 30):
    with get_conn() as conn:
        return conn.execute("""
            SELECT player1_name, player2_name, score1, score2, winner, game_type, difficulty, played_at
            FROM multi_matches ORDER BY played_at DESC LIMIT ?
        """, (limit,)).fetchall()

# ── Achievements ─────────────────────────────────────────────────────────────

BADGE_RULES = {
    "first_game":    "Played your first game!",
    "perfect_10":    "Got 10/10 correct!",
    "streak_3":      "3-day streak!",
    "streak_7":      "7-day streak!",
    "century":       "Scored 100 total points!",
    "speed_demon":   "Finished a round in under 60 seconds!",
    "bilingual":     "Played in both English and Hausa!",
}

def award_badge(player_id: int, badge: str):
    with get_conn() as conn:
        exists = conn.execute(
            "SELECT 1 FROM achievements WHERE player_id=? AND badge=?", (player_id, badge)
        ).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO achievements (player_id, badge) VALUES (?,?)", (player_id, badge)
            )
            return True
    return False

def get_badges(player_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT badge, earned_at FROM achievements WHERE player_id=? ORDER BY earned_at",
            (player_id,)
        ).fetchall()

# ── Legacy compat (used by old storage.py callers) ───────────────────────────

def legacy_add_single_score(name: str, score: int):
    p = get_player(name)
    if not p:
        create_player(name)
        p = get_player(name)
    if p:
        sid = start_session(p["id"], "legacy", "easy")
        finish_session(sid, score, score, score, 0)

def legacy_load_progress():
    with get_conn() as conn:
        single = {}
        rows = conn.execute("""
            SELECT p.name, MAX(s.score) as best
            FROM sessions s JOIN players p ON p.id=s.player_id
            GROUP BY p.id
        """).fetchall()
        for r in rows:
            single[r["name"]] = r["best"]
        multi = {}
        matches = conn.execute(
            "SELECT * FROM multi_matches ORDER BY played_at DESC"
        ).fetchall()
        for m in matches:
            key = f"{m['player1_name']} vs {m['player2_name']}"
            entry = f"{m['player1_name']}: {m['score1']}, {m['player2_name']}: {m['score2']} → Winner: {m['winner']}"
            multi.setdefault(key, []).append(entry)
        return {"single": single, "multi": multi}

init_db()
