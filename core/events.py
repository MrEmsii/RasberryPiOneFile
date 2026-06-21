# core/events.py
# Author: Emsii (refactored)
# Event-Driven architecture — centralny szyna zdarzeń
#
# Przepływ:
#   Producer (IR, Temp, Weather) → emit(event) → EventBus → Consumer (LEDs, LCD, DB)

import queue
import threading
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List
from enum import Enum, auto

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Typy zdarzeń
# ─────────────────────────────────────────────

class EventType(Enum):
    # IR Remote
    IR_COLOR_CHANGED      = auto()   # payload: {"color": int}
    IR_BRIGHTNESS_CHANGED = auto()   # payload: {"brightness": float}
    IR_EFFECT_CHANGED     = auto()   # payload: {"effects": int}

    # Temperatura
    TEMP_INDOOR_UPDATED   = auto()   # payload: {"value": float}
    TEMP_OUTDOOR_UPDATED  = auto()   # payload: {"value": float}
    TEMP_ALL_UPDATED      = auto()   # payload: {"indoor": float, "outdoor": float | None}
    CPU_TEMP_UPDATED      = auto()   # payload: {"temp": float}
    FAN_SPEED_CHANGED     = auto()   # payload: {"speed": int (0/50/100)}  CPUEventType for fan
    CPU_PROCENT_UPDATED   = auto()   # payload: {"procent": int (0-100)}  CPUEventType for CPU load percentage

    # Pogoda
    WEATHER_UPDATED       = auto()   # payload: dict z danymi pogodowymi

    # Sieć / lokalizacja
    IP_UPDATED            = auto()   # payload: {"ip_home": str}
    LOCATION_UPDATED      = auto()   # payload: {"city": str, "ip_query": str}

    # System
    LCD_ON                = auto()   # payload: {"stop_at": datetime}
    LCD_OFF               = auto()
    LEDS_OFF              = auto()
    SHUTDOWN              = auto()


# ─────────────────────────────────────────────
#  Obiekt zdarzenia
# ─────────────────────────────────────────────

@dataclass
class Event:
    type: EventType
    payload: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self):
        return f"Event({self.type.name}, {self.payload})"


# ─────────────────────────────────────────────
#  EventBus — serce architektury
# ─────────────────────────────────────────────

class EventBus:
    """
    Centralny dispatcher zdarzeń.

    Producenci (IR, Temp, Weather) wywołują bus.emit(event).
    Konsumenci (LEDs, LCD, DB) rejestrują się przez bus.subscribe(event_type, handler).

    Handlery są wywoływane w osobnym wątku dispatcher'a — producent
    nie blokuje się czekając na zakończenie obsługi.
    """

    def __init__(self, maxsize: int = 100):
        self._queue: queue.Queue[Event] = queue.Queue(maxsize=maxsize)
        self._handlers: Dict[EventType, List[Callable]] = {}
        self._running = False
        self._dispatcher_thread: "threading.Thread | None" = None

    def subscribe(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """Zarejestruj handler dla danego typu zdarzenia."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"Subscribed {handler.__qualname__} → {event_type.name}")

    def emit(self, event: Event) -> None:
        """Wyemituj zdarzenie. Nie blokuje — wrzuca do kolejki i wraca."""
        try:
            self._queue.put_nowait(event)
            logger.debug(f"Emitted: {event}")
        except queue.Full:
            logger.warning(f"EventBus full! Dropped: {event}")

    def start(self) -> None:
        """Uruchom wątek dispatcher'a."""
        self._running = True
        self._dispatcher_thread = threading.Thread(
            target=self._dispatch_loop,
            name="EventBus-Dispatcher",
            daemon=True
        )
        self._dispatcher_thread.start()
        logger.info("EventBus started")

    def stop(self) -> None:
        """Zatrzymaj dispatcher gracefully."""
        self._running = False
        self._queue.put_nowait(Event(EventType.SHUTDOWN))  # odblokuj get()
        if self._dispatcher_thread:
            self._dispatcher_thread.join(timeout=3)
        logger.info("EventBus stopped")

    def _dispatch_loop(self) -> None:
        """Pętla dispatching'u — działa w osobnym wątku."""
        while self._running:
            try:
                event = self._queue.get(timeout=1.0)

                if event.type == EventType.SHUTDOWN:
                    break

                handlers = self._handlers.get(event.type, [])
                for handler in handlers:
                    try:
                        handler(event)
                    except Exception:
                        logger.exception(f"Handler {handler.__qualname__} failed for {event}")

                self._queue.task_done()

            except queue.Empty:
                continue
            except Exception:
                logger.exception("EventBus dispatch loop error")


# ─────────────────────────────────────────────
#  Singleton — jeden bus dla całej aplikacji
# ─────────────────────────────────────────────

bus = EventBus()