# services/consumers.py
# Author: Emsii (refactored)
# KONSUMENCI — subskrybują zdarzenia i reagują na nie.
# Każdy consumer ma jedną odpowiedzialność.

import logging
import datetime

from core.events import bus, Event, EventType
from core.state import state
from core import config as cfg_manager

logger = logging.getLogger(__name__)


# ─── StateUpdater — aktualizuje AppState ─────────────────

class StateUpdater:
    """
    Centralny konsument który aktualizuje AppState na podstawie zdarzeń.
    Jeden handler per typ zdarzenia — żadnej logiki biznesowej, tylko zapis do stanu.
    """

    def __init__(self):
        self._register()

    def _register(self) -> None:
        bus.subscribe(EventType.IR_COLOR_CHANGED,      self._on_color)
        bus.subscribe(EventType.IR_BRIGHTNESS_CHANGED, self._on_brightness)
        bus.subscribe(EventType.IR_EFFECT_CHANGED,     self._on_effect)
        bus.subscribe(EventType.TEMP_ALL_UPDATED,      self._on_temp)
        bus.subscribe(EventType.WEATHER_UPDATED,       self._on_weather)
        bus.subscribe(EventType.LOCATION_UPDATED,      self._on_location)
        bus.subscribe(EventType.IP_UPDATED,            self._on_ip)
        bus.subscribe(EventType.LEDS_OFF,              self._on_leds_off)

    def _on_color(self, event: Event) -> None:
        state.update_leds(color=event.payload["color"])

    def _on_brightness(self, event: Event) -> None:
        state.update_leds(brightness=event.payload["brightness"])

    def _on_effect(self, event: Event) -> None:
        state.update_leds(effects=event.payload["effects"])

    def _on_temp(self, event: Event) -> None:
        state.update_temperature(
            indoor=event.payload.get("indoor"),
            outdoor=event.payload.get("outdoor"),
        )

    def _on_weather(self, event: Event) -> None:
        state.update_weather(
            temp_outside=event.payload.get("temp_outside", ""),
            current_pressure=event.payload.get("current_pressure", ""),
            current_humidity=event.payload.get("current_humidity", ""),
            info_weather=event.payload.get("info_weather", ""),
            time_update=event.payload.get("time_update", ""),
        )

    def _on_location(self, event: Event) -> None:
        state.update_weather(city=event.payload["city"], ip_query=event.payload["ip_query"])
        state.update_network(ip_query=event.payload["ip_query"])

    def _on_ip(self, event: Event) -> None:
        state.update_network(ip_home=event.payload["ip_home"])

    def _on_leds_off(self, event: Event) -> None:
        brightness = state.get_leds().brightness
        new_br = max(brightness, 0.5)
        state.update_leds(color=0, effects=0, brightness=new_br)


# ─── ConfigPersister — zapisuje config.json ──────────────

class ConfigPersister:
    """
    Subskrybuje zdarzenia i persystuje zmieniony stan do config.json.
    To JEDYNE miejsce które pisze do pliku w runtime.

    Zapis odbywa się po każdej istotnej zmianie — w praktyce
    wystarczyłoby debounce'ować (np. co 30s), ale dla prostoty zapis jest natychmiastowy.
    """

    def __init__(self):
        self._register()

    def _register(self) -> None:
        bus.subscribe(EventType.IR_COLOR_CHANGED,      self._save)
        bus.subscribe(EventType.IR_BRIGHTNESS_CHANGED, self._save)
        bus.subscribe(EventType.IR_EFFECT_CHANGED,     self._save)
        bus.subscribe(EventType.WEATHER_UPDATED,       self._save)
        bus.subscribe(EventType.LOCATION_UPDATED,      self._save)
        bus.subscribe(EventType.IP_UPDATED,            self._save)
        bus.subscribe(EventType.LEDS_OFF,              self._save)

    def _save(self, event: Event) -> None:
        """Zapisz aktualny stan do config.json po każdym zdarzeniu."""
        try:
            # StateUpdater już zaktualizował state przed nami (kolejność subskrypcji)
            # więc state.to_dict() zawiera świeże dane
            cfg_manager.save(state.to_dict())
        except Exception:
            logger.exception(f"ConfigPersister: failed to save after {event.type.name}")


# ─── DatabaseWriter — zapisuje temperatury do SQLite ─────

class DatabaseWriter:
    """
    Subskrybuje TEMP_ALL_UPDATED i zapisuje do bazy Heat.db.
    Jedyna klasa która dotyka bazy danych w runtime.
    """

    def __init__(self):
        self._register()

    def _register(self) -> None:
        bus.subscribe(EventType.TEMP_ALL_UPDATED, self._on_temp)

    def _on_temp(self, event: Event) -> None:
        from services import db_service
        indoor = event.payload.get("indoor")
        outdoor = event.payload.get("outdoor")

        now_date = datetime.datetime.now().strftime("%Y-%m-%d")
        now_time = datetime.datetime.now().strftime("%H:%M:%S")

        try:
            if indoor is not None:
                db_service.insert_temperature(
                    table="temperatura",
                    date=now_date, time=now_time,
                    value=indoor,
                )
            if outdoor is not None:
                db_service.insert_temperature(
                    table="temperatura_outdoor",
                    date=now_date, time=now_time,
                    value=outdoor,
                )
        except Exception:
            logger.exception("DatabaseWriter: insert failed")


# ─── Scheduler — obsługuje zdarzenia czasowe ─────────────

class Scheduler:
    """
    Zastępuje chaos z thread_Control.
    Tick co 1s — sprawdza co należy włączyć/wyłączyć.
    Nie używa wątków do każdej operacji — emituje zdarzenia.

    LCD ON/OFF jest teraz zdarzeniem, a nie bezpośrednim wywołaniem wątku.
    """

    def __init__(self):
        self._lcd_on = True
        self._next_weather_check = datetime.datetime.now()
        self._next_ip_check = datetime.datetime.now()
        self._next_location_check = datetime.datetime.now()

    def tick(self, now: datetime.datetime) -> None:
        """Wywoływać co 1s z głównej pętli."""
        hour = now.hour
        hour_start = state.hour_start_lcd
        hour_stop = state.hour_stop_lcd

        # LCD
        should_be_on = hour_start <= hour < hour_stop
        if should_be_on and not self._lcd_on:
            stop_at = now.replace(hour=hour_stop, minute=0, second=0, microsecond=0)
            bus.emit(Event(EventType.LCD_ON, {"stop_at": stop_at}))
            self._lcd_on = True
        elif not should_be_on and self._lcd_on:
            bus.emit(Event(EventType.LCD_OFF))
            bus.emit(Event(EventType.LEDS_OFF))
            self._lcd_on = False

        # Wymuszenie następnego dnia
        if hour < hour_start and not self._lcd_on:
            self._lcd_on = False
