#!/usr/bin/env python3
from gpiozero import Button
import time

# GPIO16 mit internem Pull-Down:
# Pin ist normalerweise LOW (0)
# Beim Drücken wird Pin auf 3,3V gezogen und somit HIGH (1)
button = Button(16, pull_up=False)

try:
    while True:
        if button.is_pressed:
            print("1")
        else:
            print("0")
        time.sleep(0.5)
except KeyboardInterrupt:
    pass