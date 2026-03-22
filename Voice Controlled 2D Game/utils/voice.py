# utils/voice.py
import speech_recognition as sr
import threading
import logging

_recognizer = sr.Recognizer()
_recognizer.energy_threshold = 300
_recognizer.dynamic_energy_threshold = True

ERR_NO_MIC = "__NO_MIC__"
ERR_NO_SPEECH = "__NO_SPEECH__"
ERR_NO_INTERNET = "__NO_INTERNET__"

def _recognize_blocking(timeout=5, phrase_time_limit=5, lang_hint=None):
    try:
        with sr.Microphone() as source:
            _recognizer.adjust_for_ambient_noise(source, duration=0.1)
            audio = _recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
    except (OSError, AttributeError):
        return ERR_NO_MIC
    except sr.WaitTimeoutError:
        return ERR_NO_SPEECH
    try:
        lang = "ha" if (lang_hint and lang_hint.startswith("ha")) else "en-US"
        return _recognizer.recognize_google(audio, language=lang)
    except sr.UnknownValueError:
        return ERR_NO_SPEECH
    except (sr.RequestError, Exception) as e:
        logging.warning("Speech recognition failed: %s", e)
        return ERR_NO_INTERNET

def listen_async(callback, listen_id=None, timeout=5, phrase_time_limit=5, lang_hint=None):
    """Recognize in background and call callback(listen_id, recognized_text)."""
    def worker():
        try:
            res = _recognize_blocking(timeout=timeout, phrase_time_limit=phrase_time_limit, lang_hint=lang_hint)
        except Exception as e:
            logging.warning("listen_async worker crashed: %s", e)
            res = ERR_NO_SPEECH
        callback(listen_id, res)
    threading.Thread(target=worker, daemon=True).start()
