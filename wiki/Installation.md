# Installation

## Prerequisites

- **Raspberry Pi 4** (4GB+ recommended)
- **Raspbian Bullseye or later** with `python3.9+`
- **Internet connection** (for weather API)

## Hardware Setup

### Wiring

| Device | GPIO Pin | Notes |
|--------|----------|-------|
| DS18B20 (1-Wire) | GPIO4 | Data pin, with 4.7kΩ pullup |
| I2C LCD (20×4) | SDA/SCL | Default address `0x27` |
| NeoPixel Data | GPIO21 | WS2812B strip |
| IR Receiver | GPIO20 | NEC protocol |
| RGB LED Red | GPIO16 (PWM) | Optional, test mode |
| RGB LED Green | GPIO26 (PWM) | Optional, test mode |
| RGB LED Blue | GPIO12 (PWM) | Optional, test mode |
| Fan PWM | GPIO21 | CPU cooling (optional) |
| Fan Power | GPIO16 | Enable/disable (optional) |

### Enabling Interfaces

Enable 1-Wire and I2C in `raspi-config`:

```bash
sudo raspi-config
# → Interfacing Options
#   → I2C (enable)
#   → One-Wire (enable)
# → Reboot
```

Verify:
```bash
# Check I2C device
ls /dev/i2c*
i2cdetect -y 1    # Should show your LCD at 0x27

# Check 1-Wire
ls /sys/bus/w1/devices/
# Should list 28-XXXX devices (DS18B20)
```

## Software Installation

### 1. Clone Repository

```bash
cd ~
git clone https://github.com/EmsiiDiss/emsii_lcd
cd emsii_lcd
```

### 2. Install System Dependencies

```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-dev i2c-tools libopenblas-dev
```

### 3. Install Python Dependencies

```bash
pip3 install --break-system-packages \
  setproctitle \
  w1thermsensor \
  numpy \
  requests \
  psutil \
  gpiozero \
  adafruit-blinka \
  adafruit-circuitpython-neopixel \
  smbus-cffi
```

> ⚠️ Note: `--break-system-packages` is required on Raspberry Pi OS due to PEP 668. Use a virtual environment if you prefer isolation.

### 4. Setup Configuration

Copy `API_LCD_I2C.py` to the `hardware/` folder:

```bash
# If you have it in /samba/python/RP_LCD/:
cp /samba/python/RP_LCD/API_LCD_I2C.py ./hardware/

# Or create a symlink if it's in a shared location
ln -s /path/to/API_LCD_I2C.py ./hardware/API_LCD_I2C.py
```

### 5. Create config.json

On first run, you'll be prompted for an OpenWeatherMap API key:

```bash
sudo python3 main.py
```

You'll see:
```
Podaj api_key z https://home.openweathermap.org/api_keys:
> YOUR_API_KEY_HERE
```

Paste your free API key from [openweathermap.org/api_keys](https://home.openweathermap.org/api_keys).

The program creates `config.json`:

```json
{
    "api_key": "your_key_here",
    "base_url": "http://api.openweathermap.org/data/2.5/weather?",
    "localization_url": "http://ipinfo.io/json",
    "city": "Rzeszow",
    "temp_outside": "",
    "current_pressure": "",
    "current_humidity": "",
    "info_weather": "",
    "IP_query": "",
    "IP_home": "",
    "color": 0,
    "brightness": 0.5,
    "effects": 0,
    "leds_speed": 1.0,
    "hour_start_LCD": 8,
    "hour_stop_LCD": 22,
    "time_update": ""
}
```

Edit as needed:
- `hour_start_LCD` / `hour_stop_LCD` — LCD backlight schedule (24-hour format)
- `color` — default LED color (0=off, 1-10=colors)
- `brightness` — LED brightness (0.0-0.8)

### 6. Run as Service (Optional)

Create a systemd service file for automatic startup:

```bash
sudo nano /etc/systemd/system/emsii-lcd.service
```

Paste:

```ini
[Unit]
Description=Emsii LCD — Raspberry Pi Display System
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=pi
ExecStart=/usr/bin/python3 /home/pi/emsii_lcd/main.py
Restart=on-failure
RestartSec=10s
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable emsii-lcd.service
sudo systemctl start emsii-lcd.service

# Check status
sudo systemctl status emsii-lcd.service

# View logs
sudo journalctl -u emsii-lcd.service -f
```

## Verification

### Check Python Installation

```bash
python3 --version    # Should be 3.9+
cd emsii_lcd && python3 -c "import main; print('OK')"
```

### Test Hardware

```bash
# Test I2C LCD
i2cdetect -y 1

# Test 1-Wire temperature
python3 -c "
import w1thermsensor
for sensor in w1thermsensor.W1ThermSensor.get_available_sensors():
    print(f'Sensor {sensor.id}: {sensor.get_temperature()}°C')
"

# Test GPIO
python3 -c "
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(16, GPIO.OUT)
GPIO.output(16, GPIO.HIGH)
print('GPIO16 set HIGH')
GPIO.cleanup()
"
```

### Run Application

```bash
cd ~/emsii_lcd
sudo python3 main.py
```

You should see:

```
2025-01-15 14:32:05  INFO     emsii_lcd.main — Emsii LCD starting up
2025-01-15 14:32:05  INFO     emsii_lcd.core.config — Config loaded from ...
2025-01-15 14:32:06  INFO     emsii_lcd.services.db_service — DB tables ready
2025-01-15 14:32:06  INFO     emsii_lcd.core.events — EventBus started
2025-01-15 14:32:06  INFO     emsii_lcd.services.consumers — Consumers registered
2025-01-15 14:32:06  INFO     emsii_lcd.main — Hardware threads started
2025-01-15 14:32:06  INFO     emsii_lcd.main — Main loop running
```

LCD backlight should turn on/off based on `hour_start_LCD` / `hour_stop_LCD`.

## Troubleshooting Installation

### `ModuleNotFoundError: No module named 'board'`

```bash
pip3 install --break-system-packages adafruit-blinka
```

### `RuntimeError: Failed to initialize PWM hardware`

Check GPIO permissions:

```bash
sudo usermod -a -G gpio pi
# Log out and back in
```

### I2C device not found

Verify I2C is enabled and device is connected:

```bash
sudo raspi-config  # Enable I2C
i2cdetect -y 1     # Should show your device
```

Default LCD address is `0x27`. If different, edit `core/state.py`:

```python
LCD_ADDRESS = 0x27  # Change if needed
```

### DS18B20 not detected

Verify 1-Wire is enabled:

```bash
ls /sys/bus/w1/devices/
# Should show 28-XXXX... entries

# If not, enable in raspi-config
sudo raspi-config
# → Interfacing Options → One-Wire
```

## Next Steps

- **[Configuration](Configuration)** — Customize config.json
- **[Usage](Usage)** — Operating the system
- **[Modules](Modules)** — Understanding each component
- **[Troubleshooting](Troubleshooting)** — Common issues
