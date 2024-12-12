#!/bin/bash

set -e

echo "==== Bienenwaage Installation ===="

# 1. Systemaktualisierung
echo "System wird aktualisiert..."
sudo apt update && sudo apt upgrade -y

# 2. Installieren der benötigten Pakete
echo "Installieren von benötigten Abhängigkeiten..."
sudo apt install -y python3 python3-pip telegraf git

# 3. Python-Abhängigkeiten installieren
echo "Python-Abhängigkeiten werden installiert..."
pip3 install -r /opt/bienenwaage/config/requirements.txt

# 4. Verzeichnisstruktur einrichten
echo "Verzeichnisstruktur wird organisiert..."
sudo mkdir -p /opt/bienenwaage/config
sudo mkdir -p /opt/bienenwaage/scripts

sudo cp -r config/* /opt/bienenwaage/config/
sudo cp -r scripts/* /opt/bienenwaage/scripts/

# 5. Konfiguration vorbereiten
echo "Prüfen der settings.env Datei..."
if [[ ! -f /opt/bienenwaage/config/settings.env ]]; then
    echo "Die settings.env Datei fehlt. Bitte fügen Sie diese im Verzeichnis /opt/bienenwaage/config hinzu."
    exit 1
fi

echo "Telegraf-Konfiguration wird generiert..."
python3 /opt/bienenwaage/scripts/generate_config.py

# 6. Telegraf einrichten
echo "Telegraf wird eingerichtet..."
sudo cp /opt/bienenwaage/config/telegraf.conf /etc/telegraf/telegraf.conf
sudo systemctl enable telegraf
sudo systemctl restart telegraf

# 7. Abschluss
echo "==== Installation abgeschlossen! ===="
echo "Telegraf läuft und die Konfiguration ist aktiv. Passen Sie ggf. die settings.env Datei an und starten Sie den Telegraf-Dienst neu."
