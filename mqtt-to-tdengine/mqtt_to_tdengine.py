import os
import json
import taosrest
import paho.mqtt.client as mqtt
import random

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
        client = taosrest.connect(url=tdengine_host, user=tdengine_user, password=tdengine_password)

        # Construire la requête d'insertion
        sensor_id = payload.get("sensor_id", 0)
        location = payload.get("location", "none")
        timestamp = payload.get("ts", "now")  # Utiliser "now" si 'ts' n'est pas spécifié
        temperature = payload.get("temperature", 0.0)
        humidity = payload.get("humidity", 0.0)

        query = (
            f"INSERT INTO {database}.{table} TAGS ({sensor_id}, {location}) "
            f"VALUES ('{timestamp}', {temperature}, {humidity})"
        )

        # Exécuter l'insertion
        client.query(query)
        print(f"[SUCCESS] Data inserted: {query}")

    except Exception as e:
        print(f"[ERROR] Failed to insert data into TDengine: {e}")


# === Callback MQTT: Lorsqu'un message est reçu ===
def on_message(client, userdata, msg, properties=None):
    """
    Callback appelé à la réception d'un message MQTT.
    """
    try:
        print(f"[INFO] Message reçu sur {msg.topic}: {msg.payload.decode()}")

        # Les messages MQTT sont supposés être au format JSON
        payload = json.loads(msg.payload.decode())

        # Ajouter les données dans TDengine
        tdengine_host = os.getenv("TDENGINE_HOST")
        tdengine_user = os.getenv("TDENGINE_USER")
        tdengine_password = os.getenv("TDENGINE_PASSWORD")
        tdengine_db = os.getenv("TDENGINE_DB")
        tdengine_table = os.getenv("TDENGINE_TABLE")

        insert_into_tdengine(tdengine_host, tdengine_user, tdengine_db, tdengine_password, tdengine_table, payload)

    except Exception as e:
        print(f"[ERROR] Failed to process MQTT message: {e}")

def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print("Connected to MQTT Broker!")
    else:
        print("Failed to connect, return code %d\n", rc)


# === Programme principal ===
if __name__ == "__main__":
    # Lire les variables d'environnement
    mqtt_broker = os.getenv("MQTT_BROKER")
    mqtt_port = int(os.getenv("MQTT_PORT"))
    mqtt_topic = os.getenv("MQTT_TOPIC")

    client_id = f'python-mqtt-{random.randint(0, 1000)}'

    # Configuration du client MQTT avec l'API v2
    print(f"[INFO] Configuration du client MQTT avec l'API v2...")
    client = mqtt.Client(protocol=mqtt.MQTTv5, client_id=client_id, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

    try:
        client.on_connect = on_connect
        print(f"[INFO] Connexion au broker MQTT {mqtt_broker}:{mqtt_port}...")
        client.connect(mqtt_broker, mqtt_port, keepalive=60)

        # Souscription au topic MQTT
        print(f"[INFO] Souscription au topic MQTT: {mqtt_topic}")
        client.subscribe(mqtt_topic)

        client.on_message = on_message

        # Boucle MQTT
        client.loop_forever()

    except Exception as e:
        print(f"[ERROR] Impossible de se connecter au broker MQTT : {e}")
