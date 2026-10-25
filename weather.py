# Meteo (OpenWeather) ; lance par main.py (run(display, stop))
import network
import time
import framebuf
import wifi

try:
    import rp2
except ImportError:
    rp2 = None

try:
    import urequests as requests
except ImportError:
    import requests

try:
    import uos as os
except ImportError:
    import os

try:
    import secrets
except ImportError:
    secrets = None

WIFI_SSID = getattr(secrets, "WIFI_SSID", "VOTRE_WIFI")
WIFI_PASSWORD = getattr(secrets, "WIFI_PASSWORD", "VOTRE_MOT_DE_PASSE")
LIVEBOX_WIFI_SSID = getattr(secrets, "LIVEBOX_WIFI_SSID", "")
LIVEBOX_WIFI_PASSWORD = getattr(secrets, "LIVEBOX_WIFI_PASSWORD", "")
OPENWEATHER_API_KEY = getattr(secrets, "OPENWEATHER_API_KEY", "VOTRE_API_KEY_OPENWEATHER")
LATITUDE = getattr(secrets, "LATITUDE", 47.0589)
LONGITUDE = getattr(secrets, "LONGITUDE", -0.8790)
UPDATE_INTERVAL_SECONDS = getattr(secrets, "WEATHER_UPDATE_INTERVAL_SECONDS", 600)
DISPLAY_INTERVAL_SECONDS = getattr(secrets, "DISPLAY_INTERVAL_SECONDS", 10)
FORECAST_EVENING_HOUR = getattr(secrets, "FORECAST_EVENING_HOUR", 18)
AFTERNOON_FORECAST_HOUR = getattr(secrets, "AFTERNOON_FORECAST_HOUR", 17)
TOMORROW_FORECAST_HOUR = getattr(secrets, "TOMORROW_FORECAST_HOUR", 14)
WIFI_SCAN_ATTEMPTS = getattr(secrets, "WIFI_SCAN_ATTEMPTS", 8)
WIFI_SCAN_DELAY_SECONDS = getattr(secrets, "WIFI_SCAN_DELAY_SECONDS", 2)
WIFI_CONNECT_TIMEOUT_SECONDS = getattr(secrets, "WIFI_CONNECT_TIMEOUT_SECONDS", 60)

WEATHER_ICON_DIR = "ressources"
WEATHER_ICON_SIZE = 100
ATMOSPHERE_CONDITIONS = (
    "MIST", "SMOKE", "HAZE", "DUST", "FOG", "SAND", "ASH", "SQUALL", "TORNADO",
)

tft = None

# Tampon complet 320x240 envoye d'un bloc : pas de scintillement
W, H = 320, 240
fb = framebuf.FrameBuffer(bytearray(W * H * 2), W, H, framebuf.RGB565)


def rgb(r, g, b):
    """RGB565 avec octets inverses (le bus SPI attend du big-endian)."""
    c = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    return ((c & 0xFF) << 8) | (c >> 8)


BLACK = rgb(0, 0, 0)
WHITE = rgb(255, 255, 255)
YELLOW = rgb(255, 220, 0)
CYAN = rgb(0, 220, 255)
GREEN = rgb(0, 255, 100)
RED = rgb(255, 60, 60)
BLUE = rgb(80, 120, 255)

ICON_CACHE_NAME = None
ICON_CACHE_FB = None


def trace(message):
    print("[trace]", message)


def sanitize_text(value):
    return "".join(c if 32 <= ord(c) < 127 else " " for c in str(value).upper())


