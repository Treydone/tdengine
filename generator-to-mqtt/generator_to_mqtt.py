import time
import os
import socket
import json
import random
import math
from datetime import datetime, timedelta
import paho.mqtt.client as mqtt


def wait_for_broker(host, port, timeout=30):
    """ Attend que le broker MQTT soit disponible """
    start_time = time.time()
    while True:
        try:
            with socket.create_connection((host, port), timeout=5):
                print("Broker MQTT est disponible")
                break
        except (socket.error, ConnectionRefusedError):
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Le broker MQTT {host}:{port} n'est pas disponible après {timeout} secondes")
            print(f"Attente de la disponibilité du broker MQTT ({host}:{port})...")
            time.sleep(2)


# Configuration MQTT
broker = os.getenv("MQTT_BROKER", "localhost")  # Utilisation du nom du service Docker
port = int(os.getenv("MQTT_PORT", "1883"))  # Port par défaut pour MQTT
wait_for_broker(broker, port)

topic = os.getenv("MQTT_TOPIC", "sensors/data")

# Configuration des paramètres de simulation
POINTS_PER_SECOND = 10  # 10 mesures par seconde (1/10 de seconde entre chaque mesure)
TEMPERATURE_SPIKE_INTERVAL = 60  # Pic de température toutes les 60 secondes (1 minute)
SPIKE_DURATION = 3  # Durée du pic en secondes
SPIKE_TEMPERATURE = 8  # Augmentation de température pendant le pic

# Capteurs situés dans deux sites de production en France
sensors = [
    {
        "sensor_id": 1,
        "location": "Paris",
        "base_temperature": 22.5,  # Température de base à Paris
        "base_humidity": 55.0,  # Humidité moyenne à Paris
        "temp_variation": 1.5,  # Variation normale de température
        "humidity_variation": 5.0  # Variation normale d'humidité
    },
    {
        "sensor_id": 2,
        "location": "Marseille",
        "base_temperature": 24.0,  # Température de base à Marseille
        "base_humidity": 50.0,  # Humidité moyenne à Marseille
        "temp_variation": 2.0,  # Variation normale de température
        "humidity_variation": 7.0  # Variation normale d'humidité
    }
]


def is_in_temperature_spike(current_time):
    """
    Détermine si le moment actuel est dans une période de pic de température
    """
    seconds_since_start = current_time.timestamp()
    seconds_in_minute = seconds_since_start % TEMPERATURE_SPIKE_INTERVAL
    return seconds_in_minute < SPIKE_DURATION


def generate_sensor_reading(sensor_config, current_time):
    """
    Génère les valeurs simulées pour un capteur à un moment donné
    """
    # Déterminer si nous sommes dans un pic de température
    in_spike = is_in_temperature_spike(current_time)

    # Générer la température de base avec une légère variation aléatoire
    temperature = sensor_config["base_temperature"] + random.uniform(-sensor_config["temp_variation"],
                                                                     sensor_config["temp_variation"])

    # Ajouter un pic de température si nécessaire
    if in_spike:
        # Plus le pic est récent, plus la température est élevée
        seconds_in_spike = current_time.timestamp() % TEMPERATURE_SPIKE_INTERVAL
        spike_factor = 1 - (seconds_in_spike / SPIKE_DURATION)  # 1 au début du pic, diminue progressivement
        temperature += SPIKE_TEMPERATURE * spike_factor

    # Générer l'humidité qui varie légèrement et inversement à la température
    humidity = sensor_config["base_humidity"] + random.uniform(-sensor_config["humidity_variation"],
                                                               sensor_config["humidity_variation"])

    # Diminuer légèrement l'humidité quand la température augmente
    if in_spike:
        humidity -= (SPIKE_TEMPERATURE / 2) * spike_factor

    # S'assurer que l'humidité est entre 0 et 100%
    humidity = max(0, min(100, humidity))

    return round(temperature, 2), round(humidity, 2)


def main():
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.connect(broker, port)

    try:
        point_counter = 0
        while True:
            # Obtenir l'heure actuelle pour ce point de données
            current_time = datetime.now()

            # Pour chaque capteur, générer et envoyer des données
            for sensor in sensors:
                temperature, humidity = generate_sensor_reading(sensor, current_time)

                # Préparer les données du capteur
                data = {
                    "sensor_id": sensor["sensor_id"],
                    "location": sensor["location"],
                    "temperature": temperature,
                    "humidity": humidity,
                    "timestamp": int(current_time.timestamp() * 1000)
                }

                # Publier les données
                client.publish(topic, json.dumps(data))

                # Afficher les informations
                log_time = current_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                point_counter = (point_counter % POINTS_PER_SECOND) + 1
                print(f"{log_time} Point {point_counter}/{POINTS_PER_SECOND}: {current_time.strftime('%H:%M:%S')} - "
                      f"Sensor {sensor['sensor_id']} - T: {temperature}°C, H: {humidity}%")

                # Indiquer si nous sommes dans un pic de température
                if is_in_temperature_spike(current_time):
                    print(f"🔥 Pic de température en cours! 🔥")

            # Attendre 1/10 de seconde avant la prochaine mesure
            time.sleep(1.0 / POINTS_PER_SECOND)

    except KeyboardInterrupt:
        print("\nArrêt du générateur de données")
    finally:
        client.disconnect()
        print("Déconnecté du broker MQTT")


if __name__ == "__main__":
    main()
