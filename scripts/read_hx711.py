#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time
import sys
import RPi.GPIO as GPIO
from hx711 import HX711
import logging

# Konfigurationsdateien und Pins
CALIBRATION_FILE = "/etc/telegraf/waage_calibration.json"
STATE_FILE = "/tmp/waage_state.json"  # Temporärer Speicherort
DOUT_PIN = 5
SCK_PIN = 6

# Temperaturkompensation
TEMP_SENSOR_PATH = "/sys/bus/w1/devices/28-5c80211864ff/w1_slave"

# Glättungsparameter
OUTLIER_THRESHOLD = 3  # Faktor für Ausreißererkennung
CHANGE_THRESHOLD = 3    # Anzahl der aufeinanderfolgenden Ausreißer zur Anerkennung einer Änderung

# Anpassungsparameter für smoothed_weight
INITIAL_STEP_SIZE = 0.2  # Startschrittgröße in Gramm
STEP_INCREMENT = 0.5      # Schrittgrößen-Inkrement in Gramm
MAX_STEP_SIZE = 5.0       # Maximale Schrittgröße in Gramm

# Logging konfigurieren
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Funktionen
def read_state():
    """Lädt den letzten Zustand aus der Datei."""
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "last_valid_weight": None,
            "smoothed_weight": None,
            "change_counter": 0,
            "previous_delta": None,
            "step_size": INITIAL_STEP_SIZE
        }

