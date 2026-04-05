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
    conn.execute("DELETE FROM sentences")
    sentences = [
        # ── ENGLISH EASY: 2–4 word phrases, real daily life ──────────────────
        ("en","daily life","easy","I am ___","here","Where are you?"),
        ("en","daily life","easy","I am ___","ready","Are you prepared?"),
        ("en","daily life","easy","I am ___","hungry","You need food"),
        ("en","daily life","easy","I am ___","tired","You need rest"),
        ("en","daily life","easy","I am ___","happy","You feel good"),
        ("en","daily life","easy","I am ___","sorry","You made a mistake"),
        ("en","daily life","easy","I am ___","fine","You are okay"),
        ("en","daily life","easy","I am ___","late","You missed the time"),
        ("en","daily life","easy","I am ___","lost","You don't know the way"),
        ("en","daily life","easy","I am ___","done","You finished the task"),
        # ── ENGLISH MEDIUM: 5–8 word sentences ───────────────────────────────
        ("en","school","medium","I go to school every ___","day","How often?"),
        ("en","school","medium","She reads a book every ___","night","When does she read?"),
        ("en","school","medium","He drinks water when he is ___","thirsty","Why drink water?"),
        ("en","school","medium","We play outside when the sun ___","shines","When do you play?"),
        ("en","school","medium","I wash my hands before I ___","eat","Good hygiene habit"),
        ("en","work","medium","She wakes up early to go to ___","work","Where does she go?"),
        ("en","work","medium","He saves money to buy a ___","house","What does he want?"),
        ("en","work","medium","They work hard so they can ___","succeed","What is the goal?"),
        ("en","work","medium","I call my mother when I feel ___","lonely","Who do you call?"),
        ("en","work","medium","She cooks dinner for her ___","family","Who does she cook for?"),
        # ── ENGLISH HARD: full real-world sentences ───────────────────────────
        ("en","real world","hard","If you want to pass the exam, you must study ___","hard","What must you do?"),
        ("en","real world","hard","The doctor told him to rest and drink plenty of ___","water","Doctor's advice"),
        ("en","real world","hard","She applied for the job because she needed the ___","money","Why apply?"),
        ("en","real world","hard","The teacher asked the students to be quiet and ___","listen","Classroom rule"),
        ("en","real world","hard","He missed the bus so he had to walk to ___","school","What happened next?"),
        ("en","real world","hard","You should always tell the truth even when it is ___","hard","Honesty lesson"),
        ("en","real world","hard","She saved enough money to pay her rent and buy ___","food","Basic needs"),
        ("en","real world","hard","The farmer wakes up at dawn to water his ___","crops","Farm life"),
        ("en","real world","hard","He studied medicine for six years to become a ___","doctor","Long journey"),
        ("en","real world","hard","Without clean water, people cannot stay ___","healthy","Basic need"),
        # ── HAUSA EASY ────────────────────────────────────────────────────────
        ("ha","rayuwa","easy","Ina ___ yanzu","nan","Ina kake?"),
        ("ha","rayuwa","easy","Ina ___ sosai","jin yunwa","Kana buƙatar abinci"),
        ("ha","rayuwa","easy","Ina ___ yau","farin ciki","Yaya kake ji?"),
        ("ha","rayuwa","easy","Ina ___ da wannan","nadama","Ka yi kuskure"),
        ("ha","rayuwa","easy","Ina ___ yanzu","gajiya","Kana buƙatar hutawa"),
        # ── HAUSA MEDIUM ──────────────────────────────────────────────────────
        ("ha","makaranta","medium","Ina zuwa makaranta kowace ___","rana","Yaushe?"),
        ("ha","makaranta","medium","Tana karanta littafi duk ___","dare","Yaushe take karatu?"),
        ("ha","makaranta","medium","Muna wasa waje idan rana ta ___","haskaka","Yaushe kuke wasa?"),
        ("ha","aiki","medium","Tana tashi da wuri don zuwa ___","aiki","Ina take tafi?"),
        ("ha","aiki","medium","Suna aiki tuƙuru don su ___","ci nasara","Menene manufarsu?"),
        # ── HAUSA HARD ────────────────────────────────────────────────────────
        ("ha","duniya","hard","Idan kana son cin jarrabawa, dole ne ka yi ___","karatu","Me ya kamata ka yi?"),
        ("ha","duniya","hard","Likita ya ce masa ya huta ya sha ruwa mai ___","yawa","Shawarar likita"),
        ("ha","duniya","hard","Ta nemi aiki saboda tana buƙatar ___","kuɗi","Me ya sa ta nemi aiki?"),
        ("ha","duniya","hard","Ba tare da ruwa mai tsabta ba, mutane ba za su iya zama ___","lafiya","Buƙatar rayuwa"),
        ("ha","duniya","hard","Ya yi karatu shekara shida don ya zama ___","likita","Tafiya mai nisa"),
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
