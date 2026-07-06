"""
VenvStudio - Internationalization (i18n) System
Supports: en, tr, de, fr, es, pt, ru, zh, ja, ko, ar

Translation data lives in src/utils/i18n_data/<lang>.py (one dict per
language). This module keeps the public API (tr / set_language /
get_language) and assembles the combined TRANSLATIONS dict from them.
"""

from src.utils.i18n_data.en import TRANSLATIONS as _EN
from src.utils.i18n_data.tr import TRANSLATIONS as _TR
from src.utils.i18n_data.de import TRANSLATIONS as _DE
from src.utils.i18n_data.fr import TRANSLATIONS as _FR
from src.utils.i18n_data.es import TRANSLATIONS as _ES
from src.utils.i18n_data.pt import TRANSLATIONS as _PT
from src.utils.i18n_data.ru import TRANSLATIONS as _RU
from src.utils.i18n_data.zh import TRANSLATIONS as _ZH
from src.utils.i18n_data.ja import TRANSLATIONS as _JA
from src.utils.i18n_data.ko import TRANSLATIONS as _KO
from src.utils.i18n_data.ar import TRANSLATIONS as _AR

_current_lang = "en"


def set_language(lang_code: str):
    global _current_lang
    _current_lang = lang_code


def get_language() -> str:
    return _current_lang


TRANSLATIONS = {
    "en": _EN,
    "tr": _TR,
    "de": _DE,
    "fr": _FR,
    "es": _ES,
    "pt": _PT,
    "ru": _RU,
    "zh": _ZH,
    "ja": _JA,
    "ko": _KO,
    "ar": _AR,
}


def tr(key: str) -> str:
    """Translate a key to the current language. Falls back to English."""
    lang_dict = TRANSLATIONS.get(_current_lang, TRANSLATIONS["en"])
    return lang_dict.get(key, TRANSLATIONS["en"].get(key, key))
