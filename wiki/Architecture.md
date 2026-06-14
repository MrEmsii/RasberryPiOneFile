# Architecture

## Event-Driven / Producer-Consumer Pattern

Emsii LCD uses a **decoupled, event-driven architecture** where components communicate through events rather than direct function calls. This eliminates race conditions, improves testability, and makes the system resilient to changes.

### Core Concepts

#### **Producer**
A component that generates data and **emits events**.

Examples:
- `IRController` — reads remote button presses, emits `IR_COLOR_CHANGED`
- `TemperatureProducer` — reads DS18B20 sensors, emits `TEMP_ALL_UPDATED`
- `WeatherProducer` — fetches OpenWeatherMap, emits `WEATHER_UPDATED`
- `CPUTemperatureProducer` — reads `/sys/class/thermal/`, emits `CPU_TEMP_UPDATED`

#### **Consumer**
A component that **subscribes to events** and reacts to them.

Examples:
- `StateUpdater` — listens to all events, updates `AppState`
- `ConfigPersister` — listens to state changes, writes to `config.json`
- `DatabaseWriter` — listens to temperature events, inserts into `Heat.db`
- `LEDController` — listens to color/brightness events, adjusts LEDs
- `LCDController` — listens to `LCD_ON/LCD_OFF`, displays data

#### **Event Bus**
Central message queue (`queue.Queue`) with a dispatcher thread. Producers call `bus.emit()` and return immediately — they **never block waiting for consumption**.

Handlers are invoked sequentially in the dispatcher thread, so if a handler takes time, other events queue up but the producer is not affected.

#### **AppState**
Thread-safe in-memory state (protected by `RLock`). Hardware controllers read from it constantly, rather than being pushed updates via events.

Why? Because LCD needs to refresh every 0.4s, but we don't want to emit 2.5 events per second. Instead, LCD reads current state on demand.

### Event Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      PRODUCERS (threads)                        │
│                                                                 │
│  IRController      TemperatureP.      WeatherP.   CPUTempP.    │
│  (GPIO20)          (1-Wire)           (HTTP)      (/sys)       │
│  every 0.3s        every 180s         every 120s  every 5s     │
│       │                  │                 │           │        │
│       ▼                  ▼                 ▼           ▼        │
│  IR_COLOR_CHANGED  TEMP_ALL_UPDATED   WEATHER_    CPU_TEMP_    │
│  IR_BRIGHTNESS_    TEMP_OUTDOOR_      UPDATED     UPDATED      │
│  EFFECT_CHANGED    UPDATED                                      │
│       │                  │                 │           │        │
│       └──────────────────┴─────────────────┴───────────┘        │
│                          │                                      │
└──────────────────────────┼──────────────────────────────────────┘
                           ▼
           ┌───────────────────────────────┐
           │     EVENT BUS (queue)         │
           │                               │
           │  Dispatcher thread calls:     │
           │  1. StateUpdater handlers     │
           │  2. ConfigPersister handlers  │
           │  3. DatabaseWriter handlers   │
           └───────────────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        ┌──────────┐     ┌──────────┐     ┌──────────┐
        │StateUpd. │     │ConfigPer.│     │DatabaseW.│
        └────┬─────┘     └──────────┘     └──────────┘
             │
             ▼
        ┌──────────────────────────────────────┐
        │         APP STATE                    │
        │  (in-memory, thread-safe)            │
        │                                      │
        │  LEDConfig:   color, brightness     │
        │  TempData:    indoor, outdoor       │
        │  WeatherData: city, temp, humidity  │
        │  NetworkData: ip_home, ip_query     │
        └────────┬─────────────────┬──────────┘
                 │                 │
    ┌────────────┴─────┐  ┌────────┴──────────┐
    │ Continuous read  │  │ Event-driven      │
    │ (polling)        │  │ update (reactive) │
    ▼                  ▼  ▼                   ▼
  ┌─────────┐      ┌──────────┐      ┌──────────┐
  │ LEDCtrl │      │LCDCtrl   │      │FanDriver │
  │ Effect  │      │Display   │      │ PWM      │
  │ loop    │      │ loop     │      │ control  │
  │0.4s     │      │3s        │      │ (react)  │
  └─────────┘      └──────────┘      └──────────┘
