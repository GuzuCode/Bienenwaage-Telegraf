#!/usr/bin/env python3
import json
import board
import adafruit_bme680

# I2C-Setup
i2c = board.I2C()
bme = adafruit_bme680.Adafruit_BME680_I2C(i2c)

# Optional: Meeresspiegel-Luftdruck anpassen (Standard: 1013.25 hPa)
# bme.sea_level_pressure = 1013.25

# Messwerte auslesen
data = {
    "temperature": bme.temperature,          # in °C
    "humidity": bme.relative_humidity,       # in %
    "pressure": bme.pressure,                # in hPa
    "gas_resistance": bme.gas                # in Ohm
}

print(json.dumps(data))