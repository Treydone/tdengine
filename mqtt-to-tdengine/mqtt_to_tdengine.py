import os
import json
import time
import socket
import taosrest
import paho.mqtt.client as mqtt
import random
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# === Fonction pour insérer des données dans TDengine ===
def insert_into_tdengine(tdengine_host, tdengine_user, tdengine_password, database, table, payload):
    """
    Insère des données dans TDengine.

    :param tdengine_host: L'hôte TDengine (par exemple, http://tdengine:6041).
    :param database: Nom de la base de données où insérer les données.
    :param table: Nom de la table où insérer les données.
    :param payload: Données du message MQTT sous forme de dictionnaire.
    """
    try:
        # Configuration du client TDengine REST
        #client = taosrest.connect(url=tdengine_host, user=tdengine_user, password=tdengine_password)
        client = taosrest.connect(url=tdengine_host)

        # Construire la requête d'insertion
        sensor_id = payload.get("sensor_id", 0)
        location = payload.get("location", "none")
        timestamp = payload.get("timestamp", "now")  # Utiliser "now" si 'ts' n'est pas spécifié
        temperature = payload.get("temperature", 0.0)
        humidity = payload.get("humidity", 0.0)

        # Nom de la table enfant basé sur l'ID du capteur
        child_table = f"{table}_{sensor_id}"

        # Formater correctement le timestamp selon son type
        if isinstance(timestamp, int):
            # Convertir le timestamp Unix (secondes) en millisecondes pour TDengine
            timestamp_value = f"{timestamp * 1000}"  # Conversion en millisecondes
        elif timestamp == "now":
            timestamp_value = "NOW"  # Utiliser le mot-clé NOW pour le timestamp actuel
        else:
            # Si c'est une chaîne, la laisser telle quelle avec des guillemets
            timestamp_value = f"'{timestamp}'"

        query = (
            f"INSERT INTO {database}.{child_table} USING {database}.{table} TAGS ({sensor_id}, '{location}') "
            f"VALUES ('{timestamp_value}', {temperature}, {humidity})"
        )

        # Exécuter l'insertion
        client.query(query)
        logger.info(f"[SUCCESS] Data inserted: {query}")

    except Exception as e:
        logger.error(f"[ERROR] Failed to insert data into TDengine: {e}")


# === Callback MQTT: Lorsqu'un message est reçu ===
def on_message(client, userdata, msg, properties=None):
    """
    Callback appelé à la réception d'un message MQTT.
    """
    try:
        logger.info(f"[INFO] Message reçu sur {msg.topic}: {msg.payload.decode()}")

        # Les messages MQTT sont supposés être au format JSON
        payload = json.loads(msg.payload.decode())

        # Ajouter les données dans TDengine
        tdengine_host = os.getenv("TDENGINE_HOST")
        tdengine_user = os.getenv("TDENGINE_USER")
        tdengine_password = os.getenv("TDENGINE_PASSWORD")
        tdengine_db = os.getenv("TDENGINE_DB")
        tdengine_table = os.getenv("TDENGINE_TABLE")

        insert_into_tdengine(tdengine_host, tdengine_user, tdengine_password, tdengine_db, tdengine_table, payload)

    except Exception as e:
        logger.error(f"[ERROR] Failed to process MQTT message: {e}")

def on_connect(client, userdata, flags, rc, properties=None
               ):
    if rc == 0:
        logger.info("Connected to MQTT Broker!")
    else:
        logger.error("Failed to connect, return code %d\n", rc)

FIRST_RECONNECT_DELAY = 1
RECONNECT_RATE = 2
MAX_RECONNECT_COUNT = 12
MAX_RECONNECT_DELAY = 60

def on_disconnect(client, userdata, rc):
    logger.info("Disconnected with result code: %s", rc)
    reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
    while reconnect_count < MAX_RECONNECT_COUNT:
        logger.info("Reconnecting in %d seconds...", reconnect_delay)
        time.sleep(reconnect_delay)

        try:
            client.reconnect()
            logger.info("Reconnected successfully!")
            return
        except Exception as err:
            logger.warn("%s. Reconnect failed. Retrying...", err)

        reconnect_delay *= RECONNECT_RATE
        reconnect_delay = min(reconnect_delay, MAX_RECONNECT_DELAY)
        reconnect_count += 1
    logger.info("Reconnect failed after %s attempts. Exiting...", reconnect_count)

def wait_for_broker(host, port, timeout=30):
    start_time = time.time()
    while True:
        try:
            with socket.create_connection((host, port), timeout=5):
                logger.info(f"Broker MQTT disponible sur {host}:{port}")
                return
        except (socket.error, ConnectionRefusedError):
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Broker MQTT {host}:{port} indisponible après {timeout} secondes")
            logger.info(f"En attente du broker MQTT ({host}:{port})...")
            time.sleep(2)

def main():
    # Lire les variables d'environnement
    mqtt_broker = os.getenv("MQTT_BROKER")
    mqtt_port = int(os.getenv("MQTT_PORT"))
    mqtt_topic = os.getenv("MQTT_TOPIC")

    # Attendre que le broker soit disponible
    wait_for_broker(mqtt_broker, mqtt_port)

    # Configuration du client MQTT avec l'API v2
    logger.info(f"[INFO] Configuration du client MQTT avec l'API v2...")

    client_id = f'python-mqtt-{random.randint(0, 1000)}'

    client = mqtt.Client(client_id=client_id, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    logger.info(f"[INFO] Connexion au broker MQTT {mqtt_broker}:{mqtt_port}...")
    client.connect(mqtt_broker, mqtt_port, keepalive=60)

    # Souscription au topic MQTT
    logger.info(f"[INFO] Souscription au topic MQTT: {mqtt_topic}")
    client.subscribe(mqtt_topic)
    logger.info(f"[INFO] on_message: {mqtt_topic}")
    client.on_message = on_message

    # Boucle MQTT
    logger.info(f"[INFO] looooooooping: {mqtt_topic}")
    client.loop_forever()

if __name__ == "__main__":
    main()
