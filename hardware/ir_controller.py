# hardware/ir_controller.py
# Author: Emsii (refactored)
# PRODUCER — odczytuje sygnały IR i emituje zdarzenia.
# Nie wie nic o LEDs, config, LCD — tylko sygnalizuje co naciśnięto.

import time
import logging
from datetime import datetime

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logging.getLogger(__name__).warning("RPi.GPIO not available — IR disabled")

from core.events import bus, Event, EventType
from core.state import state

logger = logging.getLogger(__name__)

PIN = 20
MAX_EFFECTS = 4

# Kody HEX pilota → nazwy przycisków
BUTTON_MAP = {
    0x300FF30CF: "1",   0x300FF18E7: "2",   0x300FF7A85: "3",
    0x300FF10EF: "4",   0x300FF38C7: "5",   0x300FF5AA5: "6",
    0x300FF42BD: "7",   0x300FF4AB5: "8",   0x300FF52AD: "9",
    0x300FF6897: "0",   0x300FF9867: "100+", 0x300FFB04F: "200+",
    0x300FFE01F: "-",   0x300FFA857: "+",   0x300FF906F: "eq",
    0x300FF22DD: "<<",  0x300FF02FD: ">>",  0x300FFC23D: ">||",
    0x300FFA25D: "ch-", 0x300FF629D: "ch",  0x300FFE21D: "ch+",
}

# Akcje pogrupowane semantycznie
COLOR_BUTTONS    = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}
EQ_BUTTON        = {"eq"}       # kolor 10 (biały)
DIM_DOWN         = {"<<"}
DIM_UP           = {">>"}
EFFECT_DOWN      = {"-"}
EFFECT_UP        = {"+"}


def _get_binary() -> int:
    """Odczyt surowego sygnału IR z pinu GPIO."""
    num1s = 0
    binary = 1
    command = []
    previous_value = 0
    value = GPIO.input(PIN)

    while value:
        time.sleep(0.01)
        value = GPIO.input(PIN)

    start_time = datetime.now()

    while True:
        if previous_value != value:
            now = datetime.now()
            pulse_time = now - start_time
            start_time = now
            command.append((previous_value, pulse_time.microseconds))

        if value:
            num1s += 1
        else:
            num1s = 0

        if num1s > 10000:
            break

        previous_value = value
        value = GPIO.input(PIN)

    for (typ, tme) in command:
        if typ == 1:
            binary = binary * 10 + (1 if tme > 1000 else 0)

    if len(str(binary)) > 34:
        binary = int(str(binary)[:34])

    return binary


def _convert_hex(binary_value: int) -> str:
    return hex(int(str(binary_value), 2))


def _handle_button(button_name: str) -> None:
    """
    Interpretuje naciśnięty przycisk i emituje odpowiednie zdarzenie.
    Żadnych bezpośrednich zapisów — tylko emit().
    """
    leds = state.get_leds()

    if button_name in COLOR_BUTTONS:
        bus.emit(Event(EventType.IR_COLOR_CHANGED, {"color": int(button_name)}))

    elif button_name in EQ_BUTTON:
        bus.emit(Event(EventType.IR_COLOR_CHANGED, {"color": 10}))

    elif button_name in DIM_DOWN:
        new_brightness = max(0.01, round(leds.brightness - 0.05, 3))
        bus.emit(Event(EventType.IR_BRIGHTNESS_CHANGED, {"brightness": new_brightness}))

    elif button_name in DIM_UP:
        new_brightness = min(0.80, round(leds.brightness + 0.05, 3))
        bus.emit(Event(EventType.IR_BRIGHTNESS_CHANGED, {"brightness": new_brightness}))

    elif button_name in EFFECT_DOWN:
        new_effects = max(1, leds.effects - 1)
        bus.emit(Event(EventType.IR_EFFECT_CHANGED, {"effects": new_effects}))

    elif button_name in EFFECT_UP:
        new_effects = min(MAX_EFFECTS, leds.effects + 1)
        bus.emit(Event(EventType.IR_EFFECT_CHANGED, {"effects": new_effects}))

    else:
        logger.debug(f"Unhandled button: {button_name}")


def run() -> None:
    """
    Główna pętla IR — blokująca, uruchamiać w osobnym wątku (thread lub Producer).
    """
    if not GPIO_AVAILABLE:
        logger.warning("IR Controller disabled — no GPIO")
        return

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PIN, GPIO.IN)
    logger.info("IR Controller started")

    try:
        while True:
            time.sleep(0.3)
            try:
                incoming = _convert_hex(_get_binary())
                for code, name in BUTTON_MAP.items():
                    if hex(code) == incoming:
                        logger.info(f"IR button: {name}")
                        _handle_button(name)
                        break
            except Exception:
                logger.exception("IR read error")
    finally:
        GPIO.cleanup()
        logger.info("IR Controller stopped, GPIO cleaned up")
