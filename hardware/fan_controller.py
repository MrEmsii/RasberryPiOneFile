# hardware/fan_controller.py
# Author: Emsii (refactored)
# CPU temperature monitoring + PWM fan control with hysteresis.
#
# PRODUCER: CPUTemperatureProducer — emits CPU_TEMP_UPDATED events
# CONSUMER: FanDriver — subscribes and adjusts PWM based on hysteresis thresholds

import logging
import threading
from typing import Optional

try:
    import RPi.GPIO as GPIO
    HW_AVAILABLE = True
except ImportError:
    HW_AVAILABLE = False

from core.events import bus, Event, EventType
from core.state import state

logger = logging.getLogger(__name__)

# ─── Konfiguracja sprzętu ────────────────────────────────

PWM_PIN = 21      # GPIO21 -> PWM wentylator
POWER_PIN = 16    # GPIO16 -> zasilanie (opcjonalnie)
PWM_FREQ = 25000  # 25kHz

# ─── Hystereza temperatury ───────────────────────────────

FAN_OFF_TEMP = 48    # Temperatura poniżej której wentylator wyłącza się
FAN_LOW_TEMP = 52    # Temperatura powyżej której włącza się na niskich obrotach
HYSTERESIS = 2       # Margines — unikanie oscylacji

# Stan wentylatora: 0% OFF, 50% LOW, 100% HIGH
FAN_STATE_OFF = 0
FAN_STATE_LOW = 50
FAN_STATE_HIGH = 100


# ─── EventType dla wentylatora ───────────────────────────

class FanEventType:
    """Dodatkowe typy zdarzeń specyficzne dla wentylatora."""
    CPU_TEMP_UPDATED = "cpu_temp_updated"      # payload: {"temp": float}
    FAN_SPEED_CHANGED = "fan_speed_changed"    # payload: {"speed": int (0/50/100)}


# ─── CPU Temperature Producer ────────────────────────────

class CPUTemperatureProducer(threading.Thread):
    """
    Odczytuje CPU temperature z /sys/class/thermal/ i emituje zdarzenie.
    Wątek demoniczny — uruchamia się w tle co N sekund.
    """

    def __init__(self, interval: float = 5.0):
        super().__init__(name="CPU-Temp-Producer", daemon=True)
        self._interval = interval
        self._stop_event = threading.Event()

    def run(self) -> None:
        logger.info(f"CPUTemperatureProducer started (interval={self._interval}s)")
        while not self._stop_event.is_set():
            try:
                temp = self._read_cpu_temp()
                if temp is not None:
                    bus.emit(Event(EventType.CPU_TEMP_UPDATED, {"temp": temp}))
                    logger.debug(f"CPU temp: {temp:.1f}°C")
            except Exception:
                logger.exception("CPU temperature read failed")

            self._stop_event.wait(timeout=self._interval)
        logger.info("CPUTemperatureProducer stopped")

    def _read_cpu_temp(self) -> Optional[float]:
        """Odczyt temperatury z thermal_zone0."""
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp_millidegrees = int(f.read().strip())
                return temp_millidegrees / 1000.0
        except FileNotFoundError:
            logger.warning("thermal_zone0 not found — CPU temp monitoring disabled")
            return None
        except Exception:
            logger.exception("Failed to read CPU temperature")
            return None

    def stop(self) -> None:
        self._stop_event.set()


# ─── Fan Driver (Consumer + PWM control) ─────────────────

