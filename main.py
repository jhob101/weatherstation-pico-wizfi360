from machine import Pin, I2C
import time
from breakout_bme280 import BreakoutBME280
import network
#import urequests
import json
import adafruit_requests as requests
import adafruit_wizfiatcontrol_socket as socket
import random
from adafruit_wizfiatcontrol import WizFi_ATcontrol
from config import (
    WIFI_SSID,
    WIFI_PASSWORD,
    ADAFRUIT_IO_USERNAME,
    ADAFRUIT_IO_KEY,
    AIO_BASE_URL,
    WU_URL,
    WU_STATION_ID,
    WU_STATION_PWD
)

# Configure I2C for BME280
i2c = I2C(1, sda=Pin(2), scl=Pin(3))  # Using GP2 (SDA) and GP3 (SCL)
bme = BreakoutBME280(i2c=i2c)

# Configure LED
led = Pin(25,Pin.OUT)

def connect_wifi():
    """Connect to WiFi network"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Connecting to WiFi...')
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        while not wlan.isconnected():
            time.sleep(1)
    print('WiFi connected!')
    print('Network config:', wlan.ifconfig())

def init_wizfi():
    debugflag = False

    TIME_BETWEEN_QUERY = 60  # in seconds

    # WizFi360 configuration
    PORT=1
    RX = 5
    TX = 4
    resetpin = 20
    rtspin = False

    UART_Tx_BUFFER_LENGTH = 1024
    UART_Rx_BUFFER_LENGTH = 1024*2

    uart = machine.UART(PORT, 115200, tx= machine.Pin(TX), rx= machine.Pin(RX), txbuf=UART_Tx_BUFFER_LENGTH, rxbuf=UART_Rx_BUFFER_LENGTH)
    wizfi = WizFi_ATcontrol( uart, 115200, reset_pin=resetpin, rts_pin=rtspin, debug=debugflag )

    return wizfi

def connect_wizfi(wizfi):
    try:
        from secrets import secrets
    except ImportError:
        print("Wi-Fi secrets are kept in secrets.py, please add them there!")
        raise

    #print("Resetting WizFi360 module")
    #wizfi.hard_reset()

    disconnect_wizfi(wizfi)

    wizfi.connect(secrets)
    requests.set_socket(socket, wizfi)

    print("Checking connection...")
    while not wizfi.is_connected:
        print("Connecting to AP...")
        wizfi.connect(secrets)
    print("Connected!")
    return True

def disconnect_wizfi(wizfi):
    print("Resetting WizFi360 module")
    wizfi.hard_reset()
    return True

def hpa_to_inches(pressure_in_hpa):
    """Convert hectopascals to inches of mercury"""
    return pressure_in_hpa * 0.02953

def degc_to_degf(temperature_in_c):
    """Convert Celsius to Fahrenheit"""
    return (temperature_in_c * (9 / 5.0)) + 32

def read_sensor():
    """Read temperature, pressure, and humidity from BME280"""
    try:
        temperature, pressure, humidity = bme.read()
        return temperature, pressure, humidity
    except Exception as e:
        print("Error reading sensor:", e)
        return None, None, None

def send_to_adafruit(feed_key, value):
    """Send data to Adafruit IO"""
    url = f"{AIO_BASE_URL}{ADAFRUIT_IO_USERNAME}/feeds/{feed_key}/data"
    headers = {
        'X-AIO-Key': ADAFRUIT_IO_KEY,
        'Content-Type': 'application/json'
    }
    data = {'value': value}


    try:
        response = requests.post(url, headers=headers, json=data)
        #response = urequests.post(url, headers=headers, json=data)
        print(f"Adafruit IO Update ({feed_key}):", response.status_code)
        response.close()
    except Exception as e:
        print(f"Error sending to Adafruit IO ({feed_key}):", e)

def send_to_weather_underground(temperature, pressure, humidity):
    """Send data to Weather Underground"""
    temp_str = "{0:.2f}".format(degc_to_degf(temperature))
    humidity_str = "{0:.2f}".format(humidity)
    pressure_str = "{0:.2f}".format(hpa_to_inches(pressure))

    payload = {
        'action': 'updateraw',
        'dateutc': 'now',
        'ID': WU_STATION_ID,
        'PASSWORD': WU_STATION_PWD,
        'realtime': 1,
        'rtfreq': 2.5,
        'tempf': temp_str,
        'humidity': humidity_str,
        'baromin': pressure_str
    }

    request_url = WU_URL
    querystring = []
    for key, value in payload.items():
        querystring.append(f"{key}={value}")

    request_url += "?" + "&".join(querystring)

    try:
        # response = urequests.get(WU_URL, params=payload)
        response = requests.get(request_url)
        print("Weather Underground Update:", response.status_code)
        response.close()
    except Exception as e:
        print("Error sending to Weather Underground:", e)

def main():
    wizfi = init_wizfi()

    while True:
        # Read sensor data
        led.value(1)
        temperature, pressure, humidity = read_sensor()
        led.value(0)

        if all((temperature, pressure, humidity)):
            #temperature = random.randint(-10,30)
            print(f'{temperature:05.1f}°C {pressure:05.1f}hPa {humidity:05.1f}%')

            # Weird stuff happens if the connection isn't re-established with each request.
            # WizFi wifi seems a bit janky...

            # Send data to Weather Underground
            try:
                connect_wizfi(wizfi)
                time.sleep(2)  # Small delay between requests
                led.value(1)
                send_to_weather_underground(temperature, pressure, humidity)
                led.value(0)
            except Exception as e:
                print("Error in Weather Underground update:", e)

            # Send data to Adafruit IO
            sensor_data = [
                ('ptemperature', temperature),
                ('ppressure', pressure),
                ('phumidity', humidity)
            ]

            for feed_key, value in sensor_data:
                try:
                    connect_wizfi(wizfi)
                    time.sleep(2)  # Small delay between requests
                    led.value(1)
                    send_to_adafruit(feed_key, value)
                    led.value(0)
                except Exception as e:
                    print(f"Error in Adafruit IO update for {feed_key}:", e)

        disconnect_wizfi(wizfi)

        # Wait before next reading (5 minutes)
        time.sleep(300)

if __name__ == '__main__':
    main()