```

### Architecture Principles

#### **1. Producers don't know consumers**
```python
# IR Controller — emits and forgets
bus.emit(Event(EventType.IR_COLOR_CHANGED, {"color": 3}))
# That's it. ir_controller never imports led_controller.
```

**Benefit:** You can add a new consumer (e.g., API endpoint, cloud sync) without touching the producer.

#### **2. Consumers don't know producers**
```python
# LED Controller — doesn't care where event came from
def _on_color_changed(self, event: Event) -> None:
    state.update_leds(color=event.payload["color"])
    # Could be IR, web API, scheduler — doesn't matter
```

**Benefit:** Event source can change without changing the consumer.

#### **3. Single writer per resource**
```
config.json  → ONLY ConfigPersister writes
Heat.db      → ONLY DatabaseWriter writes
AppState     → ONLY StateUpdater writes (via events)
```

**Benefit:** No race conditions, no file corruption, predictable behavior.

#### **4. Hardware reads state (polling), not events**
```python
# LED Controller loop — reads state continuously
while True:
    leds = state.get_leds()  # thread-safe copy
    if leds.effects == 1:
        self._effect_constant()
    time.sleep(0.4)
```

**Benefit:** High-frequency hardware operations (0.4s refresh) don't spam the event bus.

### Event Types Reference

Complete list in [`core/events.py`](../core/events.py). Common ones:

| Event | Source | Payload | Consumer |
|-------|--------|---------|----------|
| `IR_COLOR_CHANGED` | IRController | `{"color": int}` | StateUpdater → LEDController |
| `TEMP_ALL_UPDATED` | TemperatureProducer | `{"indoor": float, "outdoor": float}` | StateUpdater → DatabaseWriter |
| `WEATHER_UPDATED` | WeatherProducer | weather dict | StateUpdater → ConfigPersister |
| `CPU_TEMP_UPDATED` | CPUTemperatureProducer | `{"temp": float}` | FanDriver |
| `LCD_ON` | Scheduler | `{"stop_at": datetime}` | LCDController |
| `LCD_OFF` | Scheduler | - | LCDController |

### Thread Model

```
Main Thread              Dispatcher Thread          Hardware Threads
═══════════              ═════════════════          ════════════════

initialize()
  ↓
start_event_bus()  ────→ EventBus._dispatch_loop() [daemon]
  ↓
start_hardware()   ────→ IRController.run()        [daemon]
  ├─ LCDController │    ├─ TemperatureProducer    [daemon]
  ├─ LEDController │    ├─ WeatherProducer        [daemon]
  └─ FanDriver     │    └─ CPUTemperatureProducer [daemon]
  ↓                │
register_consumers()     (All producers emit events → bus → dispatcher)
  ↓                │
main_loop()        │     (Event handlers: StateUpdater, ConfigPersister,
  ├─ Scheduler     │      DatabaseWriter, LEDs, LCD react to events)
  │   tick() 1/s   │
  │                │
  └─ sleep(1)      │
                   ↓
                (on SIGTERM/KeyboardInterrupt)
                shutdown() — cleanly stop all threads
```

All daemon threads are cleanly stopped in `shutdown()`.

### Comparison with Original Code

| Aspect | Original | Event-Driven |
|--------|----------|--------------|
| Config writes | Multiple threads write directly to file | Only ConfigPersister writes |
| Temperature state | Global `temperature_list` variable | AppState with RLock |
| Temperature to DB | Hardcoded in Temp Producer | DatabaseWriter consumer |
| IR to LEDs | Direct function call (blocking) | Event → bus → LEDController |
| LCD initialization | Always tries to display | Respects LCD ON/OFF schedule |
| Logging | `Another.save_logs_to_file()` | Python `logging` module |
| Error handling | Custom decorators | Standard `try/except` + logging |
| Thread safety | None | RLock on shared state |
| Testability | Tightly coupled | Mock producers/consumers easily |

### Why Event-Driven?

✅ **Decoupling** — Components don't import each other  
✅ **Scalability** — Add new features without modifying existing code  
✅ **Thread-safety** — No race conditions on shared state  
✅ **Debuggability** — Every event is logged  
✅ **Resilience** — One consumer's error doesn't crash the producer  
✅ **Reusability** — Producers/consumers can be moved between projects  
