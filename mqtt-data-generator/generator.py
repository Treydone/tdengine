import time
import json
import random
import math
from datetime import datetime, timedelta
import paho.mqtt.client as mqtt

# Configuration MQTT
broker = "mqtt-broker"  # Nom de service défini dans docker-compose
port = 1883  # Port standard MQTT
topic = "sensor/data"  # Topic vers lequel publier

# Configuration des paramètres de simulation
SECONDS_PER_HOUR = 1  # 1 seconde dans la simulation correspond à 1 heure réelle
POINTS_PER_SECOND = 10  # Nombre de points générés par seconde réel (10 points/seconde)
TEMP_BOOST = 5.0  # Augmentation de la température pour les journées chaudes
HIGH_TEMP_DAY = 1 / 3  # Probabilité qu'une journée soit "chaude" (1 jour sur 3)

# Capteurs situés dans deux villes en France
sensors = [
    {
        "sensor_id": 1,
        "location": "Paris",
        "base_temperature": 10.0,  # Température minimale de base à Paris
        "base_humidity": 70.0,  # Humidité moyenne à Paris
        "temp_amplitude_day": 12.0,  # Amplitude thermique jour/nuit
        "humidity_amplitude_day": 20.0  # Amplitude variation humidité
    },
    {
        "sensor_id": 2,
        "location": "Marseille",
        "base_temperature": 15.0,  # Température minimale de base à Marseille
        "base_humidity": 60.0,  # Humidité moyenne à Marseille
        "temp_amplitude_day": 10.0,  # Amplitude thermique jour/nuit
        "humidity_amplitude_day": 15.0  # Amplitude variation humidité
    }
]


def generate_daily_pattern(hour, minute_fraction, sensor_config, is_hot_day):
    """
    Génère les valeurs simulées pour une heure donnée selon un modèle réaliste.
    :param hour: Heure de la journée (0-23).
    :param minute_fraction: Fraction de minute (sous-division de l'heure).
    :param sensor_config: Configuration du capteur (ville, base_temperature, etc.).
    :param is_hot_day: Boolean indiquant si la journée est plus chaude que la normale.
    :return: Tuple (température, humidité).
    """
    # Calculer la position temporelle avec minute_fraction
    time_in_hours = hour + minute_fraction / 60.0

    # Température suit une sinusoïde pour simuler les variations jour/nuit
    temp_variation = sensor_config["temp_amplitude_day"] * math.sin(
        math.pi * (time_in_hours - 6) / 12.0)  # Max vers 15h
    temperature = sensor_config["base_temperature"] + temp_variation
    if is_hot_day:
        temperature += TEMP_BOOST  # Augmentation pour journée chaude

    # Humidité varie inversement à la température
    humidity_variation = sensor_config["humidity_amplitude_day"] * math.sin(
        math.pi * (time_in_hours + 6) / 12.0)  # Max vers 3h
    humidity = sensor_config["base_humidity"] - humidity_variation

    # Ajouter un bruit aléatoire pour rendre les données plus réalistes
    temperature += random.uniform(-1.0, 1.0)
    humidity += random.uniform(-3.0, 3.0)

    return round(temperature, 2), round(humidity, 2)


def main():
    client = mqtt.Client()
    client.connect(broker, port)

    # Initialiser la date de simulation au début d'une journée (ex : 00h00)
    simulated_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Déterminer pour chaque capteur si la journée est chaude
    is_hot_day = {sensor["sensor_id"]: random.random() < HIGH_TEMP_DAY for sensor in sensors}

    while True:
        # Heure simulée
        hour = simulated_time.hour  # Obtenir l'heure actuelle (0-23)

        # Générer 10 points interpolés pour chaque seconde simulée
        for i in range(POINTS_PER_SECOND):
            # Calculer la fraction de minute (interpolation)
            second_fraction = i / POINTS_PER_SECOND
            minute_fraction = (simulated_time.minute + second_fraction) + simulated_time.second / 60.0

            # Générer des données pour chaque capteur
            for sensor in sensors:
                temperature, humidity = generate_daily_pattern(
                    hour,
                    minute_fraction,
                    sensor,
                    is_hot_day[sensor["sensor_id"]]
                )

                # Préparer les données du capteur
                data = {
                    "sensor_id": sensor["sensor_id"],
                    "location": sensor["location"],
                    "temperature": temperature,
                    "humidity": humidity,
                    "timestamp": int((simulated_time + timedelta(seconds=second_fraction)).timestamp())
                }

                # Publier les données
                client.publish(topic, json.dumps(data))
                print(f"Published: {data}")

        # Avancer d'une heure simulée (correspondant à 1 seconde réelle)
        simulated_time += timedelta(hours=1)

        # Passer au jour suivant si minuit vient d'être atteint
        if simulated_time.hour == 0:
            is_hot_day = {sensor["sensor_id"]: random.random() < HIGH_TEMP_DAY for sensor in sensors}

        # Pause (1 seconde réelle = 1 heure simulée)
        time.sleep(SECONDS_PER_HOUR)


if __name__ == "__main__":
    main()
