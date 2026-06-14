# Events

Complete reference of all EventTypes and their payloads. Events are the communication mechanism in the event-driven architecture.

## EventType Enum

All event types are defined in `core/events.py`:

```python
from core.events import EventType

# Usage
bus.emit(Event(EventType.IR_COLOR_CHANGED, {"color": 3}))
```

## IR Remote Events

### `IR_COLOR_CHANGED`

**Source:** `IRController` (button 0-9)  
**Payload:** `{"color": int}`  
**Consumers:** `StateUpdater` → `LEDController`

Change LED color.

```python
# Payload example
{"color": 3}  # Set to blue
{"color": 10} # Set to white
```

**Values:** 0=off, 1-10=colors (see [Configuration](Configuration) for color map)

---

### `IR_BRIGHTNESS_CHANGED`

**Source:** `IRController` (buttons `<<` / `>>`)  
**Payload:** `{"brightness": float}`  
**Consumers:** `StateUpdater` → `LEDController`

Adjust LED brightness with `±0.05` steps (clamped 0.01-0.8).

```python
{"brightness": 0.55}
```

---

### `IR_EFFECT_CHANGED`

**Source:** `IRController` (buttons `-` / `+`)  
**Payload:** `{"effects": int}`  
**Consumers:** `StateUpdater` → `LEDController`

Change LED animation effect.

```python
{"effects": 2}  # Staircase effect
```

**Values:** 0=off, 1=constant, 2=fade, 3=random, 4=rainbow

---

## Temperature Events

### `TEMP_ALL_UPDATED`

**Source:** `TemperatureProducer` (every 3 minutes)  
**Payload:** `{"indoor": float | None, "outdoor": float | None}`  
**Consumers:** `StateUpdater` → `DatabaseWriter`

Temperature readings from DS18B20 sensors. Values are already `-3.5°C` corrected.

```python
{"indoor": 22.5, "outdoor": 15.3}
{"indoor": 22.5, "outdoor": None}  # Outdoor sensor missing
```

---

### `CPU_TEMP_UPDATED`

**Source:** `CPUTemperatureProducer` (every 5 seconds)  
**Payload:** `{"temp": float}`  
**Consumers:** `FanDriver`

CPU temperature from `/sys/class/thermal/thermal_zone0/temp`.

```python
{"temp": 52.3}  # Celsius
```

---

## Weather & Network Events

### `WEATHER_UPDATED`

**Source:** `WeatherProducer` (every 2 minutes, during LCD hours)  
**Payload:** weather dict  
**Consumers:** `StateUpdater` → `ConfigPersister`

Weather data from OpenWeatherMap API.

```python
{
    "temp_outside": "12.5°C / 11.0°C",
    "current_pressure": "1013 hPa",
    "current_humidity": "72%",
    "info_weather": "scattered clouds",
    "time_update": "2025-01-15 14:32:05"
}
```

---

### `LOCATION_UPDATED`

**Source:** `LocationProducer` (every 5 minutes)  
**Payload:** `{"city": str, "ip_query": str}`  
**Consumers:** `StateUpdater` → `ConfigPersister`

Location and public IP from ipinfo.io.

```python
{"city": "Rzeszow", "ip_query": "1.2.3.4"}
```

---

### `IP_UPDATED`

**Source:** `LocalIPProducer` (every 5 minutes)  
**Payload:** `{"ip_home": str}`  
**Consumers:** `StateUpdater` → `ConfigPersister`

Local network IP address from `hostname -I`.

```python
{"ip_home": "192.168.1.100"}
```

---

## System Events

### `LCD_ON`

**Source:** `Scheduler` (at `hour_start_LCD`)  
**Payload:** `{"stop_at": datetime}`  
**Consumers:** `LCDController`

Turn on LCD backlight and start display loop.

```python
{"stop_at": datetime.datetime(2025, 1, 15, 22, 0)}  # Stop at 10 PM
```

---

### `LCD_OFF`

**Source:** `Scheduler` (at `hour_stop_LCD`)  
**Payload:** (empty)  
**Consumers:** `LCDController`

Turn off LCD backlight and stop display loop.

```python
{}
```

---

### `LEDS_OFF`

**Source:** `Scheduler` (at `hour_stop_LCD`)  
**Payload:** (empty)  
**Consumers:** `StateUpdater`

Turn off LEDs when LCD is disabled (energy saving).

```python
{}
```

---

### `SHUTDOWN`

**Source:** `main.py` (on SIGTERM/SIGINT)  
**Payload:** (empty)  
**Consumers:** `EventBus` (breaks dispatcher loop)

Graceful shutdown signal.

```python
{}
```

---

## Event Flow Example

### Scenario: Press remote button "3" (blue color)

```
1. User presses button on IR remote
   ↓
2. IRController.run() reads signal (GPIO20)
   ↓
3. Signal matches "3" button
   ↓
4. bus.emit(Event(EventType.IR_COLOR_CHANGED, {"color": 3}))
   ↓
5. Event enters EventBus queue
   ↓
6. EventBus dispatcher thread dequeues event
   ↓
7. StateUpdater._on_color handler:
   - state.update_leds(color=3)
   ↓
8. ConfigPersister._on_color handler:
   - config.save(state.to_dict())  # Write config.json
   ↓
9. LEDController reads state in its loop (every 0.4s):
   - leds = state.get_leds()  # color=3
   - self._fill(COLOR_PALETTE[3], brightness)  # Blue
   ↓
10. NeoPixel strip turns blue
```

Total latency: ~10-50ms (dispatcher + handler execution)

---

## Emitting Custom Events

To add your own producer:

```python
from core.events import bus, Event, EventType

# Create event
event = Event(EventType.SOME_EVENT, {"data": "value"})

# Emit
bus.emit(event)
```

To add a consumer:

```python
from core.events import bus, Event, EventType

class MyConsumer:
    def __init__(self):
        bus.subscribe(EventType.SOME_EVENT, self._handle)
    
    def _handle(self, event: Event) -> None:
        data = event.payload["data"]
        print(f"Received: {data}")
```

---

## Debugging Events

### Enable Debug Logging

Edit `utils/logging_setup.py`:

```python
root.setLevel(logging.DEBUG)  # Was logging.INFO
```

Run and watch logs:

```bash
sudo python3 main.py 2>&1 | grep -i "event"
```

Output:

```
14:32:06  DEBUG  emsii_lcd.core.events — Emitted: Event(IR_COLOR_CHANGED, {'color': 3})
14:32:06  DEBUG  emsii_lcd.services.consumers — State.leds.color = 3
14:32:06  DEBUG  emsii_lcd.services.consumers — ConfigPersister: saved
```

### List All Registered Handlers

In `core/events.py`, add debug method:

```python
def debug_handlers(self) -> None:
    for event_type, handlers in self._handlers.items():
        print(f"{event_type.name}: {[h.__qualname__ for h in handlers]}")

# Usage
from core.events import bus
bus.debug_handlers()
```

---

## Next Steps

- **[Modules](Modules)** — How each component uses events
- **[Architecture](Architecture)** — Event flow diagram
- **[Development](Development)** — Extending with new events
