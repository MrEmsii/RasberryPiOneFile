# Development

Guide for contributing and extending Emsii LCD.

## Setting Up Development Environment

### Clone and Install Editable

```bash
git clone https://github.com/EmsiiDiss/emsii_lcd
cd emsii_lcd
pip3 install -e .  # Editable install
```

### Create a Feature Branch

```bash
git checkout -b feature/my-feature
```

## Adding a New Producer

Producers gather data and emit events. Example: adding a new weather source.

### 1. Define Event Type

Edit `core/events.py`:

```python
class EventType(Enum):
    # ... existing events ...
    CUSTOM_DATA_UPDATED = auto()  # New event
```

### 2. Create Producer Class

Create a new file `services/custom_producer.py`:

```python
import logging
import threading
from typing import Optional
from core.events import bus, Event, EventType

logger = logging.getLogger(__name__)

class CustomDataProducer(threading.Thread):
    """
    Fetches custom data and emits CUSTOM_DATA_UPDATED event.
    
    Runs in background thread with configurable interval.
    """
    
    def __init__(self, interval: float = 60.0):
        super().__init__(name="CustomData-Producer", daemon=True)
        self._interval = interval
        self._stop_event = threading.Event()
    
    def run(self) -> None:
        logger.info(f"Producer '{self.name}' started (interval={self._interval}s)")
        while not self._stop_event.is_set():
            try:
                data = self._fetch_data()
                bus.emit(Event(EventType.CUSTOM_DATA_UPDATED, {
                    "value": data,
                    "timestamp": datetime.datetime.now()
                }))
                logger.debug(f"Emitted: {data}")
            except Exception:
                logger.exception(f"Producer '{self.name}' error")
            
            self._stop_event.wait(timeout=self._interval)
        logger.info(f"Producer '{self.name}' stopped")
    
    def _fetch_data(self):
        """Implement data fetching logic."""
        # Example: query API, read sensor, calculate value
        return 42
    
    def stop(self) -> None:
        self._stop_event.set()
```

### 3. Add to Main

Edit `main.py`:

```python
from services.custom_producer import CustomDataProducer

def start_producers() -> list:
    producers = [
        # ... existing producers ...
        CustomDataProducer(interval=60),
    ]
    for p in producers:
        p.start()
    return producers
```

### 4. Register in Shutdown

Edit `main.py` shutdown:

```python
# Already handles all producers in the list:
for p in producers:
    p.stop()
    p.join(timeout=3)
```

## Adding a New Consumer

Consumers listen to events and perform actions. Example: logging temperature to cloud.

### 1. Create Consumer Class

Create `services/cloud_uploader.py`:

```python
import logging
from core.events import bus, Event, EventType
from core.state import state

logger = logging.getLogger(__name__)

class CloudUploader:
    """Uploads temperature data to cloud service."""
    
    def __init__(self, api_url: str):
        self.api_url = api_url
        self._register()
    
    def _register(self) -> None:
        """Subscribe to temperature events."""
        bus.subscribe(EventType.TEMP_ALL_UPDATED, self._on_temperature)
        logger.info("CloudUploader registered")
    
    def _on_temperature(self, event: Event) -> None:
        """Handle temperature update event."""
        temp = event.payload.get("indoor")
        if temp is None:
            return
        
        try:
            self._upload(temp)
        except Exception:
            logger.exception("Upload failed")
    
    def _upload(self, temperature: float) -> None:
        """Upload to cloud."""
        import requests
        data = {
            "temperature": temperature,
            "timestamp": datetime.datetime.now().isoformat(),
            "location": state.weather.city
        }
        response = requests.post(self.api_url, json=data, timeout=5)
        response.raise_for_status()
        logger.debug(f"Uploaded: {data}")
```

### 2. Register in Main

Edit `main.py`:

```python
from services.cloud_uploader import CloudUploader

def register_consumers() -> "Scheduler":
    state_updater = StateUpdater()
    config_persister = ConfigPersister()
    db_writer = DatabaseWriter()
    
    # Add custom consumer
    cloud_uploader = CloudUploader(api_url="https://mycloud.example.com/api/temp")
    
    scheduler = Scheduler()
    return scheduler
```

## Creating a Custom Event Type

### 1. Add to EventType Enum

`core/events.py`:

```python
class EventType(Enum):
    # ... existing ...
    MOTION_DETECTED = auto()      # payload: {"location": str}
    ALERT_TRIGGERED = auto()      # payload: {"alert_type": str, "severity": int}
```

### 2. Emit from Producer

```python
def _on_motion(self):
    bus.emit(Event(EventType.MOTION_DETECTED, {"location": "living_room"}))
```

### 3. Handle in Consumer

```python
def __init__(self):
    bus.subscribe(EventType.MOTION_DETECTED, self._on_motion)

def _on_motion(self, event: Event) -> None:
    location = event.payload["location"]
    logger.info(f"Motion detected at {location}")
```

## Extending Existing Components

### Add New LED Effect

Edit `hardware/led_controller.py`:

