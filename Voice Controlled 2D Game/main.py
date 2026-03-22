# main.py
import tkinter as tk
from tkinter import messagebox, simpledialog
import uuid
import random
import os

from translations import t, set_language, current_language
from utils.storage import load_progress, add_single_score, add_multi_match, delete_pair, reset_progress
from utils.voice import listen_async, ERR_NO_MIC, ERR_NO_SPEECH, ERR_NO_INTERNET
from utils.tts import speak

ASSETS_UI = os.path.join(os.path.dirname(__file__), "assets", "images", "ui")

def load_image(name):
    path = os.path.join(ASSETS_UI, name)
    try:
        img = tk.PhotoImage(file=path)
        return img
    except Exception:
        return None

# Theme
BG = "#fff9e6"
HEADER_BG = "#ff6f91"
BTN_FONT = ("Comic Sans MS", 14, "bold")
TITLE_FONT = ("Comic Sans MS", 26, "bold")
TRIES_PER_QUESTIONS = 2
BASE_QUESTIONS = 10
DIFF_ROUNDS = {"easy": 0, "medium": 2, "hard": 5}
MULTI_MULT = 1.2

def rounds_for(single, difficulty):
    base = BASE_QUESTIONS + DIFF_ROUNDS.get(difficulty, 0)
    if not single:
        base = max(1, int(base * MULTI_MULT))
    return base

def safe_config(widget, **kwargs):
    try:
        if widget and widget.winfo_exists():
            widget.config(**kwargs)
    except Exception:
        pass

class VoiceLearningApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Voice Learning Game")
        self.geometry("1280x720")
        self.configure(bg=BG)
        self.resizable(False, False)

        # statelite
        self.lang = current_language()
        self.player_single = None
        self.player1 = None
        self.player2 = None
        self.single_mode = True
        self.game_type = None
        self.difficulty = "easy"
        self.rounds_total = BASE_QUESTIONS
        self.round_index = 0
        self.tries_left = TRIES_PER_QUESTIONS
        self.current_answer = ""
        self.current_listen_id = None
        self.session_scores = {}
        self.current_player_turn = 1
        self._images = {}

        for n in ("star.png", "mic.png", "trophy.png", "home.png", "reset.png", "scores.png", "quit.png"):
            img = load_image(n)
            if img:
                self._images[n] = img

        # topbar
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

        # container
        self.container = tk.Frame(self, bg=BG)
        self.container.pack(fill="both", expand=True)

        self.bind("<space>", self.on_space)

        self.show_main_menu()

    def show_main_menu(self):
        self.title_label.config(text=t("welcome"))
        self.lang_btn.config(text=f"{t('language')}: {current_language().upper()}")

        for w in self.container.winfo_children():
            w.destroy()
        frame = tk.Frame(self.container, bg=BG)
        frame.pack(expand=True)
        title_card = tk.Label(frame, text=t("welcome"), font=TITLE_FONT, bg="#ff6f91", fg="white", width=40, pady=12)
        title_card.pack(pady=20)

        btnf = tk.Frame(frame, bg=BG)
        btnf.pack(pady=8)
        def make_btn(key, cmd, bg="#6fe7d6", imgname=None):
            img = self._images.get(imgname) if imgname else None
            if img:
                b = tk.Button(btnf, text=t(key), image=img, compound="left", command=cmd, font=BTN_FONT, bg=bg, width=320, height=70, anchor="w")
                b.image = img
            else:
                b = tk.Button(btnf, text=t(key), command=cmd, font=BTN_FONT, bg=bg, width=28, height=2)
            return b
        make_btn("single_player", self.enter_single_name, bg="#ffd86b", imgname="star.png").grid(row=0, column=0, padx=10, pady=8)
        make_btn("multiplayer", self.enter_multi_names, bg="#9ad0f5", imgname="trophy.png").grid(row=0, column=1, padx=10, pady=8)
        make_btn("view_scores", self.show_scores, bg="#b2f7ef", imgname="scores.png").grid(row=1, column=0, padx=10, pady=8)
        make_btn("reset_scores", self.reset_scores_confirm, bg="#ff9aa2", imgname="reset.png").grid(row=1, column=1, padx=10, pady=8)
        make_btn("quit", self.quit, bg="#ffb703", imgname="quit.png").grid(row=2, column=0, columnspan=2, pady=14)

    def toggle_language(self):
        new = "ha" if current_language() == "en" else "en"
        set_language(new)
        self.lang = new
        self.lang_btn.config(text=f"{t('language')}: {current_language().upper()}")
        self.show_main_menu()

    def enter_single_name(self):
        for w in self.container.winfo_children():
            w.destroy()
        f = tk.Frame(self.container, bg=BG)
        f.pack(expand=True)
        tk.Label(f, text=t("enter_name"), font=("Segoe UI", 20), bg=BG).pack(pady=12)
        e = tk.Entry(f, font=("Segoe UI", 16))
        e.pack(pady=8)
        tk.Button(f, text=t("continue"), bg="#6fe7d6", font=BTN_FONT, command=lambda: self.start_single(e.get())).pack(pady=10)
        tk.Button(f, text=t("back"), bg="#ff9aa2", command=self.show_main_menu).pack(pady=6)

    def start_single(self, name):
        if not name.strip():
            messagebox.showinfo("Info", t("name_required"))
            return
        self.player_single = name.strip()
        self.single_mode = True
        self.session_scores = {self.player_single: 0}
        self.choose_game_mode()

    def enter_multi_names(self):
        for w in self.container.winfo_children():
            w.destroy()
        f = tk.Frame(self.container, bg=BG)
        f.pack(expand=True)
        tk.Label(f, text=t("enter_name_p1"), font=("Segoe UI", 16), bg=BG).pack(pady=6)
        p1 = tk.Entry(f, font=("Segoe UI", 14)); p1.pack(pady=6)
        tk.Label(f, text=t("enter_name_p2"), font=("Segoe UI", 16), bg=BG).pack(pady=6)
        p2 = tk.Entry(f, font=("Segoe UI", 14)); p2.pack(pady=6)
        tk.Button(f, text=t("continue"), bg="#ffd86b", font=BTN_FONT, command=lambda: self.start_multi(p1.get(), p2.get())).pack(pady=10)
        tk.Button(f, text=t("back"), bg="#ff9aa2", command=self.show_main_menu).pack(pady=6)

    def start_multi(self, n1, n2):
        if not n1.strip() or not n2.strip():
            messagebox.showinfo("Info", t("name_required"))
            return
        self.player1 = n1.strip(); self.player2 = n2.strip()
        self.single_mode = False
        self.session_scores = {"player1": 0, "player2": 0}
        self.current_player_turn = 1
        self.choose_game_mode()

    def choose_game_mode(self):
        for w in self.container.winfo_children(): w.destroy()
        f = tk.Frame(self.container, bg=BG); f.pack(expand=True)
        tk.Label(f, text=t("choose_game_mode"), font=("Comic Sans MS", 22, "bold"), bg=BG).pack(pady=12)
        bf = tk.Frame(f, bg=BG); bf.pack(pady=8)
        tk.Button(bf, text=t("alphabet_game"), bg="#ff9aa2", font=BTN_FONT, width=22, command=lambda: self.choose_difficulty("alphabet")).grid(row=0, column=0, padx=10, pady=6)
        tk.Button(bf, text=t("number_game"), bg="#6fe7d6", font=BTN_FONT, width=22, command=lambda: self.choose_difficulty("numbers")).grid(row=0, column=1, padx=10, pady=6)
        tk.Button(bf, text=t("math_game"), bg="#9ad0f5", font=BTN_FONT, width=22, command=lambda: self.choose_difficulty("math")).grid(row=0, column=2, padx=10, pady=6)
        tk.Button(f, text=t("back"), bg="#ffd86b", command=self.show_main_menu).pack(pady=14)

    def choose_difficulty(self, game_type):
        self.game_type = game_type
        for w in self.container.winfo_children(): w.destroy()
        f = tk.Frame(self.container, bg=BG); f.pack(expand=True)
        tk.Label(f, text=t("choose_difficulty"), font=("Comic Sans MS", 20), bg=BG).pack(pady=12)
        bf = tk.Frame(f, bg=BG); bf.pack(pady=8)
        tk.Button(bf, text=t("easy"), bg="#b2f7ef", font=BTN_FONT, width=18, command=lambda: self.start_game("easy")).grid(row=0, column=0, padx=8, pady=6)
        tk.Button(bf, text=t("medium"), bg="#ffe4a3", font=BTN_FONT, width=18, command=lambda: self.start_game("medium")).grid(row=0, column=1, padx=8, pady=6)
        tk.Button(bf, text=t("hard"), bg="#ffb3c1", font=BTN_FONT, width=18, command=lambda: self.start_game("hard")).grid(row=0, column=2, padx=8, pady=6)
        tk.Button(f, text=t("back"), bg="#ffd86b", command=self.choose_game_mode).pack(pady=14)

    def start_game(self, difficulty):
        self.difficulty = difficulty
        self.rounds_total = rounds_for(self.single_mode, difficulty)
        self.round_index = 0
        self.tries_left = TRIES_PER_QUESTIONS
        if self.single_mode:
            self.session_scores = {self.player_single: 0}
        else:
            self.session_scores = {"player1": 0, "player2": 0}
            self.current_player_turn = 1
        self.show_round_screen()

    def show_round_screen(self):
        for w in self.container.winfo_children(): w.destroy()
        frame = tk.Frame(self.container, bg=BG); frame.pack(fill="both", expand=True)
        header = f"{t(self.game_type+'_game') if self.game_type else ''} — {t(self.difficulty)}"
        tk.Label(frame, text=header, font=("Segoe UI", 20, "bold"), bg=BG).pack(pady=10)
        self.round_label = tk.Label(frame, text=f"{t('question')} {self.round_index+1} / {self.rounds_total}", font=("Segoe UI", 14), bg=BG); self.round_label.pack(pady=6)
        self.prompt_label = tk.Label(frame, text="", font=("Segoe UI", 36, "bold"), bg=BG, fg="#333"); self.prompt_label.pack(pady=12)
        self.tries_label = tk.Label(frame, text=t("tries_left").format(tries=self.tries_left), font=("Segoe UI", 14), bg=BG); self.tries_label.pack(pady=6)
        self.feedback_label = tk.Label(frame, text="", font=("Segoe UI", 14), bg=BG); self.feedback_label.pack(pady=6)
        self.objects_frame = tk.Frame(frame, bg=BG); self.objects_frame.pack(pady=8)
        control_frame = tk.Frame(frame, bg=BG); control_frame.pack(pady=12)
        mic_img = self._images.get("mic.png")
        if mic_img:
            self.speak_btn = tk.Button(control_frame, text=t("speak"), image=mic_img, compound="left", font=BTN_FONT, bg="#ffd86b", command=self.on_speak); self.speak_btn.image = mic_img
        else:
            self.speak_btn = tk.Button(control_frame, text=t("speak"), font=BTN_FONT, bg="#ffd86b", command=self.on_speak)
        self.speak_btn.pack(side="left", padx=8)
        tk.Button(control_frame, text=t("play_again"), bg="#9ad0f5", font=BTN_FONT, command=self.retry_round).pack(side="left", padx=8)
        tk.Button(control_frame, text=t("back"), bg="#ff9aa2", font=BTN_FONT, command=self.show_main_menu).pack(side="left", padx=8)
        score_frame = tk.Frame(frame, bg=BG); score_frame.pack(pady=8)
        if self.single_mode:
            self.score_label = tk.Label(score_frame, text=f"{self.player_single}: {self.session_scores.get(self.player_single,0)} pts", font=("Segoe UI", 15, "bold"), bg=BG, fg="#333")
            self.score_label.pack()
        else:
            self.score_label = tk.Label(score_frame, text=f"{self.player1}: {self.session_scores['player1']}  |  {self.player2}: {self.session_scores['player2']}", font=("Segoe UI", 15, "bold"), bg=BG, fg="#333")
            self.score_label.pack()
        self.tries_left = TRIES_PER_QUESTIONS
        self.tries_label.config(text=t("tries_left").format(tries=self.tries_left))
        self.generate_question()

    def retry_round(self):
        self.tries_left = TRIES_PER_QUESTIONS
        self.tries_label.config(text=t("tries_left").format(tries=self.tries_left))
        self.feedback_label.config(text="")
        self.generate_question()

    def generate_question(self):
        for w in self.objects_frame.winfo_children(): w.destroy()
        gm = self.game_type; d = self.difficulty
        if gm == "alphabet":
            if d == "easy": pool = list("abcde")
            elif d == "medium": pool = list("abcdefghijklm")
            else: pool = list("abcdefghijklmnopqrstuvwxyz")
            chosen = random.choice(pool); self.current_answer = chosen.lower(); display = chosen.upper()
            if not self.single_mode:
                playername = self.player1 if self.current_player_turn==1 else self.player2
                self.prompt_label.config(text=f"{playername}: {display}")
                speak(f"{playername}, {t('say_letter')} {display}")
            else:
                self.prompt_label.config(text=f"{t('say_letter')} {display}"); speak(f"{t('say_letter')} ")
        elif gm == "numbers":
            if d == "easy": n = random.randint(1,5)
            elif d == "medium": n = random.randint(1,10)
            else: n = random.randint(1,20)
            self.current_answer = str(n)
            for i in range(n):
                c = tk.Canvas(self.objects_frame, width=36, height=36, bg=BG, highlightthickness=0); c.grid(row=i//10, column=i%10, padx=3, pady=3); c.create_oval(4,4,32,32, fill="#ffd86b", outline="#ffb703")
            if not self.single_mode:
                playername = self.player1 if self.current_player_turn==1 else self.player2
                self.prompt_label.config(text=f"{playername}: {t('say_number')} {n}"); speak(f"{playername}, {t('say_number')} {n}")
            else:
                self.prompt_label.config(text=f"{t('say_number')} {n}"); speak(f"{t('say_number')} ")
        else: #math game
            if d == "easy":
                a,b = random.randint(1,10), random.randint(1,10); self.current_answer = str(a+b); qtext = f"{a} + {b} = ?"; speak_text = f"{t('say_sum')} {a} plus {b}"
            elif d == "medium":
                a,b = random.randint(1,20), random.randint(1,20)
                if random.choice([True,False]):
                    self.current_answer = str(a+b); qtext = f"{a} + {b} = ?"; speak_text = f"{t('say_sum')} {a} plus {b}"
                else:
                    self.current_answer = str(a-b); qtext = f"{a} - {b} = ?"; speak_text = f"{t('say_sum')} {a} minus {b}"
            else:
                a,b = random.randint(1,50), random.randint(1,50); op = random.choice(["+","-","*"])
                if op=="+": self.current_answer=str(a+b); qtext=f"{a} + {b} = ?"; speak_text=f"{t('say_sum')} {a} plus {b}"
                elif op=="-": self.current_answer=str(a-b); qtext=f"{a} - {b} = ?"; speak_text=f"{t('say_sum')} {a} minus {b}"
                else: self.current_answer=str(a*b); qtext=f"{a} × {b} = ?"; speak_text=f"{t('say_sum')} {a} times {b}"
            if not self.single_mode:
                playername = self.player1 if self.current_player_turn==1 else self.player2
                self.prompt_label.config(text=f"{playername}: {qtext}"); speak(f"{playername}, {speak_text}")
            else:
                self.prompt_label.config(text=qtext); speak(speak_text)
        self.tries_left = TRIES_PER_QUESTIONS
        self.tries_label.config(text=t("tries_left").format(tries=self.tries_left))
        self.feedback_label.config(text="")
        if hasattr(self, "round_label") and self.round_label.winfo_exists():
            self.round_label.config(text=f"{t('question')} {self.round_index+1} / {self.rounds_total}")
    def on_speak(self):
        if not hasattr(self, "speak_btn") or not self.speak_btn.winfo_exists():
            return
        listen_id = uuid.uuid4().hex
        self.current_listen_id = listen_id
        safe_config(self.speak_btn, state="disabled", text=t("listening"))
        safe_config(self.feedback_label, text="🎙 " + t("listening"), fg="#0077cc")
        lang_hint = "ha" if current_language() == "ha" else "en"
        listen_async(self._on_listen_result, listen_id=listen_id, timeout=6, phrase_time_limit=5, lang_hint=lang_hint)

    def on_space(self, event):
        if hasattr(self, "speak_btn") and self.speak_btn and self.speak_btn.winfo_exists():
            self.on_speak()

    def _on_listen_result(self, listen_id, result_text):
        def _proc():
            if listen_id != self.current_listen_id:
                return
            safe_config(self.speak_btn, state="normal", text=t("speak"))
            safe_config(self.feedback_label, fg="#333")
            if result_text == ERR_NO_MIC:
                safe_config(self.feedback_label, text="⚠️ No microphone found. Check your mic and try again.", fg="#cc0000")
                return
            if result_text == ERR_NO_INTERNET:
                safe_config(self.feedback_label, text="⚠️ No internet connection for speech recognition.", fg="#cc0000")
                return
            if result_text == ERR_NO_SPEECH:
                safe_config(self.feedback_label, text="🔇 Nothing heard — speak louder and try again.", fg="#cc6600")
                return
            self.process_voice_result(result_text)
        self.after(50, _proc)

    def process_voice_result(self, result_text):
        rt = (result_text or "").strip().lower()
        # Show what was heard so user can see if mic picked them up
        heard_display = result_text.strip() if result_text else ""
        if not rt:
            safe_config(self.feedback_label, text=t("incorrect_try"))
            return
        ans = str(self.current_answer).lower()
        ok = False
        if self.game_type == "alphabet":
            # Accept: exact match, or any token that IS the letter
            tokens = rt.replace(".", " ").replace(",", " ").split()
            ok = (rt == ans) or (ans in tokens)
        else:
            # Numbers / math: accept if the answer appears as a word token
            tokens = rt.replace(",", " ").split()
            ok = any(tok == ans for tok in tokens)
        if ok:
            if self.single_mode:
                self.session_scores[self.player_single] = self.session_scores.get(self.player_single, 0) + 1
            else:
                key = "player1" if self.current_player_turn == 1 else "player2"
                self.session_scores[key] += 1
            self._refresh_score()
            safe_config(self.feedback_label, text=t("correct").format(ans=self.current_answer))
            speak(t("correct").format(ans=self.current_answer))
            self.advance_after_answer(correct=True)
        else:
            self.tries_left -= 1
            heard_msg = f"  (heard: '{heard_display}')"
            if self.tries_left > 0:
                safe_config(self.feedback_label, text=t("incorrect_try") + heard_msg)
                self.tries_label.config(text=t("tries_left").format(tries=self.tries_left))
                speak(t("incorrect_try"))
            else:
                safe_config(self.feedback_label, text=t("incorrect_move").format(ans=self.current_answer) + heard_msg)
                speak(t("incorrect_move").format(ans=self.current_answer))
                self.advance_after_answer(correct=False)

    def _refresh_score(self):
        if not hasattr(self, "score_label") or not self.score_label.winfo_exists():
            return
        if self.single_mode:
            self.score_label.config(text=f"{self.player_single}: {self.session_scores.get(self.player_single, 0)} pts")
        else:
            self.score_label.config(text=f"{self.player1}: {self.session_scores['player1']}  |  {self.player2}: {self.session_scores['player2']}")

    def advance_after_answer(self, correct):
        if self.single_mode:
            add_single_score(self.player_single, self.session_scores[self.player_single])
            self.round_index += 1
            if self.round_index >= self.rounds_total:
                self.finish_round_single()
            else:
                self.after(700, self.generate_question)
        else:
            if self.current_player_turn == 1:
                self.current_player_turn = 2
                self.tries_left = TRIES_PER_QUESTIONS
                self.tries_label.config(text=t("tries_left").format(tries=self.tries_left))
                self.generate_question()
            else:
                self.round_index += 1
                self.current_player_turn = 1
                if self.round_index >= self.rounds_total:
                    self.finish_round_multi()
                else:
                    self.tries_left = TRIES_PER_QUESTIONS
                    self.after(700, self.generate_question)

    def finish_round_single(self):
        for w in self.container.winfo_children(): w.destroy()
        score = self.session_scores.get(self.player_single, 0)
        f = tk.Frame(self.container, bg=BG); f.pack(expand=True)
        tk.Label(f, text=t("game_over"), font=("Comic Sans MS", 22, "bold"), bg=BG).pack(pady=8)
        tk.Label(f, text=t("round_finished_single").format(player=self.player_single, score=score), font=("Segoe UI", 16), bg=BG).pack(pady=6)
        stars = score // 5; tk.Label(f, text="⭐" * stars, font=("Segoe UI", 28), bg=BG).pack(pady=6)
        tk.Button(f, text=t("play_again"), bg="#6fe7d6", font=BTN_FONT, command=lambda: self.start_game(self.difficulty)).pack(pady=6)
        tk.Button(f, text=t("back"), bg="#ff9aa2", font=BTN_FONT, command=self.show_main_menu).pack(pady=6)

    def finish_round_multi(self):
        for w in self.container.winfo_children(): w.destroy()
        f = tk.Frame(self.container, bg=BG); f.pack(expand=True)
        p1score = self.session_scores.get("player1",0); p2score = self.session_scores.get("player2",0)
        tk.Label(f, text=t("game_over"), font=("Comic Sans MS", 22, "bold"), bg=BG).pack(pady=8)
        tk.Label(f, text=t("round_finished_multi").format(p1=self.player1, s1=p1score, p2=self.player2, s2=p2score), font=("Segoe UI", 16), bg=BG).pack(pady=6)
        if p1score > p2score: winner = self.player1
        elif p2score > p1score: winner = self.player2
        else: winner = t("tie")
        tk.Label(f, text=t("match_finished").format(winner=winner), font=("Segoe UI", 18, "bold"), bg=BG).pack(pady=8)
        add_multi_match(self.player1, self.player2, p1score, p2score, winner)
        tk.Button(f, text=t("play_again"), bg="#ffd86b", font=BTN_FONT, command=lambda: self.start_game(self.difficulty)).pack(pady=6)
        tk.Button(f, text=t("back"), bg="#ff9aa2", font=BTN_FONT, command=self.show_main_menu).pack(pady=6)

    def show_scores(self):
        for w in self.container.winfo_children(): w.destroy()
        data = load_progress()
        f = tk.Frame(self.container, bg=BG); f.pack(fill="both", expand=True, padx=12, pady=12)
        tk.Label(f, text=t("view_scores"), font=("Comic Sans MS", 20, "bold"), bg=BG).pack(pady=8)
        tk.Label(f, text=t("single_player"), font=("Segoe UI", 16, "underline"), bg=BG).pack(pady=6)
        single = data.get("single", {})
        if single:
            for name, pts in single.items():
                sf = tk.Frame(f, bg=BG); sf.pack(fill="x", padx=24, pady=4)
                tk.Label(sf, text=name, width=20, anchor="w", bg=BG).pack(side="left")
                tk.Label(sf, text=f"{pts} pts", bg=BG).pack(side="left")
                stars = "⭐" * (pts // 5); tk.Label(sf, text=stars, bg=BG).pack(side="left", padx=8)
        else:
            tk.Label(f, text=t("no_scores"), bg=BG).pack()
        tk.Label(f, text=t("multiplayer"), font=("Segoe UI", 16, "underline"), bg=BG).pack(pady=10)
        multi = data.get("multi", {})
        if multi:
            for match_key, hist in multi.items():
                mf = tk.Frame(f, bg=BG, bd=1, relief="solid"); mf.pack(fill="x", padx=16, pady=6)
                tk.Label(mf, text=match_key, font=("Segoe UI", 14, "bold"), bg=BG).pack(anchor="w", padx=8, pady=4)
                if isinstance(hist, list):
                    for entry in hist[-10:]:
                        tk.Label(mf, text=entry, font=("Segoe UI", 12), bg=BG).pack(anchor="w", padx=12)
                else:
                    tk.Label(mf, text=str(hist), font=("Segoe UI", 12), bg=BG).pack(anchor="w", padx=12)
                tk.Button(mf, text=t("delete_match"), bg="#d62828", fg="white", command=lambda k=match_key: self.confirm_delete_pair(k)).pack(anchor="e", padx=8, pady=6)
        else:
            tk.Label(f, text=t("no_scores"), bg=BG).pack()
        btnf = tk.Frame(f, bg=BG); btnf.pack(pady=12)
        tk.Button(btnf, text=t("reset_scores"), bg="#ff9aa2", command=self.reset_scores_confirm).pack(side="left", padx=8)
        tk.Button(btnf, text=t("back"), bg="#6fe7d6", command=self.show_main_menu).pack(side="left", padx=8)

    def confirm_delete_pair(self, match_key):
        if messagebox.askyesno(t("delete_match"), t("confirm_delete")):
            ok = delete_pair(match_key)
            if ok:
                messagebox.showinfo(t("delete_match"), t("pair_deleted"))
                self.show_scores()
            else:
                messagebox.showinfo("Info", t("no_pairs"))

    def reset_scores_confirm(self):
        if messagebox.askyesno(t("reset_scores"), t("confirm_reset")):
            reset_progress()
            messagebox.showinfo(t("reset_scores"), t("scores_reset"))
            self.show_main_menu()

if __name__ == "__main__":
    app = VoiceLearningApp()
    app.mainloop()
