import board
import neopixel
from time import sleep
import colorsys

# Anzahl der LEDs und Pin festlegen
NUM_PIXELS = 1  # Anzahl der LEDs (bei einer einzelnen RGB-LED auf 1 setzen)
PIN = board.D10  # Pin, an den die Datenleitung der WS2812B angeschlossen ist

# LED-Streifen initialisieren
pixels = neopixel.NeoPixel(PIN, NUM_PIXELS, brightness=0.5, auto_write=False)

def set_color(r, g, b):
    """Setzt die Farbe der WS2812B-LED."""
    pixels[0] = (int(r * 255), int(g * 255), int(b * 255))
    pixels.show()

def rainbow_cycle(duration=0.1):
    """Lässt die RGB-LED in Regenbogenfarben leuchten."""
    for i in range(360):
        # Umwandlung von HSV (Hue, Saturation, Value) zu RGB
        hue = i / 360.0
        r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
        set_color(r, g, b)
        sleep(duration)

try:
    while True:
        rainbow_cycle()
except KeyboardInterrupt:
    # Farben ausschalten, wenn das Skript beendet wird
    set_color(0, 0, 0)
    print("Programm beendet")