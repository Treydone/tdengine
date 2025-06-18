import json
import os
import requests
import signal
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
keephq_webhook_url = os.getenv('KEEPHQ_WEBHOOK_URL')

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
                        # Afficher les attributs et méthodes disponibles
                        logger.info(f"Attributs disponibles: {dir(message)}")

                        # Tester quelques méthodes potentielles pour extraire les données
                        for method_name in dir(message):
                            # Ignorer les méthodes spéciales Python
                            if method_name.startswith('__'):
                                continue

                            # Tenter d'appeler la méthode/accéder à l'attribut
                            try:
                                attr = getattr(message, method_name)
                                # Si c'est un callable (méthode), on l'appelle sans paramètres
                                if callable(attr):
                                    try:
                                        result = attr()
                                        logger.info(f"Méthode {method_name}() -> {result}")
                                    except TypeError:
                                        # Peut-être que la méthode nécessite des paramètres
                                        logger.info(f"Méthode {method_name} nécessite des paramètres")
                                else:
                                    # Si c'est un attribut, on affiche sa valeur
                                    logger.info(f"Attribut {method_name} -> {attr}")
                            except Exception as e:
                                logger.info(f"Erreur lors de l'accès à {method_name}: {e}")

                        # Essayons de construire manuellement un dictionnaire de données à partir de l'objet
                        try:
                            # Supposons que nous avons des données sur la température maximale
                            # dans l'objet message d'une manière ou d'une autre
                            payload = {
                                "alert": "Température élevée détectée",
                                "details": "Température élevée détectée dans les données",
                                "timestamp": time.time(),
                            }

                            # Log des données avant envoi
                            logger.info(f"Préparation de l'envoi de l'alerte: {payload}")

                            # Envoyer la requête POST au webhook
                            response = requests.post(keephq_webhook_url, json=payload)
                            if response.status_code == 200:
                                logger.info("Alerte envoyée avec succès à KeepHQ.")
                            else:
                                logger.error(f"Erreur : {response.status_code} - {response.text}")
                        except Exception as e:
                            logger.error(f"Erreur lors de l'envoi de l'alerte: {e}")

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