# Troubleshooting

Common issues and solutions.

## Application Won't Start

### Error: `ModuleNotFoundError: No module named 'board'`

**Cause:** Adafruit blinka not installed or installed incorrectly.

**Solution:**
```bash
pip3 install --break-system-packages adafruit-blinka
```

### Error: `RuntimeError: This module can only be run on a Raspberry Pi!`

**Cause:** Trying to run on non-Raspberry Pi hardware.

**Solution:** Run only on RPi 4+ with GPIO support. For development on desktop, mock the GPIO:

```bash
# Set mock mode
export GPIOZERO_PIN_FACTORY=mock
python3 main.py
```

### Error: `PermissionError: /dev/i2c-1: Permission denied`

**Cause:** I2C permissions issue.

**Solution:**
```bash
sudo usermod -a -G i2c pi
# Log out and back in
```

### Error: `FileNotFoundError: config.json not found`

**Cause:** Missing config file after fresh install.

**Solution:**
```bash
sudo python3 main.py  # Will prompt for API key and create config.json
```

---

## Hardware Issues

### LCD Not Displaying Anything

**Check 1:** LCD powered and backlight on?
```bash
i2cdetect -y 1
# Should show device at 0x27
```

**Check 2:** Correct address?
```bash
# If not 0x27, edit lcd_controller.py or hardware/API_LCD_I2C.py
i2cdetect -y 1  # Note the address shown
```

**Check 3:** Wiring correct?
- SDA → GPIO 2
- SCL → GPIO 3
- GND → GND
- VCC → 5V

---

### LCD Backlight On But No Text

**Cause:** Usually means initialization happened but content not being written.

**Check logs:**
```bash
sudo journalctl -u emsii-lcd.service -n 50 | grep -i lcd
```

**Likely issues:**
- LCD initialization failed silently (check `logs/error.log`)
- `API_LCD_I2C.py` not found (copied to `hardware/`?)
- Encoding issue with special characters (should be fixed in latest version)

**Solution:**
```bash
# Verify API_LCD_I2C.py is in hardware/
ls -la hardware/API_LCD_I2C.py

# Test manually
cd hardware && python3 -c "from API_LCD_I2C import lcd; l=lcd(); l.lcd_clear()"
```

---

### IR Remote Not Working

**Check 1:** Receiver module connected?
- Data pin → GPIO 20
- GND → GND
- VCC → 3.3V (not 5V, will damage Pi!)

**Check 2:** Module is receiving?
```bash
sudo apt-get install ir-keytable
sudo ir-keytable -t  # Point remote at receiver
# Should show key presses
```

**Check 3:** Correct protocol?
Emsii LCD expects NEC protocol. If your remote uses different (e.g., Sony, RC6), edit `hardware/ir_controller.py`.

---

### Temperature Sensor Not Detected

**Check 1:** 1-Wire enabled?
```bash
ls /sys/bus/w1/devices/
# Should show 28-XXXX... entries
```

If empty:
```bash
sudo raspi-config
# → Interfacing Options → One-Wire → Enable
# → Reboot
```

**Check 2:** Sensor connected correctly?
- DQ (data) → GPIO 4
- GND → GND
- VCC → 3.3V (with 4.7kΩ pullup from DQ to VCC)

**Check 3:** Test sensor directly:
```bash
python3 -c "
import w1thermsensor
for sensor in w1thermsensor.W1ThermSensor.get_available_sensors():
    print(f'ID: {sensor.id}, Temp: {sensor.get_temperature()}°C')
"
```

---

### Fan Not Running

**Check 1:** PWM signal present?
```bash
# GPIO21 should output PWM
gpio readall | grep 21
```

**Check 2:** Fan powered?
- PWM → GPIO 21
- Power (optional) → GPIO 16
- GND → GND

**Check 3:** Test fan directly:
```bash
python3 -c "
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(21, GPIO.OUT)
pwm = GPIO.PWM(21, 25000)
pwm.start(100)
print('Fan should run at 100%')
input('Press Enter to stop...')
pwm.stop()
GPIO.cleanup()
"
```

**Check 4:** CPU temperature above threshold?
```bash
cat /sys/class/thermal/thermal_zone0/temp
# If < 50000 (50°C), fan won't run
```

---

## LCD Schedule Issues

### LCD Stays On After hour_stop_LCD

**Known bug:** Fixed in latest version. Update:

