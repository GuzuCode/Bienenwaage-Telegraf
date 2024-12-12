import RPi.GPIO as GPIO
import time

# GPIO-Setup
BUTTON_GPIO = 17  # GPIO-Pin des Knopfes
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Steuerdatei
STATUS_FILE = "/tmp/telegraf_collect_status"

def write_status(status):
    """Schreibt den Status in die Steuerdatei."""
    with open(STATUS_FILE, "w") as f:
        f.write("1" if status else "0")

try:
    current_status = True
    write_status(current_status)  # Initialstatus: Sammeln

    while True:
        button_pressed = not GPIO.input(BUTTON_GPIO)  # LOW = Knopf gedrückt
        if button_pressed != current_status:
            current_status = button_pressed
            write_status(not current_status)  # Umkehrung: Knopf gedrückt = nicht sammeln

        time.sleep(0.1)  # Entprellung
except KeyboardInterrupt:
    write_status(True)  # Standardmäßig auf Sammeln setzen
    GPIO.cleanup()
    print("Programm beendet.")