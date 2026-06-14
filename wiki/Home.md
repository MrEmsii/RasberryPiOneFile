# Emsii LCD — Home

Welcome to **Emsii LCD**, a refactored Raspberry Pi temperature monitoring and display system using an **Event-Driven / Producer-Consumer** architecture.

## What is Emsii LCD?

Emsii LCD is a Python application for Raspberry Pi 4 that:
- **Measures temperature** using DS18B20 sensors (1-Wire)
- **Displays data** on a 20×4 I2C LCD (date, time, temperature, weather, IP)
- **Controls RGB LEDs** — NeoPixel strip and PWM RGB LEDs via IR remote or software
- **Monitors CPU temperature** and controls a cooling fan via PWM
- **Fetches weather data** from OpenWeatherMap API
- **Logs everything** to rotating log files

Originally built in 2024, it was **refactored in 2025** to use an event-driven architecture, replacing spaghetti code and global variables with clean, thread-safe components.

## Quick Links

- **[Architecture](Architecture)** — Event-Driven / Producer-Consumer pattern
- **[Installation](Installation)** — Setup and dependencies
- **[Configuration](Configuration)** — config.json reference
- **[Modules](Modules)** — Detailed breakdown of each component
- **[Events](Events)** — Complete list of EventType and payload formats
- **[Troubleshooting](Troubleshooting)** — Common issues and solutions
- **[Development](Development)** — Contributing and extending

## Key Features

✅ **Thread-safe** — All shared state protected by locks  
✅ **No race conditions** — Only one writer per resource (config, DB, LEDs)  
✅ **Clean separation** — Producers emit events, consumers react (decoupled)  
✅ **Resilient** — Sensor errors caught and logged, system keeps running  
✅ **Debuggable** — Structured logging instead of `print()` statements  
✅ **Scalable** — Easy to add new producers/consumers without touching existing code  

## Project Status

- ✅ Core refactor complete
- ✅ Event-Driven architecture working
- ✅ LCD initialization bug fixed (respects hour_start/hour_stop on restart)
- ✅ Fan PWM controller integrated
- ✅ Polish character stripping (Unicode NFD-based)
- ✅ Comprehensive logging

## File Structure

```
emsii_lcd/
├── main.py                 ← Entry point & orchestrator
├── core/                   ← Core event system & state
│   ├── events.py           ← EventBus & EventType
│   ├── state.py            ← AppState (thread-safe)
│   └── config.py           ← config.json manager
├── hardware/               ← Physical device control
│   ├── ir_controller.py    ← IR remote (PRODUCER)
│   ├── led_controller.py   ← LEDs/NeoPixels (CONSUMER)
│   ├── lcd_controller.py   ← LCD display (CONSUMER)
│   ├── fan_controller.py   ← CPU temp & fan PWM
│   └── API_LCD_I2C.py      ← I2C LCD driver (external)
├── services/               ← Data producers & consumers
│   ├── producers.py        ← Temperature, Weather, Location, IP
│   ├── consumers.py        ← State, Config, DB, Scheduler
│   └── db_service.py       ← SQLite database
└── utils/                  ← Utilities
    ├── logging_setup.py    ← Logging configuration
    └── text.py             ← Text processing (accent removal)
```

## Architecture at a Glance

```
PRODUCERS                    EVENT BUS              CONSUMERS
(emit events)            (queue.Queue)         (handle events)
    │                         │                      │
    ├─ IR Remote ──────────┐  │  ┌────────────────── LCD Display
    ├─ DS18B20 ────────────┼──┼──┤─────────────────── LEDs
    ├─ Weather API ────────┼──┼──┤────────────────── Config Persister
    ├─ Location IP ────────┤  │  ├────────────────── Database Writer
    └─ CPU Temp ───────────┘  │  ├────────────────── State Updater
                               │  └────────────────── Scheduler
                               │
                        APP STATE (in-memory)
                        - LEDs (color, brightness, effects)
                        - Temperature (indoor, outdoor)
                        - Weather (city, temp, humidity)
                        - Network (IP home, IP query)
```

## Running the Application

```bash
cd emsii_lcd
sudo python main.py
```

Logs are written to `logs/app.log` (debug) and `logs/error.log` (errors).

## Author

**Emsii** — [github.com/EmsiiDiss](https://github.com/EmsiiDiss)  
Original: 01.03.2024 | Refactored: 2025