def draw_text(x, y, text, fg=WHITE, bg=BLACK, scale=2):
    """Texte 8x8 agrandi, dessine dans le tampon."""
    text = sanitize_text(text)[: (W - x) // (8 * scale)]
    if not text:
        return
    w = 8 * len(text)
    mono = framebuf.FrameBuffer(bytearray(len(text) * 8), w, 8, framebuf.MONO_HLSB)
    mono.text(text, 0, 0, 1)
    for row in range(8):
        for col in range(w):
            if mono.pixel(col, row):
                fb.fill_rect(x + col * scale, y + row * scale, scale, scale, fg)


def flush():
    tft.blit(fb, 0, 0, W, H)


def weather_icon_name(main_condition):
    condition = str(main_condition).upper()
    if condition == "CLEAR":
        return "clearsky"
    if condition == "CLOUDS":
        return "cloudy"
    if condition in ("RAIN", "DRIZZLE", "THUNDERSTORM"):
        return "rain"
    if condition in ATMOSPHERE_CONDITIONS:
        return "haze"
    return "cloudy"


def load_weather_icon(icon_name):
    expected_pixels = WEATHER_ICON_SIZE * WEATHER_ICON_SIZE
    buffer = bytearray(expected_pixels * 2)
    icon_path = "{}/{}.py".format(WEATHER_ICON_DIR, icon_name)
    pixel_index = 0
    trace("Chargement icone meteo: {}".format(icon_path))
    try:
        icon_file = open(icon_path, "r")
    except OSError:
        raise RuntimeError("Icone {} introuvable".format(icon_path))
    with icon_file:
        for line in icon_file:
            if "0x" not in line:
                continue
            for token in line.split(","):
                value = token.strip()
                if not value.startswith("0x"):
                    continue
                if pixel_index >= expected_pixels:
                    raise RuntimeError("Trop de pixels dans {}".format(icon_path))
                color = int(value, 16)
                offset = pixel_index * 2
                buffer[offset] = color >> 8
                buffer[offset + 1] = color & 0xFF
                pixel_index += 1
    if pixel_index != expected_pixels:
        raise RuntimeError(
            "Image invalide {} ({} pixels / {})".format(
                icon_path, pixel_index, expected_pixels
            )
        )
    return buffer


def draw_icon(main_condition, x, y):
    global ICON_CACHE_NAME, ICON_CACHE_FB
    icon_name = weather_icon_name(main_condition)
    if ICON_CACHE_NAME != icon_name:
        ICON_CACHE_FB = None
        buffer = load_weather_icon(icon_name)
        ICON_CACHE_FB = framebuf.FrameBuffer(
            buffer, WEATHER_ICON_SIZE, WEATHER_ICON_SIZE, framebuf.RGB565
        )
        ICON_CACHE_NAME = icon_name
    fb.blit(ICON_CACHE_FB, x, y)


def show_message(title, detail, color=WHITE):
    fb.fill(BLACK)
    draw_text(10, 80, title, color, BLACK, 4)
    draw_text(10, 140, detail, WHITE, BLACK, 2)
    flush()


def wifi_status_label(status_code):
    mapping = {
        network.STAT_IDLE: "IDLE",
        network.STAT_CONNECTING: "CONNECTING",
        network.STAT_WRONG_PASSWORD: "WRONG PASSWORD",
        network.STAT_NO_AP_FOUND: "NO AP FOUND",
        network.STAT_CONNECT_FAIL: "CONNECT FAIL",
        network.STAT_GOT_IP: "GOT IP",
    }
    return mapping.get(status_code, "STATUS {}".format(status_code))


def build_wifi_networks():
    if not WIFI_SSID or WIFI_SSID == "VOTRE_WIFI":
        raise RuntimeError("Configure WIFI_SSID et WIFI_PASSWORD dans secrets.py")
    if not WIFI_PASSWORD or WIFI_PASSWORD == "VOTRE_MOT_DE_PASSE":
        raise RuntimeError("Configure WIFI_SSID et WIFI_PASSWORD dans secrets.py")
    if bool(LIVEBOX_WIFI_SSID) != bool(LIVEBOX_WIFI_PASSWORD):
        raise RuntimeError(
            "Configure LIVEBOX_WIFI_SSID et LIVEBOX_WIFI_PASSWORD dans secrets.py"
        )
    networks = []
    if LIVEBOX_WIFI_SSID:
        networks.append((LIVEBOX_WIFI_SSID, LIVEBOX_WIFI_PASSWORD))
    networks.append((WIFI_SSID, WIFI_PASSWORD))
    return networks


def scan_for_wifi(wlan, ssid):
    for _ in range(WIFI_SCAN_ATTEMPTS):
        visible = wlan.scan()
        ssids = [entry[0].decode("utf-8", "ignore") for entry in visible]
        if ssid in ssids:
            return True
        time.sleep(WIFI_SCAN_DELAY_SECONDS)
    return False


def connect_wifi_network(wlan, ssid, password):
    wlan.disconnect()
    time.sleep(0.3)
    if not scan_for_wifi(wlan, ssid):
        raise RuntimeError("{} introuvable (verifie 2.4 GHz)".format(ssid))

    show_message("WIFI", "CONNEXION", CYAN)
    print("Connexion WiFi:", ssid)
    wlan.connect(ssid, password)
    start = time.ticks_ms()
    timeout_ms = WIFI_CONNECT_TIMEOUT_SECONDS * 1000
    while not wlan.isconnected():
        status = wlan.status()
        if status in (
            network.STAT_WRONG_PASSWORD,
            network.STAT_NO_AP_FOUND,
            network.STAT_CONNECT_FAIL,
        ):
            raise RuntimeError("{} {}".format(ssid, wifi_status_label(status)))
        if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
            raise RuntimeError("{} ({})".format(ssid, wifi_status_label(status)))
        time.sleep(0.25)
    return ssid


def connect_wifi():
    wlan = wifi.wait(WIFI_CONNECT_TIMEOUT_SECONDS)
    if wlan is None:
        raise RuntimeError("WiFi indisponible")
    return wlan, "WiFi"


def api_get_json(kind, label):
    if not OPENWEATHER_API_KEY or OPENWEATHER_API_KEY == "VOTRE_API_KEY_OPENWEATHER":
        raise RuntimeError("Configure OPENWEATHER_API_KEY dans secrets.py")
    url = (
        "http://api.openweathermap.org/data/2.5/{}"
        "?lat={}&lon={}&appid={}&units=metric&lang=fr"
    ).format(kind, LATITUDE, LONGITUDE, OPENWEATHER_API_KEY)
    trace("Requete {}".format(label))
    response = requests.get(url)
    try:
        if response.status_code != 200:
            raise RuntimeError("{} HTTP {}".format(label, response.status_code))
        return response.json()
    finally:
        response.close()


def fetch_weather():
    payload = api_get_json("weather", "meteo")
    return {
        "city": payload.get("name", "LOCAL"),
        "main": payload["weather"][0]["main"],
        "temp_c": int(round(payload["main"]["temp"])),
        "humidity": int(payload["main"]["humidity"]),
        "wind_kmh": int(round(payload["wind"]["speed"] * 3.6)),
        "updated_at": int(payload.get("dt", 0) + payload.get("timezone", 0)),
    }


def format_hhmm(epoch_seconds):
    tm = time.gmtime(epoch_seconds)
    return "{:02d}:{:02d}".format(tm[3], tm[4])


def fetch_forecast(current_weather):
    payload = api_get_json("forecast", "previsions")
    timezone = int(payload["city"].get("timezone", 0))
    current_timestamp = current_weather["updated_at"]
    local_time = time.gmtime(current_timestamp)
    target_timestamp = current_timestamp
    forecast_label = "AUJOURD HUI"
    forecast_hour = AFTERNOON_FORECAST_HOUR
    if local_time[3] >= FORECAST_EVENING_HOUR:
        target_timestamp += 24 * 60 * 60
        forecast_label = "DEMAIN"
        forecast_hour = TOMORROW_FORECAST_HOUR
    target_date = time.gmtime(target_timestamp)

    closest_item = None
    closest_difference = None
    for item in payload["list"]:
        forecast_time = time.gmtime(int(item["dt"] + timezone))
        if forecast_time[:3] != target_date[:3]:
            continue
        difference = abs((forecast_time[3] * 60 + forecast_time[4]) - forecast_hour * 60)
        if closest_difference is None or difference < closest_difference:
            closest_item = item
            closest_difference = difference

    if closest_item is None:
        raise RuntimeError(
            "Aucune prevision pour le {:04d}-{:02d}-{:02d}".format(*target_date[:3])
        )

    return {
        "city": current_weather["city"],
        "main": closest_item["weather"][0]["main"],
        "temp_c": int(round(closest_item["main"]["temp"])),
        "humidity": int(closest_item["main"]["humidity"]),
        "wind_kmh": int(round(closest_item["wind"]["speed"] * 3.6)),
        "updated_at": current_weather["updated_at"],
        "label": forecast_label,
    }


def draw_weather_screen(weather, title):
    fb.fill(BLACK)
    draw_text(10, 10, title, GREEN, BLACK, 3)
    draw_icon(weather["main"], 10, 70)
    draw_text(125, 70, weather["city"], WHITE, BLACK, 2)
    draw_text(125, 96, weather["main"], YELLOW, BLACK, 2)
    draw_text(125, 130, "TEMP {}C".format(weather["temp_c"]), RED, BLACK, 3)
    draw_text(125, 164, "HUM {}%".format(weather["humidity"]), CYAN, BLACK, 2)
    draw_text(125, 190, "VENT {}KMH".format(weather["wind_kmh"]), BLUE, BLACK, 2)
    draw_text(10, 215, "MAJ {}".format(format_hhmm(weather["updated_at"])), WHITE, BLACK, 2)
    flush()


def sleep_or_stop(seconds, stop):
    """Attend sans bloquer le bouton ; True si l'appui a ete detecte."""
    end = time.ticks_add(time.ticks_ms(), int(seconds * 1000))
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        if stop():
            return True
        time.sleep_ms(50)
    return False


def run(display, stop):
    global tft
    tft = display
    show_message("METEO", "CONNEXION", GREEN)
    try:
        _, connected_ssid = connect_wifi()
    except RuntimeError as error:
        show_message("ERREUR", str(error), RED)
        while not sleep_or_stop(1, stop):
            pass
        return
    print("WiFi connecte:", connected_ssid)

    while True:
        try:
            weather = fetch_weather()
            forecast = fetch_forecast(weather)
            refresh_started = time.ticks_ms()
            while time.ticks_diff(time.ticks_ms(), refresh_started) < (
                UPDATE_INTERVAL_SECONDS * 1000
            ):
                draw_weather_screen(weather, "EN CE MOMENT")
                if sleep_or_stop(DISPLAY_INTERVAL_SECONDS, stop):
                    return
                draw_weather_screen(forecast, forecast["label"])
                if sleep_or_stop(DISPLAY_INTERVAL_SECONDS, stop):
                    return
        except (OSError, RuntimeError, KeyError, ValueError) as error:
            print("Erreur meteo ({}): {}".format(type(error).__name__, error))
            show_message("ERREUR", str(error), RED)
            if sleep_or_stop(DISPLAY_INTERVAL_SECONDS, stop):
                return
