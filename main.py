# pyright: reportMissingImports=false
# TVShow : animations Eyes (humeurs) au demarrage ; KEY1 (GP14) passe au programme suivant :
# Eyes -> PicoWeather -> Airflight -> Eyes ...
from machine import Pin, SPI
import gc
import sys
import time

import ili9341
import wifi
from xpt2046 import XPT2046

spi = SPI(0, baudrate=40_000_000, sck=Pin(18), mosi=Pin(19), miso=Pin(16))
tft = ili9341.ILI9341(spi, dc=Pin(22, Pin.OUT), cs=Pin(17, Pin.OUT), rst=Pin(21, Pin.OUT))
touch = XPT2046(spi, cs=Pin(20, Pin.OUT), irq=Pin(15, Pin.IN, Pin.PULL_UP))
KEY1 = Pin(14, Pin.IN, Pin.PULL_UP)

# La connexion WiFi demarre tout de suite et reste ouverte entre les programmes
wifi.start()
last_wifi_check = time.ticks_ms()

pressed = False


def stop():
    global pressed, last_wifi_check
    now = time.ticks_ms()
    if time.ticks_diff(now, last_wifi_check) > 1000:
        last_wifi_check = now
        wifi.tick()
    if KEY1.value() == 0:
        time.sleep_ms(30)
        if KEY1.value() == 0:
            pressed = True
    return pressed


def load(name):
    gc.collect()
    return __import__(name)


def unload(name):
    sys.modules.pop(name, None)
    gc.collect()


def run_module(name, *args):
    module = load(name)
    try:
        module.run(tft, *args)
    finally:
        del module
        unload(name)


def program_eyes():
    run_module("moods", stop)


def program_weather():
    run_module("weather", stop)


def program_airflight():
    run_module("airflight", stop, touch)


PROGRAMS = (program_eyes, program_weather, program_airflight)


def main():
    global pressed
    index = 0
    while True:
        pressed = False
        try:
            PROGRAMS[index]()
        except Exception as error:
            print("Erreur programme", index, type(error).__name__, error)
            time.sleep(2)
            if not pressed:
                continue
        # Attend le relachement de KEY1 avant de passer au suivant
        while KEY1.value() == 0:
            time.sleep_ms(20)
        time.sleep_ms(200)
        index = (index + 1) % len(PROGRAMS)


main()
