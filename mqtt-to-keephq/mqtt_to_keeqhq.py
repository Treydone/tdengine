import paho.mqtt.client as mqtt
import requests
import json

# Configuration MQTT
MQTT_BROKER = "mqtt-broker"
MQTT_PORT = 1883
MQTT_TOPIC = "alerts/high_temperature"

# Configuration du webhook KeeqHQ
WEBHOOK_URL = "https://hooks.keephq.dev/api/v1/YOUR_WEBHOOK_ENDPOINT"


# Callback sur réception des messages MQTT
def on_message(client, userdata, msg):
    # Convertir le message en dictionnaire JSON
    data = json.loads(msg.payload.decode())
    payload = {
        "alert": "Température élevée détectée",
        "details": f"Température max : {data['max_temperature']} °C",
        "timestamp": data["start_time"],
    }
    # Envoyer la requête POST au webhook
    response = requests.post(WEBHOOK_URL, json=payload)
    if response.status_code == 200:
        print("Alerte envoyée avec succès à KeeqHQ.")
    else:
        print(f"Erreur : {response.status_code} - {response.text}")


# Configurer le client MQTT
client = mqtt.Client()
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.subscribe(MQTT_TOPIC)
client.loop_forever()