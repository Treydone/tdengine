import json
import os
import requests
from datetime import datetime
import signal
import uuid
import sys
import time
import logging
from taos.tmq import Consumer, TmqError

# Configuration du logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Récupération des variables d'environnement
tdengine_ip = os.getenv('TDENGINE_IP')
tdengine_port = os.getenv('TDENGINE_PORT')
tdengine_user = os.getenv('TDENGINE_USER')
tdengine_password = os.getenv('TDENGINE_PASSWORD')
tdengine_db = os.getenv('TDENGINE_DB')
tdengine_topic = os.getenv('TDENGINE_TOPIC')
keephq_url = os.getenv('KEEPHQ_URL')
keephq_provider = os.getenv('KEEPHQ_PROVIDER')
keephq_api_key = os.getenv('KEEPHQ_API_KEY')

keephq_webhook_url = f"{keephq_url}/alerts/event/"
# keephq_webhook_url = f"{keephq_url}/alerts/event/{keephq_provider}"

# Configuration du consumer
config = {
    "td.connect.user": tdengine_user,
    "td.connect.pass": tdengine_password,
    "td.connect.ip": tdengine_ip,
    "td.connect.port": tdengine_port,
    "group.id": "python_high_temp_consumer",
    "client.id": "python_client",
    "auto.offset.reset": "latest",  # 'earliest' pour lire depuis le début
    "enable.auto.commit": "true",
    "msg.with.table.name": "true"
}

# Gestionnaire de signal pour arrêter proprement
running = True

def signal_handler(sig, frame):
    global running
    logger.info("Arrêt du consumer...")
    running = False

signal.signal(signal.SIGINT, signal_handler)

def send_alert_to_keephq(message):
    """
    Envoie une alerte à KeepHQ via leur webhook API en utilisant les données du message TDengine
    """
    try:
        # Extraction des données du message
        rows = message.fetchall()
        if not rows or len(rows) == 0:
            logger.warning("Aucune donnée à traiter dans le message")
            return False

        # Extraction des noms de champs et création d'un dictionnaire pour le premier enregistrement
        fields = message.fields()
        row = rows[0]

        # Créer un dictionnaire avec les valeurs
        data = {}
        for i, field in enumerate(fields):
            if i < len(row):
                field_name = field.name
                if field_name:
                    data[field_name] = row[i]

        logger.info(f"Données extraites: {data}")

        # Récupération des valeurs pertinentes avec vérification de présence
        avg_temp = data.get('avg_temperature')
        min_temp = data.get('min_temperature')
        max_temp = data.get('max_temperature')
        avg_humidity = data.get('avg_humidity')
        min_humidity = data.get('min_humidity')
        max_humidity = data.get('max_humidity')

        # Définition des seuils d'alerte
        temp_high_threshold = 27.0
        humidity_high_threshold = 90.0

        # Détermination du niveau de sévérité en fonction des valeurs
        severity = "info"
        alert_reasons = []

        if max_temp is not None and max_temp > temp_high_threshold:
            severity = "critical"
            alert_reasons.append(f"température élevée ({max_temp:.1f}°C > {temp_high_threshold:.1f}°C)")

        if max_humidity is not None and max_humidity > humidity_high_threshold:
            severity = "warning" if severity != "critical" else severity
            alert_reasons.append(f"humidité élevée ({max_humidity:.1f}% > {humidity_high_threshold:.1f}%)")

        # S'il n'y a pas de raison d'alerte, on sort
        if not alert_reasons:
            logger.info("Aucune condition d'alerte détectée, pas d'envoi à KeepHQ")
            return False

        # Construction du titre de l'alerte
        title = "Alerte capteur: " + ", ".join(alert_reasons)

        # Construction du message détaillé
        time_str = data.get('_wstart').strftime("%Y-%m-%d %H:%M:%S") if isinstance(data.get('_wstart'), datetime) else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        description = "Alerte détectée le " + time_str + "\n\n"

        # Ajout des informations de température si disponibles
        if avg_temp is not None and min_temp is not None and max_temp is not None:
            description += f"Température: {avg_temp:.2f}°C (min: {min_temp:.2f}°C, max: {max_temp:.2f}°C)\n"

        # Ajout des informations d'humidité si disponibles
        if avg_humidity is not None and min_humidity is not None and max_humidity is not None:
            description += f"Humidité: {avg_humidity:.2f}% (min: {min_humidity:.2f}%, max: {max_humidity:.2f}%)"

        # Récupération de l'heure actuelle au format ISO
        current_time_iso = datetime.now().isoformat()

        # Extraction du sensor
        sensor_id = data.get("sensor_id")

        # Création d'un identifiant unique pour l'alerte
        alert_id = str(uuid.uuid4())

        # Format de payload conforme à AlertDto
        payload = {
            "id": alert_id,
            "name": title,
            "status": "firing",
            "severity": severity,
            "lastReceived": current_time_iso,
            "firingStartTime": current_time_iso,
            "firingCounter": 1,
            "environment": "production",
            "service": "TDengine",
            "source": [f"Agent TDEngine vers KeepHQ"],
            "description": description,
            "description_format": "markdown",
            "pushed": True,
            "event_id": alert_id,
            "labels": {
                "sensor": sensor_id,
                "service": "TDengine",
                "type": "temperature_humidity"
            },
            "fingerprint": f"tdengine-alert-{sensor_id}",
            "providerId": keephq_provider,
            "providerType": "webhook"
        }

        # Ajout des données dans les labels
        if avg_temp is not None:
            payload["labels"]["avg_temperature"] = str(avg_temp)
        if max_temp is not None:
            payload["labels"]["max_temperature"] = str(max_temp)
        if avg_humidity is not None:
            payload["labels"]["avg_humidity"] = str(avg_humidity)
        if max_humidity is not None:
            payload["labels"]["max_humidity"] = str(max_humidity)

        # En-têtes pour la requête
        headers = {
            "Content-Type": "application/json"
        }
        if keephq_api_key:
            headers["Authorization"] = f"Bearer {keephq_api_key}"

        # Envoi de la requête
        logger.info(f"Envoi d'une alerte à KeepHQ: {title}")
        logger.debug(f"Payload complet: {json.dumps(payload)}")
        response = requests.post(keephq_webhook_url, json=payload, headers=headers)

        # Vérification de la réponse
        if response.status_code in [200, 201, 202]:
            logger.info(f"Alerte envoyée avec succès à KeepHQ: {response.text}")
            return True
        else:
            logger.error(f"Échec d'envoi de l'alerte à KeepHQ. Code: {response.status_code}, Réponse: {response.text}")
            return False

    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de l'alerte à KeepHQ: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    try:
        # Créer un consumer
        consumer = Consumer(config)

        # S'abonner au topic
        consumer.subscribe([("%s" % tdengine_topic)])
        logger.info(f"Abonnement au topic {tdengine_topic} réussi")

        # Boucle de consommation
        while running:
            try:
                # Récupérer les messages (timeout en ms)
                messages = consumer.poll(1000)

                if messages:
                    for message in messages:

                        send_alert_to_keephq(message)

                    # Committer les offsets après traitement
                    consumer.commit()

                # Petite pause pour éviter de surcharger le CPU
                time.sleep(0.1)

            except TmqError as e:
                logger.error(f"Erreur TMQ: {e}")
                time.sleep(1)  # Pause avant de réessayer

    except Exception as e:
        logger.error(f"Erreur: {e}")
    finally:
        # Fermer proprement le consumer
        if 'consumer' in locals():
            consumer.unsubscribe()
            consumer.close()
            logger.info("Consumer fermé")

if __name__ == "__main__":
    main()