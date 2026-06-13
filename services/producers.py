# services/producers.py
# Author: Emsii (refactored)
# PRODUCENCI — zbierają dane ze świata zewnętrznego i emitują zdarzenia.
# Każdy Producer to osobny wątek z własnym interwałem.

import time
import datetime
import logging
import threading
from subprocess import check_output
from typing import Optional

import requests

from core.events import bus, Event, EventType
from core.state import state

logger = logging.getLogger(__name__)


# ─── Bazowa klasa Producer ───────────────────────────────

class Producer(threading.Thread):
    """
    Bazowy Producer — wątek który co `interval` sekund wykonuje zadanie i emituje zdarzenie.

    Podklasy implementują `produce()`.
    """

    def __init__(self, name: str, interval: float):
        super().__init__(name=name, daemon=True)
        self._interval = interval
        self._stop_event = threading.Event()

    def produce(self) -> None:
        """Logika zbierania danych — do nadpisania."""
        raise NotImplementedError

    def run(self) -> None:
        logger.info(f"Producer '{self.name}' started (interval={self._interval}s)")
        while not self._stop_event.is_set():
            try:
                self.produce()
            except Exception:
                logger.exception(f"Producer '{self.name}' error")
            self._stop_event.wait(timeout=self._interval)
        logger.info(f"Producer '{self.name}' stopped")

    def stop(self) -> None:
        self._stop_event.set()


# ─── Temperatura ─────────────────────────────────────────

class TemperatureProducer(Producer):
    """
    Odczytuje czujniki DS18B20 (w1therm) i emituje TEMP_ALL_UPDATED.
    Przy błędzie sensora emituje None — konsument sam decyduje jak obsłużyć brak danych.
    """

    def __init__(self, interval: float = 180.0):
        super().__init__(name="Temp-Producer", interval=interval)

    def produce(self) -> None:
        try:
            import w1thermsensor
            sensors = list(w1thermsensor.W1ThermSensor.get_available_sensors())

            indoor: Optional[float] = None
            outdoor: Optional[float] = None

            if len(sensors) >= 1:
                indoor = round(sensors[0].get_temperature() - 3.5, 1)
            if len(sensors) >= 2:
                outdoor = round(sensors[1].get_temperature() - 3.5, 1)

            bus.emit(Event(EventType.TEMP_ALL_UPDATED, {
                "indoor": indoor,
                "outdoor": outdoor,
            }))
            logger.debug(f"Temp: indoor={indoor}, outdoor={outdoor}")

        except ImportError:
            logger.warning("w1thermsensor not available — skipping temp read")
        except Exception:
            logger.exception("Temperature read failed")


# ─── Pogoda ──────────────────────────────────────────────

class WeatherProducer(Producer):
    """
    Pobiera dane pogodowe z OpenWeatherMap i emituje WEATHER_UPDATED.
    Aktywny tylko w godzinach działania LCD (sprawdza stan).
    """

    def __init__(self, interval: float = 120.0):
        super().__init__(name="Weather-Producer", interval=interval)

    def produce(self) -> None:
        cfg = state
        if not cfg.api_key or not cfg.base_url:
            logger.warning("Weather: missing api_key or base_url")
            return

        city = cfg.weather.city
        if not city:
            logger.warning("Weather: city not set yet — waiting for location")
            return

        url = f"{cfg.base_url}appid={cfg.api_key}&q={city}&lang=pl&units=metric"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            x = response.json()

            if x.get("cod") == "404":
                logger.warning(f"Weather: city '{city}' not found")
                return

            main = x["main"]
            weather_desc = x["weather"][0]["description"]

            payload = {
                "temp_outside":     f"{main['temp']}\u00dfC / {main['feels_like']}\u00dfC",
                "current_pressure": f"{main['pressure']} hPa",
                "current_humidity": f"{main['humidity']}%",
                "info_weather":     weather_desc,
                "time_update":      str(datetime.datetime.now()),
            }
            bus.emit(Event(EventType.WEATHER_UPDATED, payload))
            logger.debug(f"Weather updated: {payload['temp_outside']}")

        except requests.Timeout:
            logger.warning("Weather: request timeout")
        except requests.RequestException:
            logger.exception("Weather: network error")


# ─── Lokalizacja / IP zewnętrzne ─────────────────────────

class LocationProducer(Producer):
    """
    Pobiera lokalizację i IP z ipinfo.io, emituje LOCATION_UPDATED.
    """

    def __init__(self, interval: float = 300.0):
        super().__init__(name="Location-Producer", interval=interval)

    def produce(self) -> None:
        url = state.localization_url
        if not url:
            return
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
            city = data.get("city", "NO INFO")
            ip_query = data.get("ip", "NO INFO")
            bus.emit(Event(EventType.LOCATION_UPDATED, {"city": city, "ip_query": ip_query}))
            logger.debug(f"Location: {city}, IP: {ip_query}")
        except requests.Timeout:
            logger.warning("Location: request timeout")
        except Exception:
            logger.exception("Location fetch failed")


# ─── IP lokalne ───────────────────────────────────────────

class LocalIPProducer(Producer):
    """
    Pobiera lokalne IP przez hostname -I, emituje IP_UPDATED.
    """

    def __init__(self, interval: float = 300.0):
        super().__init__(name="LocalIP-Producer", interval=interval)

    def produce(self) -> None:
        try:
            cmd = check_output(
                "hostname -I | cut -d' ' -f1",
                shell=True, timeout=5
            ).decode("utf-8").strip()

            ip = cmd if 5 < len(cmd) < 16 else "No IP"
            bus.emit(Event(EventType.IP_UPDATED, {"ip_home": ip}))
            logger.debug(f"Local IP: {ip}")
        except Exception:
            logger.exception("Local IP fetch failed")
