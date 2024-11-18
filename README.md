# Raspberry Pi Temperature Measurement Application

## Program Description

This program, written in Python, is designed to measure temperature using the DS18B20 temperature sensor and display it on an LCD connected to a Raspberry Pi 4 via the I2C interface. Additionally, it retrieves location and weather information using extreme-ip-lookup.com and api.openweathermap.org, presenting these details on the LCD display. The program allows for local character conversion, RGB LED control, and IRDA remote control functionalities.

## Program Features

1. **Temperature Measurement with DS18B20 Sensor:** The program reads temperature data from the DS18B20 sensor and stores it in an SQLite database. In case of sensor reading errors, the user is notified, and the error is caught and not considered during database storage.

2. **Location and Weather Information Retrieval:** Utilizing extreme-ip-lookup.com and api.openweathermap.org, the program fetches location details and current weather information of the Raspberry Pi's location. This data is displayed on the LCD.

3. **Date and Time Presentation:** The program displays the local date and time in UTC format.

4. **Local IP Address Display:** The LCD displays the device's IP address in the local network.

5. **Input Data Validation:** The program ensures the correctness of input data to the database. Sensor reading errors are caught and rectified to the extent possible, with the user being informed of any invalid data.

6. **RGB LED Control:** Capability to control RGB LEDs through the software interface.

7. **IRDA Remote Control Support:** The program enables Raspberry Pi control via an IRDA remote.

## Requirements

- Raspberry Pi 4
- DS18B20 temperature sensor
- I2C-enabled LCD display
- Internet access for location and weather data retrieval
- Python libraries (sqlite3, requests, smbus, etc.) - dependencies must be installed

## Installation and Execution

1. Clone the repository onto the Raspberry Pi.
2. Install necessary Python libraries.
    - setproctitle
    - w1thermsensor
    - numpy
    - libopenblas-dev
    - python3-pyaudio
    - rpi_ws281x adafruit-circuitpython-neopixel
    - adafruit-blinka
    
    !IMPORTANT!
    - board != adafruit-blinka

3. Run the main program file.

## Contribution

I encourage collaboration on this project! If you have ideas for new features, bug fixes, or suggestions, please get in touch or raise an issue in the Issues section.

## Author

Emsii
01.03.2024

---