def save_state(state):
    """Speichert den aktuellen Zustand in die Datei."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def read_temp(sensor_path):
    """Liest die Temperatur von einem DS18B20-Sensor aus."""
    try:
        with open(sensor_path, "r") as f:
            lines = f.readlines()
        if "YES" not in lines[0]:
            return None
        temp_pos = lines[1].find("t=")
        if temp_pos != -1:
            temp_string = lines[1][temp_pos + 2:]
            return float(temp_string) / 1000.0
    except Exception:
        return None

def is_plausible(weight, min_weight=0, max_weight=50000):
    """Überprüft, ob das Gewicht innerhalb eines plausiblen Bereichs liegt."""
    return min_weight <= weight <= max_weight

def main():
    GPIO.setwarnings(False)
    logging.info("Starte Gewichtsmessung.")

    # Kalibrierwerte laden
    try:
        with open(CALIBRATION_FILE, "r") as f:
            calib = json.load(f)
        reference_unit = calib["reference_unit"]
        offset = float(calib["offset"])  # Sicherstellen, dass Offset ein Float ist
        temp_coefficient = calib["temp_coefficient"]
        reference_temp = calib["reference_temp"]
    except Exception as e:
        logging.error(f"Fehler beim Laden der Kalibrierungsdatei: {e}")
        sys.exit(1)

    # State laden
    state = read_state()
    last_valid_weight = state.get("last_valid_weight")
    smoothed_weight = state.get("smoothed_weight")
    change_counter = state.get("change_counter", 0)
    previous_delta = state.get("previous_delta", None)
    step_size = state.get("step_size", INITIAL_STEP_SIZE)

    # Plausibilitätsprüfung
    if last_valid_weight is not None and not is_plausible(last_valid_weight):
        logging.warning("Unplausibler last_valid_weight erkannt. Zustand wird zurückgesetzt.")
        last_valid_weight = None
        smoothed_weight = None
        change_counter = 0
        previous_delta = None
        step_size = INITIAL_STEP_SIZE

    # HX711 initialisieren
    try:
        hx = HX711(DOUT_PIN, SCK_PIN, gain=128)
        hx.set_reading_format("MSB", "MSB")
        hx.set_reference_unit(reference_unit)
        hx.reset()
        hx.set_offset(offset)
    except Exception as e:
        logging.error(f"Fehler bei der HX711-Initialisierung: {e}")
        sys.exit(1)

    # Temperatur lesen
    current_temp = read_temp(TEMP_SENSOR_PATH)
    if current_temp is None:
        logging.warning("Temperatur konnte nicht gelesen werden. Verwende Referenztemperatur.")
        current_temp = reference_temp  # Fallback

    # Gewicht messen (Anzahl der Messungen sicherstellen, dass es ein Integer ist)
    num_measurements = 31  # Anzahl der Messungen definieren

    try:
        # Option 1: Verwenden von get_weight_A(), wenn verfügbar
        try:
            values = [hx.get_weight_A() for _ in range(num_measurements)]
        except AttributeError:
            # Option 2: Manuelle Kalibrierung, wenn get_weight_A() nicht verfügbar ist
            raw_values = [hx.get_value_A() for _ in range(num_measurements)]
            values = [(v - offset) / reference_unit for v in raw_values if v is not None]

        values = [v for v in values if v is not None]  # Ungültige Werte filtern

        if not values:
            raise ValueError("Keine gültigen Messwerte erhalten")

        # Median berechnen
        values.sort()
        midpoint = len(values) // 2
        if len(values) % 2 == 0:
            weight_raw = (values[midpoint - 1] + values[midpoint]) / 2
        else:
            weight_raw = values[midpoint]

        logging.debug(f"Raw Weight: {weight_raw} g")
    except Exception as e:
        logging.error(f"Fehler bei der Gewichtsmessung: {e}")
        GPIO.cleanup()
        sys.exit(1)

    # Temperaturkompensation anwenden
    temp_adjustment = (current_temp - reference_temp) * temp_coefficient * weight_raw
    weight_corrected = weight_raw + temp_adjustment
    logging.debug(f"Temperaturkompensation: {temp_adjustment} g")
    logging.debug(f"Gewicht nach Kompensation: {weight_corrected} g")

    # Initialisierung der Glättungsparameter, falls nicht vorhanden
    if smoothed_weight is None:
        smoothed_weight = weight_corrected
        previous_delta = None
        step_size = INITIAL_STEP_SIZE
        logging.info("Zustand initialisiert mit dem aktuellen Gewicht.")
    else:
        delta = weight_corrected - smoothed_weight
        abs_delta = abs(delta)

        logging.debug(f"Delta: {delta} g")
        logging.debug(f"Before adjustment - step_size: {step_size} g, delta: {delta} g, previous_delta: {previous_delta} g")

        if abs_delta > 20.0:
            # Signifikante Gewichtsänderung
            change_counter += 1
            logging.warning(f"Signifikante Gewichtsänderung erkannt. Zähler erhöht auf {change_counter}.")

            if change_counter >= CHANGE_THRESHOLD:
                logging.info("Änderung als gültig erkannt. Aktualisiere smoothed_weight.")
                smoothed_weight = weight_corrected
                last_valid_weight = weight_corrected
                change_counter = 0
                step_size = INITIAL_STEP_SIZE
                previous_delta = None  # Reset previous_delta nach Änderung
            else:
                logging.debug("Änderung noch nicht signifikant genug. smoothed_weight bleibt unverändert.")
        elif abs_delta <= 20.0:
            # Messung innerhalb von ±20 g, unabhängig von der genauen Abweichung
            logging.info("Messung innerhalb von ±20 g. Zurücksetzen des change_counters.")
            change_counter = 0  # Reset des Counters

            if abs_delta > 5.0:
                logging.info("Abweichung zwischen 5 g und 20 g. Keine Anpassung des smoothed_weight.")
                # Keine Anpassung des smoothed_weight
            elif 0.1 <= abs_delta <= 5.0:
                # Hier implementieren wir die neuen Bedingungen
                if abs_delta <= 0.5:
                    # Fall 1: Abweichung innerhalb von ±0,5 g
                    step_size = INITIAL_STEP_SIZE
                    logging.debug("Abstand innerhalb von ±0,5 g erkannt. Schrittgröße auf 0,2 g zurückgesetzt. Keine Anpassung des smoothed_weight.")
                elif previous_delta is not None and (delta * previous_delta) < 0:
                    # Fall 2: Richtungswechsel
                    step_size = INITIAL_STEP_SIZE
                    logging.debug("Richtungswechsel erkannt. Schrittgröße auf 0,2 g zurückgesetzt.")
                    # Anpassung mit initialer Schrittgröße
                    step = step_size if delta > 0 else -step_size
                    smoothed_weight += step
                    logging.debug(f"smoothed_weight angepasst um {step} g auf {smoothed_weight} g.")
                elif previous_delta is not None and abs_delta >= previous_delta:
                    # Schrittgröße erhöhen, wenn aktuelle Abweichung größer oder gleich der vorherigen ist
                    step_size = min(step_size + STEP_INCREMENT, MAX_STEP_SIZE)
                    logging.debug(f"Abstand gleich oder größer als vorheriger. Schrittgröße erhöht auf {step_size} g.")
                    # Anpassung mit erhöhter Schrittgröße
                    step = step_size if delta > 0 else -step_size
                    smoothed_weight += step
                    logging.debug(f"smoothed_weight angepasst um {step} g auf {smoothed_weight} g.")
                else:
                    # Schrittgröße zurücksetzen auf initial
                    step_size = INITIAL_STEP_SIZE
                    logging.debug(f"Abstand kleiner als vorheriger oder erster Schritt. Schrittgröße zurückgesetzt auf {step_size} g.")
                    # Anpassung mit initialer Schrittgröße
                    step = step_size if delta > 0 else -step_size
                    smoothed_weight += step
                    logging.debug(f"smoothed_weight angepasst um {step} g auf {smoothed_weight} g.")
            elif abs_delta < 0.1:
                logging.debug("Delta kleiner als 0,1 g. Keine Änderung des smoothed_weight.")
                # Keine Änderung des smoothed_weight

        else:
            # Alle anderen Fälle (nicht erwartet, da abs_delta entweder >20 oder <=20)
            logging.debug("Delta außerhalb der definierten Bereiche. smoothed_weight bleibt unverändert.")
            change_counter = 0  # Reset des Counters

        # Aktualisiere previous_delta nur, wenn eine Anpassung stattgefunden hat
        if 0.1 <= abs_delta <= 5.0 or abs_delta > 5.0:
            previous_delta = abs_delta
            logging.debug(f"previous_delta aktualisiert auf {previous_delta} g.")
        else:
            # Bei delta <0,1 g wird previous_delta nicht aktualisiert
            logging.debug("previous_delta nicht aktualisiert, da Delta <0,1 g.")

        logging.debug(f"After adjustment - step_size: {step_size} g, smoothed_weight: {smoothed_weight} g")

    # State speichern
    state["last_valid_weight"] = last_valid_weight
    state["smoothed_weight"] = smoothed_weight
    state["change_counter"] = change_counter
    state["previous_delta"] = previous_delta
    state["step_size"] = step_size
    save_state(state)
    logging.info("Zustand gespeichert.")

    # Ergebnis ausgeben
    result = {
        "raw_weight": weight_raw,
        "corrected_weight": weight_corrected,
        "smoothed_weight": smoothed_weight,
        "temperature": current_temp,
    }
    print(json.dumps(result))

    GPIO.cleanup()

if __name__ == "__main__":
    main()
