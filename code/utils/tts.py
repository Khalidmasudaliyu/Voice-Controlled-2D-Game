# utils/tts.py
import threading
import tempfile
import os
import logging

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    from gtts import gTTS
    from playsound import playsound
except ImportError:
    gTTS = None
    playsound = None

from translations import current_language

# Each thread gets its own pyttsx3 engine to avoid cross-thread crashes
_thread_local = threading.local()
_speak_lock = threading.Lock()  # only one TTS at a time

def _get_engine():
    if not pyttsx3:
        return None
    if not getattr(_thread_local, "engine", None):
        try:
            engine = pyttsx3.init()
            rate = engine.getProperty("rate")
            engine.setProperty("rate", max(130, rate - 30))
            _thread_local.engine = engine
        except Exception as e:
            logging.warning("pyttsx3 init failed: %s", e)
            _thread_local.engine = None
    return _thread_local.engine

def speak(text):
    """Non-blocking TTS."""
    lang = current_language()
    def worker():
        with _speak_lock:
            engine = _get_engine()
            if engine:
                try:
                    voices = engine.getProperty("voices")
                    for v in voices:
                        name = (v.name or "").lower()
                        if lang == "en" and "english" in name:
                            engine.setProperty("voice", v.id)
                            break
                    engine.say(text)
                    engine.runAndWait()
                    return
                except Exception as e:
                    logging.warning("pyttsx3 speak failed: %s", e)
                    _thread_local.engine = None  # reset so next call retries
            if lang == "ha" and gTTS and playsound:
                try:
                    fd, path = tempfile.mkstemp(suffix=".mp3")
                    os.close(fd)
                    gTTS(text=text, lang="ha").save(path)
                    playsound(path)
                    os.remove(path)
                    return
                except Exception as e:
                    logging.warning("gTTS speak failed: %s", e)
            print("[TTS]", text)
    threading.Thread(target=worker, daemon=True).start()
