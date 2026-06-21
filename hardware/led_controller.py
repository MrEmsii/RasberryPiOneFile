# hardware/led_controller.py
# Author: Emsii (refactored)
# CONSUMER — subskrybuje zdarzenia LED i steruje diodami.
# Nie wie nic o IR, config, LCD — tylko reaguje na zdarzenia.

import time
import random
import logging
from typing import Tuple

try:
    import board
    import neopixel
    import numpy as np
    import RPi.GPIO as GPIO
    HW_AVAILABLE = True
except ImportError:
    HW_AVAILABLE = False
    logging.getLogger(__name__).warning("LED hardware not available")

from core.events import bus, Event, EventType
from core.state import state

logger = logging.getLogger(__name__)

# ─── Konfiguracja sprzętu ────────────────────────────────

PIXEL_PIN    = None   # board.D21 przy dostępnym hardware
NUM_PIXELS   = 15
ORDER        = None   # neopixel.GRB

# GPIO PWM — diody RGB (nie NeoPixel)
RGB_PINS = {"red": 9, "green": 10, "blue": 11}

# Paleta kolorów indeksowana przez state.leds.color
COLOR_PALETTE: list[Tuple[int, int, int]] = [
    (0, 0, 0),       # 0 = off
    (255, 0, 0),     # 1 = czerwony
    (0, 255, 0),     # 2 = zielony
    (0, 0, 255),     # 3 = niebieski
    (204, 51, 0),    # 4 = pomarańczowy
    (10, 255, 30),   # 5 = limonkowy
    (255, 0, 255),   # 6 = magenta
    (50, 50, 205),   # 7 = fioletowy
    (50, 120, 50),   # 8 = ciemny zielony
    (0, 255, 255),   # 9 = cyjan
    (255, 255, 255), # 10 = biały
]


