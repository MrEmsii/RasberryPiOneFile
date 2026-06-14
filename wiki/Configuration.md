# Configuration

Configuration is stored in `config.json` in the project root. The file is created automatically on first run and updated by the application as settings change.

## config.json Reference

### API Configuration

```json
{
  "api_key": "your_openweathermap_key_here",
  "base_url": "http://api.openweathermap.org/data/2.5/weather?",
  "localization_url": "http://ipinfo.io/json"
}
```

**`api_key`** (required)
- OpenWeatherMap free tier API key
- Get it at [openweathermap.org/api_keys](https://openweathermap.org/api_keys)
- Required for weather data fetching

**`base_url`**
- OpenWeatherMap API endpoint (don't change unless using custom server)

**`localization_url`**
- IP geolocation service (determines city automatically)
- Default: `ipinfo.io` (free, no auth required)

### Display Schedule

```json
{
  "hour_start_LCD": 8,
  "hour_stop_LCD": 22
}
```

**`hour_start_LCD`** (default: `8`)
- Hour when LCD backlight turns **on** (24-hour format)
- Example: `8` = 08:00 AM

**`hour_stop_LCD`** (default: `22`)
- Hour when LCD backlight turns **off** (24-hour format)
- Example: `22` = 10:00 PM

**Behavior:**
- Between `hour_start_LCD` and `hour_stop_LCD` → LCD is on
- Outside this range → LCD is off (backlight disabled, no display)
- Changes take effect on the next full hour

**Example:** `8` to `22` = display active 8 AM to 10 PM

### LED Control

```json
{
  "color": 0,
  "brightness": 0.5,
  "effects": 0,
  "leds_speed": 1.0
}
```

**`color`** (0-10)
- 0 = off
- 1 = red
- 2 = green
- 3 = blue
- 4 = orange
- 5 = lime
- 6 = magenta
- 7 = purple
- 8 = dark green
- 9 = cyan
- 10 = white

**`brightness`** (0.01-0.8)
- 0.01 = very dim
- 0.5 = medium (default)
- 0.8 = maximum (hardware limit to prevent oversaturation)

**`effects`** (0-4)
- 0 = off (LEDs dark)
- 1 = constant color (no animation)
- 2 = brightness staircase (fade in/out)
- 3 = random color staircase
- 4 = rainbow cycle (full spectrum)

**`leds_speed`** (0.5-4.0)
- Multiplier for animation speed
- 1.0 = normal speed
- 0.5 = half speed (slower)
- 2.0 = double speed (faster)

### Data Persistence

```json
{
  "city": "Rzeszow",
  "temp_outside": "12.5°C / 11.0°C",
  "current_humidity": "72%",
  "current_pressure": "1013 hPa",
  "info_weather": "scattered clouds",
  "IP_query": "1.2.3.4",
  "IP_home": "192.168.1.100",
  "time_update": "2025-01-15 14:32:05"
}
```

These are **read-only** from your perspective — the application updates them automatically:
- `city`, `temp_outside`, `info_weather` — updated by WeatherProducer
- `IP_query` — from ipinfo.io (your public IP)
- `IP_home` — from `hostname -I` (LAN IP)
- `time_update` — timestamp of last weather fetch

## Editing config.json

### Stop the Application

```bash
sudo systemctl stop emsii-lcd.service
# Or press Ctrl+C if running manually
```

### Edit the File

```bash
nano config.json
```

### Common Changes

**Change display schedule:**
```json
{
  "hour_start_LCD": 6,   // Turn on at 6 AM
  "hour_stop_LCD": 23    // Turn off at 11 PM
}
```

**Set default LED color:**
```json
{
  "color": 3,            // Blue
  "effects": 1           // Constant (no animation)
}
```

**Adjust brightness:**
```json
{
  "brightness": 0.7      // Slightly brighter
}
```

### Restart Application

```bash
sudo systemctl start emsii-lcd.service
# Or run manually to see logs:
sudo python3 main.py
```

Changes take effect immediately (most) or on next hour boundary (LCD schedule).

## Advanced Configuration

### Custom API Keys

If using a different weather service:

```json
{
  "api_key": "your_custom_key",
  "base_url": "https://api.custom-weather.example.com/v2/weather?"
}
```

### Sunrise/Sunset Based Schedule

Currently the app uses fixed hours. To use sunrise/sunset:

1. **Option A:** Use `hour_start_LCD` and `hour_stop_LCD` as approximations
2. **Option B:** Calculate in advance and update `config.json` periodically
3. **Option C:** Extend the code to use a sunrise/sunset library (PR welcome!)

### Fan Control Thresholds

Fan control is hardcoded in `hardware/fan_controller.py`:

```python
FAN_OFF_TEMP = 48    # Turn off below 48°C
FAN_LOW_TEMP = 52    # Turn on below 52°C (LOW speed)
HYSTERESIS = 2       # 2°C margin to prevent oscillation
```

To customize, edit the file and restart.

## Troubleshooting Configuration

### "API error: 401 Unauthorized"

Your OpenWeatherMap API key is invalid or expired. Regenerate at [openweathermap.org/api_keys](https://openweathermap.org/api_keys).

### "Location not found"

The ipinfo.io service returned an unrecognized location. Either:
- Your Pi has no internet connection
- The service is down (try again later)
- Manual edit: Set `city` directly in `config.json`

### "City is empty after startup"

The location producer runs every 5 minutes. Wait a bit, or manually set:

```json
{
  "city": "Rzeszow"
}
```

### LCD not turning off at hour_stop_LCD

This was a known bug, fixed in the latest refactor. Make sure you're running the updated code:

```bash
cd ~/emsii_lcd
git pull
sudo systemctl restart emsii-lcd.service
```

If LCD still doesn't turn off, check logs:

```bash
sudo journalctl -u emsii-lcd.service -n 50 | grep -i lcd
```

## File Permissions

`config.json` should be readable/writable by the `pi` user:

```bash
chmod 644 config.json
chown pi:pi config.json
```

If running as root (via `sudo`), permissions are automatic.

## Backing Up Configuration

```bash
cp config.json config.json.backup
```

Restore:

```bash
cp config.json.backup config.json
sudo systemctl restart emsii-lcd.service
```

## Next Steps

- **[Usage](Usage)** — Operating the system
- **[Events](Events)** — Understanding what triggers what
- **[Troubleshooting](Troubleshooting)** — Common issues
