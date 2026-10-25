# TVShow - Pico 2 W + écran ILI9341 320x240 (câblage Airflight)

Trois programmes en rotation, au démarrage sur les animations Eyes :

1. **Eyes** : carrousel des neuf humeurs animées (`moods.py`, issu de `moods_test.py`), en boucle.
2. **PicoWeather** (`weather.py`) : météo actuelle et prévision.
3. **Airflight** (`airflight.py`) : radar des avions.

**KEY1 (GP14, broche 19)** passe au programme suivant : Eyes → PicoWeather → Airflight → Eyes…
Dans Airflight, KEY1 ne sert donc plus à « avion suivant » (le tactile, KEY2 et KEY3 restent actifs).

Câblage : voir le [BRANCHEMENTS.md d'Airflight](../Airflight/BRANCHEMENTS.md).

## Installation
1. Copier `secrets_example.py` en `secrets.py` et le remplir (WiFi, clé OpenWeather, position, `TZ_OFFSET_HOURS`).
2. Copier sur le Pico : `main.py`, `moods.py`, `weather.py`, `airflight.py`, `ili9341.py`,
   `xpt2046.py`, `secrets.py` et le dossier `ressources/`.

Un seul programme est chargé en mémoire à la fois (150 Ko de tampon écran chacun).
