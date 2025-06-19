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
broker = os.getenv("MQTT_BROKER")  # Utilisation du nom du service Docker
port = int(os.getenv("MQTT_PORT"))  # Port par défaut pour MQTT
wait_for_broker(broker, port)

topic = os.getenv("MQTT_TOPIC")

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

    # S'assurer que l'humidité est entre 0 et 100%
    humidity = max(0, min(100, humidity))

    return round(temperature, 2), round(humidity, 2)


def main():
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.connect(broker, port)

    # Initialiser le temps simulé au temps actuel
    simulated_time = datetime.now()

    # Déterminer pour chaque capteur si la journée est chaude
    is_hot_day = {sensor["sensor_id"]: random.random() < HIGH_TEMP_DAY for sensor in sensors}

    try:
        while True:
            # Calculer le temps d'intervalle entre chaque point (en secondes)
            interval = SECONDS_PER_HOUR / POINTS_PER_SECOND  # 0.1 seconde par point

            # Pour chaque point dans la seconde
            for i in range(POINTS_PER_SECOND):
                point_start_time = time.time()

                # Temps simulé pour ce point spécifique
                # À chaque point, avancer de 1/10 d'heure (6 minutes) dans le temps simulé
                point_time = simulated_time + timedelta(hours=i / (POINTS_PER_SECOND))

                # Heure simulée pour ce point
                hour = point_time.hour
                minute = point_time.minute

                # Calculer la fraction de minute pour ce point
                minute_fraction = minute + (point_time.second / 60.0)

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
                        "timestamp": int(point_time.timestamp())
                    }

                    # Publier les données
                    client.publish(topic, json.dumps(data))
                    print(
                        f"Point {i + 1}/10: {point_time.strftime('%H:%M:%S')} - Sensor {sensor['sensor_id']} - T: {temperature}°C, H: {humidity}%")

                # Calculer le temps qu'a pris la génération et l'envoi
                elapsed = time.time() - point_start_time

                # Attendre le temps restant pour compléter l'intervalle
                sleep_time = max(0, interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)

            # Après avoir envoyé les 10 points, avancer d'une heure complète dans le temps simulé
            simulated_time += timedelta(hours=1)

            # Passer au jour suivant si minuit vient d'être atteint
            if simulated_time.hour == 0:
                is_hot_day = {sensor["sensor_id"]: random.random() < HIGH_TEMP_DAY for sensor in sensors}
                print(f"Nouveau jour simulé! Conditions météo mises à jour.")

    except KeyboardInterrupt:
        print("\nArrêt du générateur de données")
    finally:
        client.disconnect()
        print("Déconnecté du broker MQTT")


if __name__ == "__main__":
    main()
