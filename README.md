# Emsii LCD — Raspberry Pi Temperature & Weather Display

## Description

A Python application for Raspberry Pi 4 that measures temperature using DS18B20 sensors and displays it on an I2C LCD. Additionally retrieves location and weather data from external APIs, presenting everything on a 20×4 LCD display. Supports RGB LED control and IR remote operation.

Refactored to an **Event-Driven / Producer-Consumer** architecture for thread safety, reliability, and maintainability.

## Features

1. **Temperature measurement (DS18B20)** — reads indoor and outdoor sensors, stores readings in SQLite. Errors are caught and logged without crashing.
2. **Weather & location** — fetches current conditions from `ipinfo.io` and `api.openweathermap.org`, displayed on LCD.
3. **Date, time & local IP** — shown on LCD in rotation.
4. **RGB LED control** — via IR remote or programmatic interface.
5. **IR remote support** — NEC protocol remote controls LEDs (color, brightness, effects).
6. **Accent stripping** — Polish and other diacritics converted to ASCII automatically (NFD Unicode normalization) for LCD compatibility.

## Hardware Requirements

- Raspberry Pi 4
- DS18B20 temperature sensor (1-Wire, GPIO4)
- 20×4 I2C LCD display (address `0x27`)
- NeoPixel LED strip (GPIO21)
- RGB LED (GPIO 16/12/26 PWM)
- IR receiver (GPIO20)
- Internet connection for weather data

## Installation

1. Clone the repository:
   ```bash
   git clone github.com/MrEmsii/RasberryPiOneFile
   cd RasberryPiOneFile
   ```

2. Install dependencies:
   ```bash
   pip install setproctitle w1thermsensor numpy requests psutil gpiozero
   pip install rpi_ws281x adafruit-circuitpython-neopixel
   pip install adafruit-blinka
   ```

   > **Important:** `board` comes from `adafruit-blinka`, not from a separate `board` package. Do not install both.

3. Place `API_LCD_I2C.py` in the `hardware/` folder.

4. Run:
   ```bash
   sudo python main.py
   ```

   Logs are written to `logs/app.log` and `logs/error.log`.

---

## Project Structure

```
RasberryPiOneFile/
├── main.py                     ← Orchestrator (init, start, shutdown, main loop)
│
├── core/
│   ├── events.py               ← EventBus + event types (EventType enum)
│   ├── state.py                ← AppState — thread-safe in-memory state
│   └── config.py               ← Only place that reads/writes config.json
│
├── hardware/
│   ├── API_LCD_I2C.py          ← I2C LCD driver (Denis Pleic, 2015)
│   ├── ir_controller.py        ← PRODUCER: IR sensor → emits events
│   ├── led_controller.py       ← CONSUMER: subscribes to events → drives LEDs
│   └── lcd_controller.py       ← CONSUMER: subscribes to LCD_ON/OFF → displays
│
├── services/
│   ├── producers.py            ← PRODUCERS: Temp, Weather, Location, LocalIP
│   ├── consumers.py            ← CONSUMERS: StateUpdater, ConfigPersister, DB, Scheduler
│   └── db_service.py           ← Only place that touches SQLite
│
└── utils/
    ├── logging_setup.py        ← Logging config (replaces Another.py)
    └── text.py                 ← Text utils: remove_accents (NFD-based)
```

---

## Architecture — Event-Driven / Producer-Consumer

```
┌─────────────────────────────────────────────────────────────────┐
│                          PRODUCERS                              │
│                                                                 │
│  [IR remote]         [DS18B20]         [OpenWeatherMap]         │
│  ir_controller       TemperatureP.     WeatherProducer          │
│       │                   │                   │                 │
│       ▼                   ▼                   ▼                 │
│  IR_COLOR_CHANGED    TEMP_ALL_UPDATED    WEATHER_UPDATED        │
│  IR_BRIGHTNESS_CH.                                              │
│  IR_EFFECT_CHANGED   [ipinfo.io]         [hostname -I]          │
│                      LocationP.          LocalIPProducer        │
│                           │                   │                 │
│                           ▼                   ▼                 │
│                    LOCATION_UPDATED       IP_UPDATED            │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                         EVENT BUS                               │
│                      (queue.Queue)                              │
│                                                                 │
│   Dispatcher thread receives events and calls handlers          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
┌───────────────┐  ┌──────────────┐  ┌──────────────┐
│ StateUpdater  │  │ConfigPersist.│  │DatabaseWriter│
│               │  │              │  │              │
│ Updates       │  │ Writes       │  │ Inserts into │
│ AppState      │  │ config.json  │  │ Heat.db      │
└───────┬───────┘  └──────────────┘  └──────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                          APP STATE                              │
│                                                                 │
│  LEDConfig          WeatherData       TemperatureData           │
│  ├ color            ├ city            ├ indoor                  │
│  ├ brightness       ├ temp_outside    └ outdoor                 │
│  ├ effects          ├ humidity                                  │
│  └ leds_speed       └ ...             NetworkData               │
│                                       ├ ip_home                │
│                                       └ ip_query               │
└───────────────────────────┬─────────────────────────────────────┘
                            │  (read via get_leds(), get_weather() etc.)
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
┌───────────────┐  ┌──────────────┐  ┌──────────────┐
│ LEDController │  │LCDController │  │  Scheduler   │
│               │  │              │  │              │
│ Effect loop   │  │ LCD pages    │  │ LCD ON/OFF   │
│ every 0.4s    │  │ every 3s     │  │ tick 1s      │
└───────────────┘  └──────────────┘  └──────────────┘
```

### Architecture principles

**1. Producer doesn't know the consumer**
```python
# IR Controller — knows nothing about LEDs
bus.emit(Event(EventType.IR_COLOR_CHANGED, {"color": 3}))
# That's it. ir_controller doesn't import led_controller.
```

**2. Consumer doesn't know the producer**
```python
# LED Controller — doesn't care where the event came from
def _on_color_changed(self, event: Event) -> None:
    state.update_leds(color=event.payload["color"])
    # Could come from IR, API, scheduler — doesn't matter
```

**3. Single writer per resource**
```python
# config.json  → ONLY ConfigPersister
# Heat.db      → ONLY DatabaseWriter
# AppState     → ONLY StateUpdater (via events)
```

**4. Hardware reads state, not events**
```python
# LED Controller — effect loop reads current state each iteration
leds = state.get_leds()   # thread-safe copy
if leds.effects == 1:
    self._effect_constant()
```

---

## Comparison with original code

| Problem | Original | Event-Driven |
|---------|----------|--------------|
| Race condition on config.json | Multiple threads write directly | Only ConfigPersister writes |
| Race condition on temperature_list | Global var without lock | AppState with RLock |
| SQL injection | `%s % tab` string interpolation | Table whitelist |
| NeoPixel recreated in loop | Created every 0.4s | Created once in `__init__` |
| No HTTP timeout | `requests.get()` hangs forever | `timeout=10` everywhere |
| No GPIO cleanup | No `finally`/cleanup | `finally` in `ir_controller.run()` |
| Accent stripping | Manual 554-char string (with errors) | Unicode NFD normalization |
| Logging | `Another.error_insert()` manual | Python `logging` + `RotatingFileHandler` |
| Debugging | `print()` | `logger.debug/info/error/exception` |

---

## Author

Emsii — [github.com/MrEmsii](https://github.com/MrEmsii)  
Original: 01.03.2024 — Refactored: 2025 - 2.Refactored 13.06.2026