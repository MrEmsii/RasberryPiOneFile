# main.py
# Author: Emsii (refactored)
# Punkt wejścia aplikacji — orkiestrator.
#
# Odpowiedzialność main.py:
#   1. Inicjalizacja (config, logging, DB, state)
#   2. Uruchomienie EventBus
#   3. Rejestracja konsumentów
#   4. Uruchomienie producentów (wątki)
#   5. Uruchomienie sprzętu (LED, IR, LCD)
#   6. Główna pętla (Scheduler tick)
#   7. Graceful shutdown przy Ctrl+C
#
# main.py NIE zawiera logiki biznesowej — deleguje wszystko do modułów.

import time
import signal
import logging
import datetime
import threading

import setproctitle

from utils.logging_setup import setup_logging
from core import config as cfg_manager
from core.events import bus
from core.state import state

from services import db_service
from services.producers import (
    TemperatureProducer,
    WeatherProducer,
    LocationProducer,
    LocalIPProducer,
)
from services.consumers import (
    StateUpdater,
    ConfigPersister,
    DatabaseWriter,
    RPiDataWriter,
    Scheduler,
)

# Hardware — import opóźniony żeby błędy sprzętowe nie blokowały startu
from hardware.led_controller import LEDController
from hardware.lcd_controller import LCDController
from hardware.fan_controller import CPUTemperatureProducer, FanDriver
import hardware.ir_controller as ir_controller

logger = logging.getLogger(__name__)


# ─── Graceful Shutdown ───────────────────────────────────

_shutdown = threading.Event()

def _handle_signal(signum, frame):
    logger.info(f"Signal {signum} received — shutting down")
    _shutdown.set()

signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT,  _handle_signal)


# ─── Inicjalizacja ───────────────────────────────────────

def initialize() -> None:
    """Wszystko co musi się wydarzyć przed startem wątków."""
    setup_logging(logging.DEBUG)
    logger.info("=" * 60)
    logger.info("Emsii LCD starting up")

    # Config
    config_data = cfg_manager.initialize()
    state.load_from_dict(config_data)
    logger.info("Config and state loaded")

    # Baza danych
    db_service.ensure_tables()
    logger.info("Database ready")


# ─── Uruchomienie komponentów ────────────────────────────

def start_event_bus() -> None:
    bus.start()
    logger.info("EventBus running")


def register_consumers() -> "Scheduler":
    """
    Zarejestruj wszystkich konsumentów.

    WAŻNE: Kolejność ma znaczenie!
    1. StateUpdater — musi być PIERWSZY, aktualizuje AppState
    2. ConfigPersister — zapisuje config.json
    3. DatabaseWriter — zapisuje temperatury czujników do Heat.db
    4. RPiDataWriter — zapisuje CPU temp + fan speed do Heat.db
    5. Scheduler — OSTATNI, emituje zdarzenia LCD_ON/LCD_OFF w __init__

    Scheduler jest tworzony ostatni, dlatego wszystkie inne consumers
    (a przede wszystkim LCDController w hardware) są już gotowe do obsługi
    emitowanych zdarzeń.
    """
    state_updater = StateUpdater()
    config_persister = ConfigPersister()
    db_writer = DatabaseWriter()
    rpi_data_writer = RPiDataWriter()

    logger.info("Consumers registered (StateUpdater, ConfigPersister, DatabaseWriter, RPiDataWriter)")

    # Scheduler — tworzony OSTATNI, emituje LCD_ON/LCD_OFF w __init__
    scheduler = Scheduler()
    logger.info("Scheduler created — LCD state initialized based on current hour")

    return scheduler


def start_producers() -> list:
    """Uruchom wszystkich producentów danych."""
    producers = [
        TemperatureProducer(interval=180),   # co 3 minuty
        WeatherProducer(interval=120),        # co 2 minuty
        LocationProducer(interval=300),       # co 5 minut
        LocalIPProducer(interval=300),        # co 5 minut
    ]
    for p in producers:
        p.start()
        logger.info(f"Producer started: {p.name}")

    return producers


def start_hardware() -> tuple:
    """Uruchom kontrolery sprzętu."""
    # LCD — consumer, rejestruje się sam w konstruktorze
    lcd = LCDController()

    # LED — consumer + własna pętla efektów
    led = LEDController()
    led_thread = threading.Thread(
        target=led.run,
        name="LED-Effects",
        daemon=True,
    )
    led_thread.start()

    # Fan — CPU temperature monitoring + PWM control
    cpu_temp_producer = CPUTemperatureProducer(interval=5)
    cpu_temp_producer.start()

    fan_driver = FanDriver()

    # IR — producer, własna pętla odczytu
    ir_thread = threading.Thread(
        target=ir_controller.run,
        name="IR-Reader",
        daemon=True,
    )
    ir_thread.start()

    logger.info("Hardware threads started")
    return lcd, led, fan_driver, cpu_temp_producer


# ─── Główna pętla ────────────────────────────────────────

def main_loop(scheduler: Scheduler) -> None:
    """
    Główna pętla aplikacji — tick co sekundę.
    Scheduler sprawdza co włączyć/wyłączyć na podstawie czasu.
    """
    logger.info("Main loop running — press Ctrl+C to stop")
    while not _shutdown.is_set():
        try:
            scheduler.tick(datetime.datetime.now())
        except Exception:
            logger.exception("Scheduler tick error")
        time.sleep(1.0)


# ─── Shutdown ────────────────────────────────────────────

def shutdown(producers: list, led: LEDController, fan_driver: FanDriver, cpu_temp_producer: "CPUTemperatureProducer") -> None:
    logger.info("Shutdown sequence started")

    # Zatrzymaj producentów
    for p in producers:
        p.stop()
        p.join(timeout=3)

    # Zatrzymaj CPU temp producenta
    cpu_temp_producer.stop()
    cpu_temp_producer.join(timeout=3)

    # Wyczyść sprzęt
    led.cleanup()
    fan_driver.cleanup()

    # Zapisz stan końcowy
    cfg_manager.save(state.to_dict())

    # Zatrzymaj bus
    bus.stop()

    logger.info("Shutdown complete")


# ─── Punkt wejścia ───────────────────────────────────────

if __name__ == "__main__":
    setproctitle.setproctitle("Emsii_LCD")

    initialize()
    start_event_bus()

    # WAŻNE: Hardware musi się zarejestrować (subskrybować zdarzenia)
    # PRZED tym jak Scheduler będzie emitować zdarzenia LCD_ON/LCD_OFF
    lcd, led, cpu_temp_producer, fan_driver  = start_hardware()

    # Teraz rejestrujemy State/Config/DB consumers
    # Scheduler jest tworzony OSTATNI i emituje LCD_ON/LCD_OFF
    scheduler = register_consumers()

    producers = start_producers()

    try:
        main_loop(scheduler)
    finally:
        shutdown(producers, led, fan_driver, cpu_temp_producer)