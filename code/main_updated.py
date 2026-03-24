# main.py
import tkinter as tk
from tkinter import messagebox
import uuid
import random
import os
import time
from datetime import datetime

from translations import t, set_language, current_language
from utils.database import (
    create_player,
    get_player,
    verify_pin,
    update_last_login,
    start_session,
    finish_session,
    log_question,
    get_player_stats,
    get_leaderboard,
    get_badges,
    award_badge,
    get_streak,
    get_sentences,
    get_multi_history,
    get_conn,
    init_db,
    legacy_add_single_score,
    legacy_load_progress,
    save_multi_match,
)
from utils.voice import listen_async, ERR_NO_MIC, ERR_NO_SPEECH, ERR_NO_INTERNET
from utils.tts import speak

ASSETS_UI = os.path.join(os.path.dirname(__file__), "assets", "images", "ui")
BG = "#fff9e6"
HEADER_BG = "#ff6f91"
BTN_FONT = ("Comic Sans MS", 14, "bold")
TITLE_FONT = ("Comic Sans MS", 26, "bold")
TRIES_PER_QUESTION = 2
BASE_QUESTIONS = 10
DIFF_ROUNDS = {"easy": 0, "medium": 2, "hard": 5}
MULTI_MULT = 1.2

BADGE_ICON = {
    "first_game": "🎮",
    "perfect_10": "💯",
    "streak_3": "🔥",
    "streak_7": "⚡",
    "century": "💰",
    "speed_demon": "⚡",
    "bilingual": "🌍",
}

def rounds_for(single, difficulty):
    base = BASE_QUESTIONS + DIFF_ROUNDS.get(difficulty, 0)
    if not single:
        base = max(1, int(base * MULTI_MULT))
    return base

def load_image(name):
    path = os.path.join(ASSETS_UI, name)
    try:
        img = tk.PhotoImage(file=path)
        return img
    except Exception:
        return None

def safe_config(widget, **kwargs):
    try:
        if widget and widget.winfo_exists():
            widget.config(**kwargs)
    except Exception:
        pass

def normalize_answer(text):
    if not text:
        return ""
    norm = "".join(ch.lower() if ch.isalnum() or ch.isspace() else " " for ch in text.strip())
    return " ".join(norm.split())

class VoiceLearningApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Voice Learning Platform")
        self.geometry("1280x720")
        self.configure(bg=BG)
        self.resizable(False, False)

        init_db()

        self.lang = current_language()
        self.current_player_id = None
        self.current_player_name = None
        self.current_player_age = None
        self.current_player_avatar = None
        self.session_id = None
        self.session_start_ts = None
        self.total_q = 0
        self.correct_q = 0
        self.current_answer = ""
        self.current_question = ""
        self.current_hint = ""
        self.current_difficulty = "easy"
        self.current_game_type = None
        self.single_mode = True
        self.player1 = None
        self.player2 = None
        self.current_player_turn = 1
        self.rounds_total = BASE_QUESTIONS
        self.round_index = 0
        self.tries_left = TRIES_PER_QUESTION
        self.current_listen_id = None
        self.session_scores = {}
        self._images = {}
        self._load_assets()

        top = tk.Frame(self, bg=HEADER_BG, height=70)
        top.pack(fill="x")
        self.title_label = tk.Label(top, text=t("welcome"), font=TITLE_FONT, bg=HEADER_BG, fg="white")
        self.title_label.pack(side="left", padx=12, pady=8)
        right = tk.Frame(top, bg=HEADER_BG)
        right.pack(side="right", padx=12)
        self.lang_btn = tk.Button(right, text=f"{t('language')}: {current_language().upper()}", command=self.toggle_language)
        self.lang_btn.pack(side="left", padx=6)
        self.test_btn = tk.Button(right, text=t("test_voice"), command=lambda: speak(t("welcome")))
        self.test_btn.pack(side="left", padx=6)

        self.container = tk.Frame(self, bg=BG)
        self.container.pack(fill="both", expand=True)

        self.bind("<space>", self.on_space)

        self.show_login_screen()

    def _load_assets(self):
        for n in ("star.png", "mic.png", "trophy.png", "home.png", "reset.png", "scores.png", "quit.png"):
            img = load_image(n)
            if img:
                self._images[n] = img

    def toggle_language(self):
        new = "ha" if current_language() == "en" else "en"
        set_language(new)
        self.lang = new
        self.lang_btn.config(text=f"{t('language')}: {current_language().upper()}")
        self.show_login_screen()

    def show_login_screen(self):
        for w in self.container.winfo_children():
            w.destroy()
        frame = tk.Frame(self.container, bg=BG)
        frame.pack(expand=True)

        tk.Label(frame, text=t("login"), font=("Comic Sans MS", 24, "bold"), bg=BG).pack(pady=10)

        name_entry = tk.Entry(frame, font=("Segoe UI", 18))
        name_entry.pack(pady=6)
        pin_entry = tk.Entry(frame, font=("Segoe UI", 18), show="*")
        pin_entry.pack(pady=6)

        btn_frame = tk.Frame(frame, bg=BG)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text=t("login"), bg="#6fe7d6", font=BTN_FONT, command=lambda: self.do_login(name_entry.get(), pin_entry.get())).grid(row=0, column=0, padx=10)
        tk.Button(btn_frame, text=t("register"), bg="#ffd86b", font=BTN_FONT, command=self.show_register_screen).grid(row=0, column=1, padx=10)
        tk.Button(btn_frame, text="👤 Guest", bg="#b2f7ef", font=BTN_FONT, command=self.enter_guest_mode).grid(row=0, column=2, padx=10)

    def do_login(self, name, pin):
        name = name.strip()
        if not name:
            messagebox.showinfo(t("login"), t("name_required"))
            return
        player = get_player(name)
        if not player:
            messagebox.showinfo(t("login"), t("name_required"))
            return
        if not verify_pin(name, pin):
            messagebox.showerror(t("login"), t("pin_wrong"))
            return
        self.current_player_id = player["id"]
        self.current_player_name = player["name"]
        self.current_player_age = player["age"]
        self.current_player_avatar = player["avatar"]
        update_last_login(self.current_player_id)
        messagebox.showinfo(t("login"), t("welcome_back").format(name=self.current_player_name))
        self.show_main_menu()

    def show_register_screen(self):
        for w in self.container.winfo_children():
            w.destroy()
        frame = tk.Frame(self.container, bg=BG)
        frame.pack(expand=True)

        tk.Label(frame, text=t("register"), font=("Comic Sans MS", 24, "bold"), bg=BG).pack(pady=10)
        name_entry = tk.Entry(frame, font=("Segoe UI", 18))
        name_entry.pack(pady=6)
        pin_entry = tk.Entry(frame, font=("Segoe UI", 18), show="*")
        pin_entry.pack(pady=6)
        confirm_entry = tk.Entry(frame, font=("Segoe UI", 18), show="*")
        confirm_entry.pack(pady=6)
        age_entry = tk.Entry(frame, font=("Segoe UI", 18))
        age_entry.pack(pady=6)

        tk.Button(frame, text=t("continue"), bg="#6fe7d6", font=BTN_FONT, command=lambda: self.do_register(name_entry.get(), pin_entry.get(), confirm_entry.get(), age_entry.get())).pack(pady=10)
        tk.Button(frame, text=t("back"), bg="#ff9aa2", font=BTN_FONT, command=self.show_login_screen).pack(pady=4)

    def do_register(self, name, pin, confirm_pin, age_text):
        name = name.strip()
        if not name:
            messagebox.showinfo(t("register"), t("name_required"))
            return
        if pin and (len(pin) != 4 or not pin.isdigit()):
            messagebox.showerror(t("register"), t("enter_pin"))
            return
        if pin != confirm_pin:
            messagebox.showerror(t("register"), t("pin_mismatch"))
            return
        age = 0
        if age_text.strip():
            try:
                age = int(age_text)
            except ValueError:
                messagebox.showerror(t("register"), t("enter_age"))
                return
        player_id = create_player(name, pin, age)
        if not player_id:
            messagebox.showerror(t("register"), "Player already exists")
            return
        self.current_player_id = player_id
        self.current_player_name = name
        self.current_player_age = age
        update_last_login(self.current_player_id)
        messagebox.showinfo(t("register"), t("welcome_back").format(name=self.current_player_name))
        self.show_main_menu()

    def enter_guest_mode(self):
        self.current_player_id = None
        self.current_player_name = "Guest"
        self.current_player_age = None
        messagebox.showinfo("Guest", "Playing as Guest")
        self.show_main_menu()

    def show_main_menu(self):
        for w in self.container.winfo_children():
            w.destroy()

        player_info = f"{self.current_player_name or '---'}"
        badge_count = 0
        streak = 0
        if self.current_player_id:
            badges = get_badges(self.current_player_id)
            badge_count = len(badges)
            streak = get_streak(self.current_player_id)

        frame = tk.Frame(self.container, bg=BG)
        frame.pack(expand=True)
        tk.Label(frame, text=t("welcome"), font=TITLE_FONT, bg="#ff6f91", fg="white", width=30, pady=10).pack(pady=8)
        tk.Label(frame, text=f"{player_info} | {t('streak')}: {streak} | {t('achievements')}: {badge_count}", font=("Segoe UI", 14), bg=BG).pack(pady=6)

        btnf = tk.Frame(frame, bg=BG)
        btnf.pack(pady=8)

        def btn(i, text, cmd, bg):
            tk.Button(btnf, text=text, bg=bg, font=BTN_FONT, width=28, height=2, command=cmd).grid(row=i//2, column=i%2, padx=10, pady=8)

        btn(0, t("single_player"), self.enter_single_name, "#ffd86b")
        btn(1, t("multiplayer"), self.enter_multi_names, "#9ad0f5")
        btn(2, t("sentence_game"), self.enter_sentence_mode, "#b2f7ef")
        btn(3, t("leaderboard"), self.show_scores, "#9ad0f5")
        btn(4, t("achievements"), self.show_achievements, "#6fe7d6")
        btn(5, t("view_scores"), self.show_analytics_dashboard, "#ffd86b")

        tk.Button(frame, text=t("reset_scores"), bg="#ff9aa2", font=BTN_FONT, command=self.reset_scores_confirm).pack(pady=4)
        tk.Button(frame, text=t("quit"), bg="#ffb703", font=BTN_FONT, command=self.quit).pack(pady=4)
        tk.Button(frame, text="Logout", bg="#cc5500", fg="white", font=BTN_FONT, command=self.show_login_screen).pack(pady=4)

    def enter_single_name(self):
        for w in self.container.winfo_children():
            w.destroy()
        frame = tk.Frame(self.container, bg=BG)
        frame.pack(expand=True)
        tk.Label(frame, text=t("enter_name"), font=("Segoe UI", 20), bg=BG).pack(pady=12)
        name_entry = tk.Entry(frame, font=("Segoe UI", 16))
        name_entry.pack(pady=4)
        if self.current_player_name and self.current_player_name != "Guest":
            name_entry.insert(0, self.current_player_name)
        tk.Button(frame, text=t("continue"), bg="#6fe7d6", font=BTN_FONT, command=lambda: self.start_single(name_entry.get().strip())).pack(pady=10)
        tk.Button(frame, text=t("back"), bg="#ff9aa2", command=self.show_main_menu).pack(pady=6)

    def start_single(self, name):
        if not name:
            messagebox.showinfo(t("Info"), t("name_required"))
            return
        self.player1 = name
        self.single_mode = True
        self.session_scores = {name: 0}
        self.choose_game_mode()

    def enter_multi_names(self):
        for w in self.container.winfo_children():
            w.destroy()
        frame = tk.Frame(self.container, bg=BG)
        frame.pack(expand=True)
        tk.Label(frame, text=t("enter_name_p1"), font=("Segoe UI", 18), bg=BG).pack(pady=6)
        p1_entry = tk.Entry(frame, font=("Segoe UI", 16))
        p1_entry.pack(pady=6)
        tk.Label(frame, text=t("enter_name_p2"), font=("Segoe UI", 18), bg, etc...