```bash
cd ~/emsii_lcd
git pull
sudo systemctl restart emsii-lcd.service
```

**Manual fix:** Edit `services/consumers.py` and ensure `Scheduler._initialize_lcd_state()` is called.

### LCD Doesn't Turn On at hour_start_LCD

**Check:** Current time is within range?
```bash
date  # Check hour
cat config.json | grep hour_
```

**Check:** Scheduler is running?
```bash
sudo journalctl -u emsii-lcd.service | grep -i "scheduler"
```

**Fix:** Restart service:
```bash
sudo systemctl restart emsii-lcd.service
```

---

## Performance Issues

### High CPU Usage

**Check:** Which thread is consuming CPU?
```bash
top -p $(pgrep -f "python.*main.py")
# Press Shift+H to show threads
```

**Likely causes:**
- LED effect loop running continuously (check `hardware/led_controller.py`)
- Busy-wait in producer (add `time.sleep()`)
- Synchronous HTTP request blocking main thread (should be in producer thread)

---

### Slow LCD Update (>3 seconds)

**Cause:** LCD operations (write to I2C) are blocking.

**Check logs:**
```bash
tail -f logs/app.log | grep -i "lcd"
```

**Workaround:** Increase update interval in `lcd_controller.py`:
```python
segment_wait = 5  # Was 3 seconds
```

---

## Database Issues

### `OperationalError: database is locked`

**Cause:** Multiple threads trying to write simultaneously (shouldn't happen with single `DatabaseWriter`).

**Fix:** Kill any other processes accessing `Heat.db`:
```bash
lsof | grep Heat.db
kill -9 <PID>
sudo systemctl restart emsii-lcd.service
```

### Temperature Data Not Being Saved

**Check:** DatabaseWriter is registered?
```bash
sudo journalctl -u emsii-lcd.service | grep -i "database"
```

**Check:** Table exists?
```bash
sqlite3 Heat.db ".tables"
# Should show: temperatura, temperatura_outdoor
```

**Check:** Insert succeeding?
```bash
sqlite3 Heat.db "SELECT COUNT(*) FROM temperatura;"
# Should increment every few minutes
```

---

## Logging Issues

### Logs Not Being Written

**Check:** Directory permissions?
```bash
ls -la logs/
# Should be owned by pi:pi with 755
chmod 755 logs/
```

**Check:** Log level too high?
```bash
# In utils/logging_setup.py:
root.setLevel(logging.DEBUG)  # or INFO
```

### Logs Filling Up Disk

**Check:** Rotation is working?
```bash
ls -la logs/app.log*
# Should see app.log.1, app.log.2, etc. after 5MB each
```

**Manually clean:**
```bash
rm logs/app.log.*
# Keep only current logs
```

---

## Weather API Issues

### `401 Unauthorized` Error

**Cause:** Invalid or expired API key.

**Solution:**
1. Go to [openweathermap.org/api_keys](https://openweathermap.org/api_keys)
2. Generate new key
3. Update `config.json`:
   ```json
   {"api_key": "new_key_here"}
   ```
4. Restart application

### `404 City Not Found`

**Cause:** Location service couldn't determine city or OpenWeatherMap doesn't know it.

**Solution:** Manually set city in `config.json`:
```json
{"city": "Rzeszow"}
```

Restart and weather should fetch.

---

## Getting Help

### Collect Debug Info

Before reporting an issue:

```bash
# Logs
sudo journalctl -u emsii-lcd.service -n 100 > /tmp/emsii.log

# Config (redact API key!)
cat config.json > /tmp/config.txt

# Hardware
uname -a > /tmp/hw.txt
i2cdetect -y 1 >> /tmp/hw.txt
ls /sys/bus/w1/devices/ >> /tmp/hw.txt

# Zip and attach to issue
tar czf emsii-debug.tar.gz /tmp/emsii.log /tmp/config.txt /tmp/hw.txt
```

### Enabling Debug Logging

Edit `utils/logging_setup.py`:

```python
root.setLevel(logging.DEBUG)  # More verbose
```

Then:
```bash
sudo python3 main.py 2>&1 | tee debug.log
# Run for 30 seconds, then Ctrl+C
```

Share `debug.log` in issue report.

---

## Next Steps

- **[Installation](Installation)** — Reinstall from scratch
- **[Configuration](Configuration)** — Verify all settings
- **[Events](Events)** — Understand what should be happening
