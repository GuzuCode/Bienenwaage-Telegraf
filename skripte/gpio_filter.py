#!/usr/bin/env python3
import os
import sys

# pigpio als Pin-Backend verwenden
os.environ["GPIOZERO_PIN_FACTORY"] = "pigpio"

from gpiozero import Button

# GPIO16 mit Pull-Down (pull_up=False)
# Button führt von GPIO16 nach 3,3V
button = Button(16, pull_up=False)

# Lies Zeilen von stdin (Metriken) und schreibe sie nur, wenn Button nicht gedrückt
for line in sys.stdin:
    if not button.is_pressed:
        sys.stdout.write(line)