```python
def _effect_pulse(self, speed: float) -> None:
    """New effect: slow pulse."""
    for i in range(100):
        br = abs(50 - i) / 50  # 0→1→0
        self._fill(COLOR_PALETTE[self._current_color], br)
        time.sleep(0.01 * speed)

def run(self) -> None:
    leds = state.get_leds()
    
    # ... existing effects ...
    
    elif leds.effects == 5:
        self._effect_pulse(leds.leds_speed)
```

Update `core/state.py` to document the new effect.

### Add New LCD Page

Edit `hardware/lcd_controller.py`:

```python
def _page_uptime(self) -> None:
    """Display system uptime."""
    import subprocess
    uptime = subprocess.check_output(["uptime"]).decode().strip()
    self._lcd.lcd_display_string(uptime, 1)
    self._lcd.lcd_display_string("System Status", 2)
    time.sleep(5)

def _display_loop(self, stop_at):
    # ... existing loop ...
    elif i % 8 == 7:
        self._page_uptime()
```

## Testing

### Unit Testing

Create `tests/test_events.py`:

```python
import pytest
from core.events import EventBus, Event, EventType

def test_event_bus_emit_and_subscribe():
    bus = EventBus()
    bus.start()
    
    received = []
    
    def handler(event):
        received.append(event)
    
    bus.subscribe(EventType.TEMP_ALL_UPDATED, handler)
    bus.emit(Event(EventType.TEMP_ALL_UPDATED, {"indoor": 20.0}))
    
    # Give dispatcher time to process
    import time
    time.sleep(0.1)
    
    assert len(received) == 1
    assert received[0].payload["indoor"] == 20.0
    
    bus.stop()
```

Run tests:

```bash
pytest tests/ -v
```

### Manual Integration Testing

```bash
# Test with GPIO mocked
export GPIOZERO_PIN_FACTORY=mock
python3 main.py

# Should not fail on errors, just log them
```

## Code Style

Follow PEP 8:

```bash
pip3 install black flake8

# Format code
black .

# Check style
flake8 .
```

## Documentation

### Docstrings

Use Google-style docstrings:

```python
def calculate_checksum(data: bytes) -> int:
    """
    Calculate CRC16 checksum for data.
    
    Args:
        data: Input bytes
    
    Returns:
        CRC16 checksum value
    
    Raises:
        ValueError: If data is empty
    
    Example:
        >>> calculate_checksum(b'hello')
        12345
    """
    if not data:
        raise ValueError("Data cannot be empty")
    # implementation
```

### Comments

Use comments for WHY, not WHAT:

```python
# GOOD: Explains the reason
# CRC16 is required by the protocol, not for data validation
checksum = calculate_checksum(data)

# BAD: Repeats what code does
# Calculate checksum
checksum = calculate_checksum(data)
```

## Performance Considerations

### Avoid Blocking in Producers

❌ DON'T:
```python
def run(self):
    while True:
        # Long operation blocks producer
        response = requests.get(url)  # 2+ seconds
        bus.emit(event)
```

✅ DO:
```python
def run(self):
    while True:
        try:
            response = requests.get(url, timeout=10)
            bus.emit(event)
        except requests.Timeout:
            logger.warning("Request timed out")
        self._stop_event.wait(timeout=self._interval)
```

### Use Thread-Safe State

❌ DON'T:
```python
# Race condition: multiple threads accessing directly
global state
state["color"] = 3
```

✅ DO:
```python
# Thread-safe: use AppState methods
state.update_leds(color=3)
color = state.get_leds().color
```

## Submitting a Pull Request

1. **Fork the repo**
   ```bash
   gh repo fork EmsiiDiss/emsii_lcd --clone
   ```

2. **Create feature branch**
   ```bash
   git checkout -b feature/amazing-thing
   ```

3. **Make changes with tests**
   ```bash
   # Edit code
   # Add tests
   pytest tests/
   ```

4. **Commit with clear messages**
   ```bash
   git commit -m "Add new LED effect: pulse"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/amazing-thing
   # Open PR on GitHub
   ```

6. **PR should include:**
   - Description of changes
   - Motivation/use case
   - Any new dependencies
   - Test results
   - Screenshots if UI change

## Common Patterns

### Sensor Reading with Error Handling

```python
def _read_sensor(self) -> Optional[float]:
    try:
        with open("/path/to/sensor") as f:
            value = float(f.read().strip())
        return value
    except FileNotFoundError:
        logger.warning("Sensor file not found")
        return None
    except ValueError:
        logger.error("Sensor returned invalid value")
        return None
```

### Configuration Value with Default

```python
def get_setting(key: str, default=None):
    try:
        return state.__getattribute__(key)
    except AttributeError:
        logger.warning(f"Setting '{key}' not found, using default")
        return default
```

### Graceful Degradation

```python
def _setup_hardware(self):
    try:
        self._device = HardwareDevice()
    except Exception:
        logger.warning("Hardware not available, continuing in simulation mode")
        self._device = None
```

---

## Next Steps

- **[Architecture](Architecture)** — Understand the system
- **[Events](Events)** — All event types and payloads
- **[Modules](Modules)** — How to extend each component