class FanDriver:
    """
    Steruje wentylatorem na podstawie temperatury CPU z histerezą.

    Subskrybuje CPU_TEMP_UPDATED i zmienia PWM jeśli temperatura przekroczy progi.
    Histereza zapobiega oscylacji — wymaga odchylenia o HYSTERESIS od poprzedniego progu.
    """

    def __init__(self):
        self._pwm: Optional[object] = None
        self._power: Optional[object] = None
        self._current_state = FAN_STATE_OFF
        self._last_temp = 0.0

        self._setup_hardware()
        self._register_handlers()

    def _setup_hardware(self) -> None:
        """Inicjalizacja GPIO i PWM."""
        if not HW_AVAILABLE:
            logger.warning("GPIO not available — fan disabled")
            return

        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

            # Zasilanie wentylatora (opcjonalnie)
            GPIO.setup(POWER_PIN, GPIO.OUT)
            GPIO.output(POWER_PIN, GPIO.HIGH)
            self._power = POWER_PIN

            # PWM
            GPIO.setup(PWM_PIN, GPIO.OUT)
            self._pwm = GPIO.PWM(PWM_PIN, PWM_FREQ)
            self._pwm.start(0)

            logger.info("Fan hardware initialized")
        except Exception:
            logger.exception("Fan hardware init failed")

    def _register_handlers(self) -> None:
        """Subskrybuj zdarzenia temperatury."""
        # Importujemy dynamicznie — unikamy circular imports
        from core.events import EventType
        bus.subscribe(EventType.CPU_TEMP_UPDATED, self._on_cpu_temp)

    def _on_cpu_temp(self, event: Event) -> None:
        """Obsługi zdarzenia temperatury — oblicz nowy stan i zmień PWM."""
        temp = event.payload.get("temp")
        if temp is None:
            return

        self._last_temp = temp
        new_state = self._calculate_fan_state(temp, self._current_state)

        if new_state != self._current_state:
            self._set_fan_speed(new_state)
            self._current_state = new_state
            logger.info(f"Fan speed changed: {self._current_state}% (temp {temp:.1f}°C)")

    def _calculate_fan_state(self, temp: float, current_state: int) -> int:
        """
        Oblicz nowy stan wentylatora z histerezą.

        Histereza unika oscylacji na granicy progów — zmiana stanu wymaga
        odchylenia o HYSTERESIS od poprzedniego punktu aktywacji.
        """
        # OFF -> LOW (temp >= FAN_OFF_TEMP + HYSTERESIS)
        if current_state == FAN_STATE_OFF and temp >= FAN_OFF_TEMP + HYSTERESIS:
            return FAN_STATE_LOW

        # LOW -> OFF (temp <= FAN_OFF_TEMP - HYSTERESIS)
        elif current_state == FAN_STATE_LOW and temp <= FAN_OFF_TEMP - HYSTERESIS:
            return FAN_STATE_OFF

        # LOW -> HIGH (temp >= FAN_LOW_TEMP + HYSTERESIS)
        elif current_state == FAN_STATE_LOW and temp >= FAN_LOW_TEMP + HYSTERESIS:
            return FAN_STATE_HIGH

        # HIGH -> LOW (temp <= FAN_LOW_TEMP - HYSTERESIS)
        elif current_state == FAN_STATE_HIGH and temp <= FAN_LOW_TEMP - HYSTERESIS:
            return FAN_STATE_LOW

        # Bez zmian
        return current_state

    def _set_fan_speed(self, speed: int) -> None:
        """Ustaw PWM dla wentylatora i emituj zdarzenie."""
        if not HW_AVAILABLE or not self._pwm:
            return

        try:
            self._pwm.ChangeDutyCycle(speed)
            # Emituj zdarzenie o zmianie prędkości
            bus.emit(Event(EventType.FAN_SPEED_CHANGED, {"speed": speed}))
        except Exception:
            logger.exception(f"Failed to set fan speed to {speed}%")

    def get_status(self) -> dict:
        """Zwróć aktualny status wentylatora."""
        return {
            "temp": self._last_temp,
            "speed_percent": self._current_state,
            "speed_name": {
                FAN_STATE_OFF: "OFF",
                FAN_STATE_LOW: "LOW",
                FAN_STATE_HIGH: "HIGH",
            }.get(self._current_state, "UNKNOWN"),
        }

    def cleanup(self) -> None:
        """Wyczyść GPIO przy shutdown."""
        if not HW_AVAILABLE:
            return

        try:
            if self._pwm:
                self._pwm.stop()
            if self._power:
                GPIO.output(POWER_PIN, GPIO.LOW)
            GPIO.cleanup()
            logger.info("Fan GPIO cleaned up")
        except Exception:
            logger.exception("Fan cleanup failed")