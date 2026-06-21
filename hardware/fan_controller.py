# hardware/fan_controller.py
# Author: Emsii (refactored)
# CPU temperature monitoring + PWM fan control with hysteresis.
#
# PRODUCER: CPUTemperatureProducer — emits CPU_TEMP_UPDATED events
# CONSUMER: FanDriver — subscribes and adjusts PWM based on hysteresis thresholds

import logging
import threading
import psutil
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

PWM_PIN   = 12    # GPIO12 (pin 32) -> PWM wentylator
POWER_PIN = 16    # GPIO16 -> zasilanie (opcjonalnie)
PWM_FREQ  = 100   # 100 Hz — hardware PWM GPIO12

# ─── Kroki PWM co 10% z histerezą ───────────────────────
#
# Każdy próg to para (temp_up, temp_down, pwm_percent):
#   temp_up   — temperatura przy której przechodzimy NA ten poziom (z niższego)
#   temp_down — temperatura przy której schodzimy Z tego poziomu (do niższego)
#   pwm       — wypełnienie PWM [%]
#
# Histereza = temp_up - temp_down = 2°C na każdym progu.
# Zakresy: 0% < 47°C | 10% 47-49 | 20% 49-51 | 30% 51-53 | 40% 53-55
#          50% 55-57 | 60% 57-59 | 70% 59-61 | 80% 61-63 | 90% 63-65 | 100% >65°C

FAN_LEVELS = [
    # (temp_up, temp_down, pwm)
    (47,  46.9999,   0),   # OFF
    (49,  47,  10),
    (51,  49,  20),
    (53,  51,  30),
    (55,  53,  40),
    (57,  55,  50),
    (59,  57,  60),
    (61,  59,  70),
    (63,  61,  80),
    (65,  63,  90),
    (999, 64, 100),   # MAX — temp_up=999 żeby nigdy nie przejść wyżej
]

# Singleton PWM na poziomie modułu — przeżywa restart instancji FanDriver.
# GPIO.cleanup() nie niszczy obiektu PWM w RPi.GPIO, więc trzymamy go tutaj
# i reużywamy zamiast tworzyć nowy (co rzuca RuntimeError).
_pwm_singleton: Optional[object] = None


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
                cpu_percent = int(psutil.cpu_percent(interval=None))
                ram_percent = int(psutil.virtual_memory().percent)
                if temp is not None:
                    bus.emit(Event(EventType.CPU_TEMP_UPDATED, {"temp": temp}))
                    bus.emit(Event(EventType.CPU_PROCENT_UPDATED, {
                        "procent": cpu_percent,
                        "ram": ram_percent,
                    }))
                    logger.debug(f"CPU temp: {temp:.1f}°C, CPU: {cpu_percent}%, RAM: {ram_percent}%")
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

    11 poziomów PWM co 10% (0–100%). Każdy próg ma osobną temperaturę
    wejścia (temp_up) i wyjścia (temp_down) — histereza 2°C zapobiega
    oscylacji na granicy progów.
    """

    def __init__(self):
        self._pwm: Optional[object] = None
        self._power: Optional[object] = None
        self._current_level: int = 0   # indeks w FAN_LEVELS
        self._last_temp: float = 0.0

        self._setup_hardware()
        self._register_handlers()

    def _setup_hardware(self) -> None:
        """Inicjalizacja GPIO i PWM."""
        global _pwm_singleton

        if not HW_AVAILABLE:
            logger.warning("GPIO not available — fan disabled")
            return

        try:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)

            GPIO.setup(POWER_PIN, GPIO.OUT)
            GPIO.output(POWER_PIN, GPIO.HIGH)
            self._power = POWER_PIN

            GPIO.setup(PWM_PIN, GPIO.OUT)

            if _pwm_singleton is not None:
                self._pwm = _pwm_singleton
                self._pwm.ChangeDutyCycle(0)
                logger.info("Fan hardware reused existing PWM object")
            else:
                self._pwm = GPIO.PWM(PWM_PIN, PWM_FREQ)
                self._pwm.start(0)
                _pwm_singleton = self._pwm
                logger.info("Fan hardware initialized (new PWM object)")

            self._current_level = 0

        except Exception:
            logger.exception("Fan hardware init failed")

    def _register_handlers(self) -> None:
        bus.subscribe(EventType.CPU_TEMP_UPDATED, self._on_cpu_temp)

    def _on_cpu_temp(self, event: Event) -> None:
        temp = event.payload.get("temp")
        if temp is None:
            return

        self._last_temp = temp
        new_level = self._calculate_level(temp)

        if new_level != self._current_level:
            pwm = FAN_LEVELS[new_level][2]
            self._set_fan_speed(pwm)
            logger.info(
                f"Fan: {FAN_LEVELS[self._current_level][2]}% → {pwm}% "
                f"(poziom {self._current_level}→{new_level}, temp {temp:.1f}°C)"
            )
            self._current_level = new_level

    def _calculate_level(self, temp: float) -> int:
        """
        Oblicz nowy poziom wentylatora z histerezą i dowolnym skokiem.

        Wzrost: skanuj od najwyższego poziomu w dół — weź pierwszy
                którego temp_up <= temp. Pozwala przeskoczyć kilka stopni naraz.
        Spadek: skanuj od bieżącego poziomu w dół — weź pierwszy
                którego temp_down <= temp. Histereza bieżącego poziomu
                zapobiega oscylacji.
        """
        current = self._current_level

        # Wzrost — szukaj od góry
        for level in range(len(FAN_LEVELS) - 1, current, -1):
            if temp >= FAN_LEVELS[level][0]:
                return level

        # Spadek — szukaj od bieżącego w dół
        if current > 0 and temp < FAN_LEVELS[current][1]:
            for level in range(current - 1, -1, -1):
                if level == 0 or temp >= FAN_LEVELS[level][1]:
                    return level

        return current

    def _set_fan_speed(self, speed: int) -> None:
        if not HW_AVAILABLE or not self._pwm:
            return
        try:
            self._pwm.ChangeDutyCycle(speed)
            bus.emit(Event(EventType.FAN_SPEED_CHANGED, {"speed": speed}))
        except Exception:
            logger.exception(f"Failed to set fan speed to {speed}%")

    def get_status(self) -> dict:
        pwm = FAN_LEVELS[self._current_level][2]
        return {
            "temp":         self._last_temp,
            "level":        self._current_level,
            "speed_percent": pwm,
        }

    def cleanup(self) -> None:
        global _pwm_singleton

        if not HW_AVAILABLE:
            return
        try:
            if self._pwm:
                self._pwm.stop()
                _pwm_singleton = None
            if self._power:
                GPIO.output(POWER_PIN, GPIO.LOW)
            GPIO.cleanup()
            logger.info("Fan GPIO cleaned up")
        except Exception:
            logger.exception("Fan cleanup failed")