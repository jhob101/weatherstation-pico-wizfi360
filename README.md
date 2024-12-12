# weatherstation-pico-wizfi360
Read values from BME280 and send to Weather Underground &amp; adafruit.io

## Installation

### Flash the Pico
Download the latest custom image (plain pico or pico version) from [Pimoroni's GitHub](https://github.com/pimoroni/pimoroni-pico/releases/latest)

Flash the Pico using the custom image

### Configure the scripts
- Rename `config.py.example` to `config.py`
- Add account details for adafruit.io & Weather Underground
- Rename `./lib/secrets.py.example` to `secrets.py`
- Add WiFi connection details

# Libraries used
- [WizFi AT control](https://github.com/Wiznet/WizFi360-EVB-Pico-MicroPython)
