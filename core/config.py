# core/config.py
# Author: Emsii (refactored)
# Jedyne miejsce w aplikacji które czyta/pisze config.json.
# Reszta kodu używa AppState — nigdy bezpośrednio pliku.

import json
import os
import threading
import logging
from typing import Any
from pathlib import Path

logger = logging.getLogger(__name__)

_write_lock = threading.Lock()   # tylko jeden wątek pisze na raz

BASE_DIR = Path(__file__).parent.parent
CONFIG_FILE = BASE_DIR / "config.json"

CONFIG_DEFAULTS = {
    "api_key": "",
    "base_url": "http://api.openweathermap.org/data/2.5/weather?",
    "localization_url": "http://ipinfo.io/json",
    "city": "",
    "temp_outside": "",
    "current_pressure": "",
    "current_humidity": "",
    "info_weather": "",
    "IP_query": "",
    "IP_home": "",
    "color": 0,
    "brightness": 0.5,
    "effects": 0,
    "leds_speed": 1.0,
    "hour_start_LCD": 8,
    "hour_stop_LCD": 22,
    "time_update": "",
}


def load() -> dict:
    """Wczytaj config.json. Zwraca defaults jeśli plik nie istnieje."""
    if not CONFIG_FILE.exists():
        logger.warning("config.json not found, using defaults")
        return CONFIG_DEFAULTS.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"Config loaded from {CONFIG_FILE}")
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Config JSON parse error: {e} — using defaults")
        return CONFIG_DEFAULTS.copy()


def save(data: dict) -> bool:
    """
    Zapisz cały słownik do config.json.
    Thread-safe — używa locka. Zwraca True przy sukcesie.
    """
    with _write_lock:
        try:
            tmp_file = CONFIG_FILE.with_suffix(".json.tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            # Atomowe zastąpienie — unikamy częściowo zapisanego pliku
            os.replace(tmp_file, CONFIG_FILE)
            logger.debug("Config saved")
            return True
        except Exception:
            logger.exception("Failed to save config")
            return False


def patch(updates: dict) -> bool:
    """
    Zaktualizuj tylko podane klucze w config.json.
    Bezpieczne przy równoległych wywołaniach.
    """
    with _write_lock:
        try:
            current = load()
            current.update(updates)
            return save(current)
        except Exception:
            logger.exception("Failed to patch config")
            return False


def initialize(api_key: "str | None" = None) -> dict:
    """
    Upewnij się że config.json istnieje.
    Przy pierwszym uruchomieniu pyta o api_key jeśli nie podano.
    """
    if CONFIG_FILE.exists():
        return load()

    logger.info("First run — creating config.json")
    data = CONFIG_DEFAULTS.copy()
    data["api_key"] = api_key or input(
        "Podaj api_key z https://home.openweathermap.org/api_keys:\n> "
    ).strip()
    save(data)
    return data
