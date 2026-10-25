# Connexion WiFi partagee : demarree par main.py, maintenue entre les programmes
import network
import time

try:
    import rp2
except ImportError:
    rp2 = None

import secrets

RETRY_MS = 20000

wlan = None
_nets = []
_idx = 0
_started = 0


def _begin():
    global _started
    ssid, pwd = _nets[_idx]
    wlan.disconnect()
    wlan.connect(ssid, pwd)
    _started = time.ticks_ms()


def start():
    """Lance la connexion sans bloquer (reseau de secours en premier s'il existe)."""
    global wlan, _nets, _idx
    # En France, ce reglage evite les problemes de canaux 12/13 avec certaines box.
    if rp2 is not None:
        rp2.country("FR")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    _nets = []
    if getattr(secrets, "LIVEBOX_WIFI_SSID", ""):
        _nets.append((secrets.LIVEBOX_WIFI_SSID, secrets.LIVEBOX_WIFI_PASSWORD))
    _nets.append((secrets.WIFI_SSID, secrets.WIFI_PASSWORD))
    _idx = 0
    if not wlan.isconnected():
        _begin()


def tick():
    """A appeler regulierement : relance la connexion (autre reseau) si elle echoue ou tombe."""
    global _idx
    if wlan is None or wlan.isconnected():
        return True
    failed = wlan.status() < 0 or time.ticks_diff(time.ticks_ms(), _started) > RETRY_MS
    if failed:
        _idx = (_idx + 1) % len(_nets)
        _begin()
    return False


def wait(timeout_s=60):
    """Attend la connexion ; retourne le WLAN ou None."""
    start_ms = time.ticks_ms()
    while not tick():
        if time.ticks_diff(time.ticks_ms(), start_ms) > timeout_s * 1000:
            return None
        time.sleep_ms(250)
    return wlan
