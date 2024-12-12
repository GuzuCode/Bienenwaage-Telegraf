import os
from jinja2 import Environment, FileSystemLoader

# Pfade setzen
template_dir = "/opt/bienenwaage/config"
template_file = "telegraf.conf.j2"
output_file = "/etc/telegraf/telegraf.conf"
env_file = "/opt/bienenwaage/config/settings.env"

# Settings aus der .env-Datei laden
def load_env(file_path):
    settings = {}
    with open(file_path, "r") as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith("#"):
                key, value = line.split("=", 1)
                settings[key.strip()] = value.strip()
    return settings

# Jinja-Template anwenden
def generate_config(template_dir, template_file, output_file, settings):
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template(template_file)
    rendered = template.render(settings)
    
    with open(output_file, "w") as file:
        file.write(rendered)
    print(f"Konfiguration erfolgreich erstellt: {output_file}")

if __name__ == "__main__":
    # Load environment settings
    settings = load_env(env_file)

    # Generate Telegraf configuration
    generate_config(template_dir, template_file, output_file, settings)