class LEDController:
    """
    Kontroler diod NeoPixel + RGB PWM.

    Styl pracy:
      - NeoPixel tworzony RAZ w __init__ (nie przy każdej klatce!)
      - run() to pętla efektów — odczytuje stan z AppState
      - Subskrybuje zdarzenia żeby natychmiast reagować na zmiany
    """

    def __init__(self):
        self._pixels = None
        self._pwm: dict = {}
        self._setup_hardware()
        self._register_handlers()

    def _setup_hardware(self) -> None:
        if not HW_AVAILABLE:
            return
        try:
            global PIXEL_PIN, ORDER
            PIXEL_PIN = board.D21
            ORDER = neopixel.GRB

            initial_brightness = state.get_leds().brightness
            self._pixels = neopixel.NeoPixel(
                PIXEL_PIN, NUM_PIXELS,
                brightness=initial_brightness,
                auto_write=False,
                pixel_order=ORDER,
            )

            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            for name, pin in RGB_PINS.items():
                GPIO.setup(pin, GPIO.OUT)
                pwm = GPIO.PWM(pin, 50)
                pwm.start(0)
                self._pwm[name] = pwm

            logger.info("LED hardware initialized")
        except Exception:
            logger.exception("LED hardware init failed")

    def _register_handlers(self) -> None:
        """Subskrybuj zdarzenia — konsument pasywnie nasłuchuje."""
        bus.subscribe(EventType.IR_COLOR_CHANGED,      self._on_color_changed)
        bus.subscribe(EventType.IR_BRIGHTNESS_CHANGED, self._on_brightness_changed)
        bus.subscribe(EventType.IR_EFFECT_CHANGED,     self._on_effect_changed)
        bus.subscribe(EventType.LEDS_OFF,              self._on_leds_off)

    # ── Handlery zdarzeń ─────────────────────────────────

    def _on_color_changed(self, event: Event) -> None:
        """Reaguje na IR_COLOR_CHANGED — zmienia kolor w AppState."""
        state.update_leds(color=event.payload["color"])
        logger.debug(f"Color changed: {event.payload['color']}")

    def _on_brightness_changed(self, event: Event) -> None:
        brightness = event.payload["brightness"]
        state.update_leds(brightness=brightness)
        if self._pixels:
            self._pixels.brightness = brightness
        logger.debug(f"Brightness changed: {brightness}")

    def _on_effect_changed(self, event: Event) -> None:
        state.update_leds(effects=event.payload["effects"])
        logger.debug(f"Effect changed: {event.payload['effects']}")

    def _on_leds_off(self, event: Event) -> None:
        state.update_leds(color=0, effects=0)
        self._fill((0, 0, 0), 0.0)
        logger.info("LEDs turned off")

    # ── Sprzęt ───────────────────────────────────────────

    def _fill(self, color: Tuple[int, int, int], brightness: float) -> None:
        """Wypełnij wszystkie piksele i ustaw PWM RGB."""
        if not HW_AVAILABLE or not self._pixels:
            return
        self._pixels.brightness = brightness
        self._pixels.fill(color)
        self._pixels.show()
        self._set_rgb_pwm(color, brightness)

    def _set_rgb_pwm(self, color: Tuple[int, int, int], brightness: float) -> None:
        if not self._pwm:
            return
        r, g, b = color
        self._pwm["red"].ChangeDutyCycle(r / 255 * 100 * brightness)
        self._pwm["green"].ChangeDutyCycle(g / 255 * 100 * brightness)
        self._pwm["blue"].ChangeDutyCycle(b / 255 * 100 * brightness)

    def _stop_rgb_pwm(self) -> None:
        for pwm in self._pwm.values():
            pwm.ChangeDutyCycle(0)

    # ── Efekty ───────────────────────────────────────────

    def _wheel(self, pos: int) -> Tuple[int, int, int]:
        if pos < 0 or pos > 255:
            return 0, 0, 0
        if pos < 85:
            return int(pos * 3), int(255 - pos * 3), 0
        if pos < 170:
            pos -= 85
            return int(255 - pos * 3), 0, int(pos * 3)
        pos -= 170
        return 0, int(pos * 3), int(255 - pos * 3)

    def _effect_constant(self) -> None:
        leds = state.get_leds()
        color = COLOR_PALETTE[leds.color % len(COLOR_PALETTE)]
        self._fill(color, leds.brightness)

    def _effect_stair(self, step: float, color: Tuple[int, int, int]) -> None:
        import numpy as np
        for br in list(np.arange(0, 0.8, step / 2)) + list(np.arange(0.8, 0, -step / 2)):
            self._fill(color, br)
            time.sleep(step)

    def _effect_stair_random(self, step: float) -> None:
        color = (random.randint(0, 5), random.randint(0, 255), random.randint(0, 255))
        self._effect_stair(step, color)

    def _effect_rainbow(self, wait: float) -> None:
        if not HW_AVAILABLE or not self._pixels:
            return
        brightness = state.get_leds().brightness
        for j in range(255):
            for i in range(NUM_PIXELS):
                pixel_index = (i * 256 // NUM_PIXELS) + j
                self._pixels[i] = self._wheel(pixel_index & 255)
            last_color = self._pixels[NUM_PIXELS - 1]
            self._pixels.brightness = brightness
            self._pixels.show()
            self._set_rgb_pwm(last_color, brightness)
            time.sleep(wait)

    # ── Główna pętla ─────────────────────────────────────

    def run(self) -> None:
        """
        Pętla efektów — blokująca, uruchamiać w osobnym wątku.
        Odczytuje aktualny stan z AppState przy każdej iteracji.
        """
        logger.info("LED Controller loop started")
        while True:
            try:
                leds = state.get_leds()
                speed = leds.leds_speed

                if leds.effects == 1:
                    self._effect_constant()
                    time.sleep(0.4)
                elif leds.effects == 2:
                    self._effect_stair(0.004 * speed, COLOR_PALETTE[leds.color % len(COLOR_PALETTE)])
                elif leds.effects == 3:
                    self._effect_stair_random(0.004 * speed)
                elif leds.effects == 4:
                    self._effect_rainbow(0.01 / max(speed, 0.1))
                else:
                    self._fill((0, 0, 0), 0.0)
                    time.sleep(1.0)

            except Exception:
                logger.exception("LED effect error")
                time.sleep(1.0)

    def cleanup(self) -> None:
        self._stop_rgb_pwm()
        for pwm in self._pwm.values():
            pwm.stop()
        if HW_AVAILABLE:
            GPIO.cleanup()
        logger.info("LED Controller cleaned up")
