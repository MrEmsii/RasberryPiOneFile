# core/state.py
# Author: Emsii (refactored)
# Centralny stan aplikacji — zastępuje bezpośrednie odczyty config.json między wątkami.
#
# Jeden obiekt AppState przechowuje aktualny stan w pamięci.
# config.json jest używany tylko do: startu (wczytanie) i persystencji (zapis przez handler).
# Wątki nigdy nie piszą do pliku bezpośrednio — emitują zdarzenia.

import threading
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class WeatherData:
    city: str = ""
    temp_outside: str = ""
    current_pressure: str = ""
    current_humidity: str = ""
    info_weather: str = ""
    time_update: str = ""
    ip_query: str = ""


@dataclass
class NetworkData:
    ip_home: str = "..."
    ip_query: str = "..."


@dataclass
class LEDConfig:
    color: int = 0          # 0 = wyłączone, 1-10 = kolory
    brightness: float = 0.5
    effects: int = 0        # 0 = off, 1-4 = efekty
    leds_speed: float = 1.0


@dataclass
class TemperatureData:
    indoor: Optional[float] = None
    outdoor: Optional[float] = None


class AppState:
    """
    Thread-safe centralny stan aplikacji.

    Używaj:
        state.leds.color = 3          ← NIE (brak locka)
        state.update_leds(color=3)    ← TAK
        val = state.leds.color        ← TAK (odczyt jest atomowy dla prostych typów)
    """

    def __init__(self):
        self._lock = threading.RLock()  # RLock — ten sam wątek może wejść wielokrotnie

        self.leds = LEDConfig()
        self.weather = WeatherData()
        self.network = NetworkData()
        self.temperature = TemperatureData()

        # Konfiguracja statyczna (wczytana ze startu, nie zmienia się w runtime)
        self.api_key: str = ""
        self.base_url: str = ""
        self.localization_url: str = ""
        self.hour_start_lcd: int = 8
        self.hour_stop_lcd: int = 22

    # ── LED ──────────────────────────────────

    def update_leds(self, **kwargs) -> None:
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self.leds, key):
                    setattr(self.leds, key, value)
                    logger.debug(f"State.leds.{key} = {value}")
                else:
                    logger.warning(f"Unknown LED field: {key}")

    def get_leds(self) -> LEDConfig:
        with self._lock:
            # Zwróć kopię żeby uniknąć race condition przy odczycie wielu pól
            return LEDConfig(
                color=self.leds.color,
                brightness=self.leds.brightness,
                effects=self.leds.effects,
                leds_speed=self.leds.leds_speed,
            )

    # ── Temperatura ───────────────────────────

    def update_temperature(self, indoor: Optional[float] = None, outdoor: Optional[float] = None) -> None:
        with self._lock:
            if indoor is not None:
                self.temperature.indoor = indoor
            if outdoor is not None:
                self.temperature.outdoor = outdoor

    def get_temperature(self) -> TemperatureData:
        with self._lock:
            return TemperatureData(
                indoor=self.temperature.indoor,
                outdoor=self.temperature.outdoor,
            )

    # ── Pogoda ───────────────────────────────

    def update_weather(self, **kwargs) -> None:
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self.weather, key):
                    setattr(self.weather, key, value)

    def get_weather(self) -> WeatherData:
        with self._lock:
            w = self.weather
            return WeatherData(
                city=w.city,
                temp_outside=w.temp_outside,
                current_pressure=w.current_pressure,
                current_humidity=w.current_humidity,
                info_weather=w.info_weather,
                time_update=w.time_update,
                ip_query=w.ip_query,
            )

    # ── Sieć ─────────────────────────────────

    def update_network(self, **kwargs) -> None:
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self.network, key):
                    setattr(self.network, key, value)

    def get_network(self) -> NetworkData:
        with self._lock:
            return NetworkData(ip_home=self.network.ip_home, ip_query=self.network.ip_query)

    # ── Loader z config.json ──────────────────

    def load_from_dict(self, data: dict) -> None:
        """Inicjalizacja stanu z config.json przy starcie."""
        with self._lock:
            self.leds.color      = data.get("color", 0)
            self.leds.brightness = data.get("brightness", 0.5)
            self.leds.effects    = data.get("effects", 0)
            self.leds.leds_speed = data.get("leds_speed", 1.0)

            self.weather.city             = data.get("city", "")
            self.weather.temp_outside     = data.get("temp_outside", "")
            self.weather.current_pressure = data.get("current_pressure", "")
            self.weather.current_humidity = data.get("current_humidity", "")
            self.weather.info_weather     = data.get("info_weather", "")
            self.weather.ip_query         = data.get("IP_query", "")

            self.network.ip_home  = data.get("IP_home", "...")
            self.network.ip_query = data.get("IP_query", "...")

            self.api_key          = data.get("api_key", "")
            self.base_url         = data.get("base_url", "")
            self.localization_url = data.get("localization_url", "")
            self.hour_start_lcd   = data.get("hour_start_LCD", "")
            self.hour_stop_lcd    = data.get("hour_stop_LCD", "")

        logger.info("AppState loaded from config")

    def to_dict(self) -> dict:
        """Eksport stanu do zapisu w config.json."""
        with self._lock:
            return {
                "color":            self.leds.color,
                "brightness":       self.leds.brightness,
                "effects":          self.leds.effects,
                "leds_speed":       self.leds.leds_speed,
                "city":             self.weather.city,
                "temp_outside":     self.weather.temp_outside,
                "current_pressure": self.weather.current_pressure,
                "current_humidity": self.weather.current_humidity,
                "info_weather":     self.weather.info_weather,
                "IP_query":         self.weather.ip_query,
                "IP_home":          self.network.ip_home,
                "api_key":          self.api_key,
                "base_url":         self.base_url,
                "localization_url": self.localization_url,
                "hour_start_LCD":   self.hour_start_lcd,
                "hour_stop_LCD":    self.hour_stop_lcd,
            }


# Singleton
state = AppState()
